import json
import tempfile
import unittest
from pathlib import Path
from agent_wake_manager.contracts import ContractError,normalize_event,normalize_config,normalize_hook
from agent_wake_manager.core import Store

SECRET='SYNTHETIC_PRIVATE_BODY_7fa2'

class PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.config=normalize_config({'schema':'awm.config/1','instances':[{'id':'test','provider':'codex'}]})
        self.store=Store(self.root/'state.sqlite3',self.config)

    def tearDown(self):self.tmp.cleanup()

    def payload(self):
        return {'hook_event_name':'UserPromptSubmit','event_id':'native-1','session_id':'session','turn_id':'turn',
            'prompt':SECRET,'response':SECRET,'messages':[{'content':SECRET}],
            'tool_input':{'command':SECRET},'tool_response':{'stdout':SECRET},
            'transcript_path':'/never-open/'+SECRET,'api_key':SECRET,'file_content':SECRET}

    def test_hook_body_not_in_database_log_errors_or_status(self):
        event=normalize_hook(self.payload(),instance_id='test',provider='codex',owner={'pid':100,'birth':'birth'})
        self.store.apply(event)
        self.assertEqual(len(self.store.tasks()),1)
        outputs=json.dumps([event,self.store.events(),self.store.status()])
        self.assertNotIn(SECRET,outputs)
        for p in self.root.iterdir():
            if p.is_file():self.assertNotIn(SECRET.encode(),p.read_bytes(),p.name)

    def test_ignored_hook_content_is_never_inspected_or_rendered(self):
        class Forbidden:
            def __str__(self):raise AssertionError('body rendered')
            def __repr__(self):raise AssertionError('body inspected')
        payload=self.payload();payload['tool_response']=Forbidden();payload['tool_input']=Forbidden()
        event=normalize_hook(payload,instance_id='test',provider='codex',owner={'pid':100,'birth':'birth'})
        self.store.apply(event);self.assertEqual(len(self.store.tasks()),1)

    def test_direct_event_is_also_projected_at_core_boundary(self):
        event={'schema':'awm.event/1','event_id':'e1','instance_id':'test','provider':'codex',
            'kind':'task.started','session_id':'session','task_id':'turn','generation':1,
            'owner':{'pid':100,'birth':'birth','secret':SECRET},'prompt':SECRET,'tool_response':SECRET}
        self.store.apply(event)
        self.assertNotIn(SECRET,json.dumps(self.store.events()+self.store.tasks()))

    def test_invalid_metadata_errors_never_echo_input(self):
        event={'schema':SECRET,'prompt':SECRET}
        with self.assertRaises(ContractError) as result:normalize_event(event)
        self.assertNotIn(SECRET,str(result.exception))

    def test_config_supports_many_instances_and_drops_secret_fields(self):
        raw={'schema':'awm.config/1','api_key':SECRET,'instances':[
            {'id':'instance-'+str(i),'provider':'codex','config_root':'/synthetic/home-'+str(i),'token':SECRET}
            for i in range(8)]}
        config=normalize_config(raw)
        self.assertEqual(len(config['instances']),8)
        self.assertNotIn(SECRET,json.dumps(config))

    def test_duplicate_config_ids_rejected(self):
        with self.assertRaises(ContractError):normalize_config({'schema':'awm.config/1','instances':[
            {'id':'x','provider':'codex'},{'id':'x','provider':'claude'}]})

    def test_unmapped_hook_returns_safe_capability_error(self):
        with self.assertRaises(ContractError) as result:
            normalize_hook({'hook_event_name':SECRET},instance_id='test',provider='codex',owner={})
        self.assertNotIn(SECRET,str(result.exception))
