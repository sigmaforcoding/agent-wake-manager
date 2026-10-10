"""SQLite lifecycle reducer derived from the experimental Store.

No scanner, process execution, provider configuration writes or power calls.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .contracts import ContractError, STARTS, FINISHES, birth, normalize_config, normalize_event, utc_now

class Store:
    def __init__(self, path, config):
        self.path=Path(path)
        self.config=normalize_config(config)
        self.instances={i['id']:i for i in self.config['instances']}
        self._check_existing_database()
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        # Create without exposing a new database at the user's default umask.
        descriptor=os.open(str(self.path),os.O_CREAT|os.O_WRONLY,0o600);os.close(descriptor)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS tasks(key TEXT PRIMARY KEY,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS ended(key TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(instance TEXT,event_id TEXT,data TEXT NOT NULL,
                    received_at TEXT NOT NULL,PRIMARY KEY(instance,event_id));
                CREATE TABLE IF NOT EXISTS closed_sessions(key TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS generations(key TEXT PRIMARY KEY,generation INTEGER NOT NULL);
                PRAGMA user_version=1;
            ''')

    def _check_existing_database(self):
        if not self.path.exists() or self.path.stat().st_size==0:return
        expected={'tasks':['key','data'],'ended':['key'],'settings':['key','data'],
            'events':['instance','event_id','data','received_at'],'closed_sessions':['key'],
            'generations':['key','generation']}
        try:
            db=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)
            try:
                if db.execute('PRAGMA user_version').fetchone()[0]!=1:raise ContractError('INCOMPATIBLE_DATABASE')
                for table,columns in expected.items():
                    if [r[1] for r in db.execute('PRAGMA table_info('+table+')')]!=columns:
                        raise ContractError('INCOMPATIBLE_DATABASE')
            finally:db.close()
        except sqlite3.DatabaseError:raise ContractError('INCOMPATIBLE_DATABASE') from None

    @contextmanager
    def connection(self):
        db=sqlite3.connect(str(self.path),timeout=2)
        try:
            db.execute('PRAGMA busy_timeout=2000');db.execute('BEGIN IMMEDIATE')
            yield db;db.commit()
        except Exception:
            db.rollback();raise
        finally:db.close()

    @staticmethod
    def key(event):
        return json.dumps([event['instance_id'],event['session_id'],event['task_id'],event['generation']],separators=(',',':'))

    def tasks(self):
        with self.connection() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT data FROM tasks ORDER BY key')]

    def events(self):
        with self.connection() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT data FROM events ORDER BY rowid')]

    def apply(self, raw):
        event=normalize_event(raw)
        instance=self.instances.get(event['instance_id'])
        if not instance:raise ContractError('UNKNOWN_INSTANCE')
        if not instance['enabled']:raise ContractError('INSTANCE_DISABLED')
        if instance['provider']!=event['provider']:raise ContractError('PROVIDER_MISMATCH')
        encoded=json.dumps(event,sort_keys=True,separators=(',',':'))
        with self.connection() as db:
            existing=db.execute('SELECT data FROM events WHERE instance=? AND event_id=?',
                (event['instance_id'],event['event_id'])).fetchone()
            if existing:
                if existing[0]!=encoded:raise ContractError('EVENT_CONFLICT')
                return
            db.execute('INSERT INTO events VALUES(?,?,?,?)',
                (event['instance_id'],event['event_id'],encoded,utc_now()))
            key=self.key(event);kind=event['kind']
            session_key=json.dumps([event['instance_id'],event['session_id']])
            logical_key=json.dumps([event['instance_id'],event['session_id'],event['task_id']])
            def finish(k):
                db.execute('DELETE FROM tasks WHERE key=?',(k,))
                db.execute('INSERT OR IGNORE INTO ended VALUES(?)',(k,))
            if kind in FINISHES:finish(key)
            elif kind=='session.closed':
                db.execute('INSERT OR IGNORE INTO closed_sessions VALUES(?)',(session_key,))
                for k,data in list(db.execute('SELECT key,data FROM tasks')):
                    task=json.loads(data)
                    if task['instance_id']==event['instance_id'] and task['session_id']==event['session_id'] and task['task_kind']=='main':finish(k)
            elif kind in STARTS:
                if db.execute('SELECT 1 FROM ended WHERE key=?',(key,)).fetchone():return
                maximum=db.execute('SELECT generation FROM generations WHERE key=?',(logical_key,)).fetchone()
                if maximum and event['generation']<maximum[0]:return
                previous=db.execute('SELECT data FROM tasks WHERE key=?',(key,)).fetchone()
                is_main=kind not in ('child.started','background.registered') and (
                    not previous or json.loads(previous[0])['task_kind']=='main')
                if is_main and db.execute('SELECT 1 FROM closed_sessions WHERE key=?',(session_key,)).fetchone():return
                for old_key,data in list(db.execute('SELECT key,data FROM tasks')):
                    older=json.loads(data)
                    if all(older[field]==event[field] for field in ('instance_id','session_id','task_id')) and older['generation']<event['generation']:
                        finish(old_key)
                task=json.loads(previous[0]) if previous else dict(
                    instance_id=event['instance_id'],provider=event['provider'],session_id=event['session_id'],
                    task_id=event['task_id'],generation=event['generation'],
                    task_kind='subagent' if kind=='child.started' else 'background' if kind=='background.registered' else 'main')
                task.update(owner=event['owner'],parent_task_id=event['parent_task_id'],
                    phase='waiting_permission' if kind=='task.waiting_permission' else 'running')
                db.execute('INSERT OR REPLACE INTO tasks VALUES(?,?)',(key,json.dumps(task)))
            if kind in STARTS or kind in FINISHES:
                db.execute('INSERT INTO generations VALUES(?,?) ON CONFLICT(key) DO UPDATE SET generation=MAX(generation,excluded.generation)',
                    (logical_key,event['generation']))
            # Tool/session-open metadata never revives a terminal or invents a task.
            # Pause affects intent only; all lifecycle transactions above continue.

    def pause(self):
        with self.connection() as db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('paused','true'))

    def resume(self):
        with self.connection() as db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('paused','false'))

    def reset(self, *, confirm=False):
        if confirm is not True:raise ContractError('RESET_CONFIRMATION_REQUIRED')
        with self.connection() as db:
            db.execute('INSERT OR IGNORE INTO ended SELECT key FROM tasks')
            db.execute('DELETE FROM tasks')
        # Independent cleanup: deliberately neither pauses nor resumes.

    def reap(self, observation):
        if observation is None:return
        if not isinstance(observation,dict):raise ContractError('INVALID_OBSERVATION')
        validated={}
        for pid,process in observation.items():
            if type(pid) is not int or pid<=0 or not isinstance(process,dict):raise ContractError('INVALID_OBSERVATION')
            validated[pid]=birth(process.get('birth'))
        with self.connection() as db:
            for key,data in list(db.execute('SELECT key,data FROM tasks')):
                task=json.loads(data);owner=task['owner']
                if validated.get(owner['pid'])==owner['birth']:continue
                db.execute('DELETE FROM tasks WHERE key=?',(key,))
                db.execute('INSERT OR IGNORE INTO ended VALUES(?)',(key,))

    def status(self):
        with self.connection() as db:
            row=db.execute('SELECT data FROM settings WHERE key="paused"').fetchone()
            paused=json.loads(row[0]) if row else False
            tasks=[json.loads(r[0]) for r in db.execute('SELECT data FROM tasks')]
        return dict(schema='awm.status/1',updated_at=utc_now(),paused=paused,
            active_task_count=len(tasks),lease_intent=bool(tasks and not paused),
            service_alive=None,lease_alive=None,amphetamine_active=None,last_error=None,
            instances=[dict(id=i['id'],active_count=sum(t['instance_id']==i['id'] for t in tasks))
                for i in self.config['instances']])
