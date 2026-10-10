import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from agent_wake_manager.core import Store
from agent_wake_manager.contracts import ContractError, normalize_config

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'state.sqlite3'
        self.config=normalize_config({'schema':'awm.config/1','instances':[
            {'id':'personal','provider':'codex'},{'id':'work','provider':'codex'},
            {'id':'claude','provider':'claude'}]})
        self.store=Store(self.path,self.config)
        self.serial=0

    def tearDown(self):
        self.tmp.cleanup()

    def event(self,kind='task.started',instance='personal',task='turn',generation=1,**kwargs):
        self.serial+=1
        e=dict(schema='awm.event/1',event_id='event-'+str(self.serial),
            instance_id=instance,provider='claude' if instance=='claude' else 'codex',
            kind=kind,session_id='session',task_id=task,generation=generation,
            owner={'pid':100,'birth':'born100'})
        e.update(kwargs)
        return e

    def test_start_and_finish_update_hold_intent(self):
        self.store.apply(self.event())
        self.assertEqual(self.store.status()['active_task_count'],1)
        self.assertTrue(self.store.status()['lease_intent'])
        self.store.apply(self.event('task.finished'))
        self.assertEqual(self.store.tasks(),[])
        self.assertFalse(self.store.status()['lease_intent'])

    def test_instances_with_identical_native_ids_are_isolated(self):
        for instance in ('personal','work','claude'):
            self.store.apply(self.event(instance=instance))
        self.store.apply(self.event('task.finished',instance='work'))
        self.assertEqual({t['instance_id'] for t in self.store.tasks()},{'personal','claude'})

    def test_duplicate_delivery_is_idempotent(self):
        event=self.event()
        self.store.apply(event);self.store.apply(event)
        self.assertEqual(len(self.store.tasks()),1)
        self.assertEqual(len(self.store.events()),1)

    def test_same_event_id_different_metadata_is_rejected(self):
        event=self.event();self.store.apply(event)
        with self.assertRaises(ContractError):
            self.store.apply({**event,'task_id':'other'})
        self.assertEqual(len(self.store.tasks()),1)

    def test_late_start_and_tool_events_do_not_reopen_terminal_generation(self):
        self.store.apply(self.event())
        self.store.apply(self.event('task.finished'))
        for kind in ('task.started','tool.started','tool.finished','task.waiting_permission'):
            self.store.apply(self.event(kind,tool_id='tool-1'))
        self.assertEqual(self.store.tasks(),[])

    def test_terminal_before_start_blocks_late_start(self):
        self.store.apply(self.event('task.finished'))
        self.store.apply(self.event())
        self.assertEqual(self.store.tasks(),[])

    def test_explicit_new_generation_can_resume(self):
        self.store.apply(self.event());self.store.apply(self.event('task.finished'))
        self.store.apply(self.event('task.resumed',generation=2))
        self.assertEqual([t['generation'] for t in self.store.tasks()],[2])

    def test_pause_preserves_records_and_finish_during_pause(self):
        self.store.apply(self.event());self.store.pause()
        self.assertEqual(len(self.store.tasks()),1)
        self.assertFalse(self.store.status()['lease_intent'])
        self.store.apply(self.event('task.finished'))
        self.store.resume()
        self.assertEqual(self.store.tasks(),[])
        self.assertFalse(self.store.status()['lease_intent'])

    def test_start_during_pause_is_tracked_and_resume_restores_intent(self):
        self.store.pause();self.store.apply(self.event())
        self.assertEqual(len(self.store.tasks()),1)
        self.assertFalse(self.store.status()['lease_intent'])
        self.store.resume()
        self.assertTrue(self.store.status()['lease_intent'])

    def test_pause_survives_core_reopen_without_losing_task(self):
        self.store.apply(self.event());self.store.pause()
        reopened=Store(self.path,self.config)
        self.assertTrue(reopened.status()['paused'])
        self.assertEqual(len(reopened.tasks()),1)
        reopened.resume();self.assertTrue(reopened.status()['lease_intent'])

    def test_reset_requires_confirmation_and_is_not_pause(self):
        self.store.apply(self.event())
        with self.assertRaises(ContractError):self.store.reset()
        self.assertEqual(len(self.store.tasks()),1)
        self.store.reset(confirm=True)
        self.assertEqual(self.store.tasks(),[])
        self.assertFalse(self.store.status()['paused'])
        self.store.apply(self.event())
        self.assertEqual(self.store.tasks(),[])

    def test_reset_does_not_resume_a_paused_core(self):
        self.store.pause();self.store.apply(self.event())
        self.store.reset(confirm=True)
        self.assertTrue(self.store.status()['paused'])

    def test_pid_reuse_reaps_only_old_identity(self):
        self.store.apply(self.event())
        self.store.apply(self.event(instance='work',owner={'pid':200,'birth':'born200'}))
        self.store.reap({100:{'birth':'reused100'},200:{'birth':'born200'}})
        self.assertEqual([t['instance_id'] for t in self.store.tasks()],['work'])
        self.store.apply(self.event())
        self.assertEqual(len(self.store.tasks()),1)

    def test_failed_observation_preserves_hold(self):
        self.store.apply(self.event());self.store.reap(None)
        self.assertTrue(self.store.status()['lease_intent'])

    def test_invalid_observation_cannot_partially_reap(self):
        self.store.apply(self.event())
        self.store.apply(self.event(instance='work',owner={'pid':200,'birth':'born200'}))
        with self.assertRaises(ContractError):self.store.reap({200:None})
        self.assertEqual(len(self.store.tasks()),2)

    def test_confirmed_empty_observation_reaps(self):
        self.store.apply(self.event());self.store.reap({})
        self.assertFalse(self.store.status()['lease_intent'])

    def test_no_silence_expiry(self):
        self.store.apply(self.event(occurred_at='2000-01-01T00:00:00Z'))
        self.store.reap({100:{'birth':'born100'}})
        self.assertEqual(len(self.store.tasks()),1)

    def test_parent_stop_preserves_child_and_background(self):
        self.store.apply(self.event())
        self.store.apply(self.event('child.started',task='child',parent_task_id='turn'))
        self.store.apply(self.event('background.registered',task='background',parent_task_id='turn'))
        self.store.apply(self.event('task.finished'))
        self.assertEqual({t['task_id'] for t in self.store.tasks()},{'child','background'})
        self.store.apply(self.event('child.finished',task='child'))
        self.store.apply(self.event('background.finished',task='background'))
        self.assertFalse(self.store.status()['lease_intent'])

    def test_session_close_does_not_close_independent_child(self):
        self.store.apply(self.event())
        self.store.apply(self.event('child.started',task='child',parent_task_id='turn'))
        self.store.apply(self.event('session.closed',task_id=None))
        self.assertEqual([t['task_id'] for t in self.store.tasks()],['child'])

    def test_permission_wait_keeps_hold(self):
        self.store.apply(self.event());self.store.apply(self.event('task.waiting_permission'))
        self.assertEqual(self.store.tasks()[0]['phase'],'waiting_permission')
        self.assertTrue(self.store.status()['lease_intent'])

    def test_unknown_instance_is_rejected(self):
        with self.assertRaises(ContractError):self.store.apply(self.event(instance='unregistered'))
        self.assertEqual(self.store.tasks(),[])

    def test_no_implicit_task_from_tool_or_session_open(self):
        self.store.apply(self.event('session.opened',task_id=None))
        self.store.apply(self.event('tool.started',tool_id='tool'))
        self.assertEqual(self.store.tasks(),[])

    def test_status_does_not_fabricate_external_observations(self):
        self.store.apply(self.event())
        state=self.store.status()
        for field in ('service_alive','lease_alive','amphetamine_active'):
            self.assertIsNone(state[field])
        self.assertTrue(state['lease_intent'])

    def test_older_generation_cannot_create_a_second_hold(self):
        self.store.apply(self.event(generation=2))
        self.store.apply(self.event(generation=1))
        self.assertEqual([t['generation'] for t in self.store.tasks()],[2])

    def test_closed_session_blocks_unseen_late_main_start(self):
        self.store.apply(self.event('session.closed',task_id=None))
        self.store.apply(self.event(task='never-observed'))
        self.assertEqual(self.store.tasks(),[])

    def test_foreign_database_is_rejected_without_mutating_schema(self):
        foreign=self.path.parent/'foreign.sqlite3'
        with sqlite3.connect(str(foreign)) as db:
            db.execute('CREATE TABLE events(seq INTEGER PRIMARY KEY,data TEXT)')
        before=foreign.read_bytes()
        with self.assertRaises(ContractError):Store(foreign,self.config)
        self.assertEqual(foreign.read_bytes(),before)

    def test_disabled_instance_and_provider_mismatch_are_rejected(self):
        disabled=Store(self.path,normalize_config({'schema':'awm.config/1','instances':[
            {'id':'personal','provider':'codex','enabled':False}]}))
        with self.assertRaises(ContractError):disabled.apply(self.event())
        with self.assertRaises(ContractError):self.store.apply(self.event(provider='claude'))
        self.assertEqual(self.store.tasks(),[])
