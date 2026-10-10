import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from agent_wake_manager.core import Store
from agent_wake_manager.contracts import normalize_config

SECRET='SYNTHETIC_PRIVATE_CLI_BODY_41bc'

class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.config=self.root/'fixture-config.json'
        self.config.write_text(json.dumps({'schema':'awm.config/1','instances':[{'id':'test','provider':'codex'}]}))
        self.data=self.root/'isolated-data'

    def tearDown(self):self.tmp.cleanup()

    def run_cli(self,command,input_text=''):
        return subprocess.run([sys.executable,'-B','-m','agent_wake_manager','--data-dir',str(self.data),
            '--config',str(self.config)]+command,input=input_text,capture_output=True,text=True)

    def event(self):
        return {'schema':'awm.event/1','event_id':'e1','instance_id':'test','provider':'codex',
            'kind':'task.started','session_id':'session','task_id':'turn','generation':1,
            'owner':{'pid':100,'birth':'birth'},'prompt':SECRET,'response':SECRET}

    def test_body_not_in_cli_output_database_or_audit_log(self):
        result=self.run_cli(['event'],json.dumps(self.event()))
        self.assertEqual(result.returncode,0,result.stderr)
        status=self.run_cli(['status'])
        self.assertEqual(json.loads(status.stdout)['active_task_count'],1)
        self.assertNotIn(SECRET,result.stdout+result.stderr+status.stdout+status.stderr)
        self.assertTrue((self.data/'audit.jsonl').exists())
        for p in self.data.iterdir():
            if p.is_file():self.assertNotIn(SECRET.encode(),p.read_bytes(),p.name)

    def test_malformed_json_has_fixed_error_without_body(self):
        result=self.run_cli(['event'],'{"prompt":"'+SECRET)
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stderr.strip(),'INVALID_JSON')
        self.assertNotIn(SECRET,result.stdout+result.stderr)

    def test_cli_reset_needs_confirmation_and_warns(self):
        self.assertEqual(self.run_cli(['event'],json.dumps(self.event())).returncode,0)
        result=self.run_cli(['reset'])
        self.assertEqual(result.returncode,2)
        self.assertIn('RESET_CONFIRMATION_REQUIRED',result.stderr)
        self.assertEqual(json.loads(self.run_cli(['status']).stdout)['active_task_count'],1)
        confirmed=self.run_cli(['reset','--confirm'])
        self.assertEqual(confirmed.returncode,0)
        self.assertIn('RESET_CLEARS_TASKS',confirmed.stderr)
        state=json.loads(confirmed.stdout)
        self.assertEqual(state['active_task_count'],0)
        self.assertFalse(state['paused'])

    def test_cli_pause_and_resume_preserve_existing_task(self):
        self.run_cli(['event'],json.dumps(self.event()))
        paused=json.loads(self.run_cli(['pause']).stdout)
        self.assertEqual(paused['active_task_count'],1)
        self.assertFalse(paused['lease_intent'])
        resumed=json.loads(self.run_cli(['resume']).stdout)
        self.assertTrue(resumed['lease_intent'])

    def test_explicit_data_dir_is_mandatory(self):
        result=subprocess.run([sys.executable,'-B','-m','agent_wake_manager','status'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('--data-dir',result.stderr)
