"""Anomalous accounting is unknown, never free work."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from _usage_events import events_from_db
from _launch_budget import spend, LaunchLedger

class AttemptIdentities(unittest.TestCase):
    def test_nested_attempt_names_remain_distinct_and_flat_names_stay_compatible(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); run=root/'run'; run.mkdir()
            ledger=LaunchLedger(root/'ledger.json')
            identities=['attempts/reviewer-1',
                        'phases/design/tasks/requirements/attempts/spec-reflector-1',
                        'phases/design/tasks/consistency/attempts/spec-reflector-1']
            for identity in identities:
                event=run/identity; event.mkdir(parents=True)
                slot=ledger.reserve(phase='design',task=identity,role='spec-reflector',note='offline identity check')
                ledger.classify(slot['slot'],run_root=run,event_dir=event,
                                launcher_returncode=2,launcher_output='no executor launched')
            self.assertEqual(ledger.own_event_dirs(),['reviewer-1',*identities[1:]])
            self.assertEqual(LaunchLedger(root/'ledger.json').own_event_dirs(),ledger.own_event_dirs())

class UsageAnomalies(unittest.TestCase):
    def test_malformed_or_missing_token_counts_are_retained_and_block(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); db=root/'worker.db'; run=root/'run'; run.mkdir()
            with closing(sqlite3.connect(db)) as conn:
                conn.execute('create table session (id text,title text)')
                conn.execute('create table message (id text,session_id text,time_created integer,data text)')
                conn.execute('create table part (id text,message_id text,data text)')
                conn.execute('insert into session values ("s","t")')
                conn.execute('insert into message values ("m","s",1,?)',(json.dumps({'role':'assistant'}),))
                conn.execute('insert into part values ("p","m",?)',(json.dumps({'type':'step-finish','tokens':{'input':-3,'output':2}}),))
                conn.execute('insert into part values ("broken","m","not JSON")')
                conn.commit()
            events=events_from_db(db)
            self.assertTrue(events['anomalies'])
            self.assertIn('broken',{a['part_id'] for a in events['anomalies']})
            account=spend(run,db)
            self.assertFalse(account['complete']); self.assertIsNone(account['derived'])
            self.assertTrue(account['anomalies'])

class DatedCallPricing(unittest.TestCase):
    def account(self, second_stamp):
        from datetime import datetime, timezone
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name); db = root / 'worker.db'; run = root / 'run'
        event = run / 'attempts' / 'implementer-1'; event.mkdir(parents=True)
        (event / 'attempt.json').write_text(json.dumps({'started_at':'2026-09-21T00:30:00+00:00'}))
        (event / 'terminal.json').write_text(json.dumps({'status':'completed','session_id':'s'}))
        first = int(datetime(2026,9,21,0,30,tzinfo=timezone.utc).timestamp()*1000)
        with closing(sqlite3.connect(db)) as conn:
            conn.execute('create table session (id text,title text)')
            conn.execute('create table message (id text,session_id text,time_created integer,data text)')
            conn.execute('create table part (id text,message_id text,data text)')
            conn.execute('insert into session values ("s","t")')
            for n, stamp in enumerate((first, second_stamp)):
                mid = str(n)
                conn.execute('insert into message values (?,"s",?,?)',(mid,stamp,json.dumps({'role':'assistant'})))
                for kind in ('step-start','step-finish'):
                    part = {'type':kind,'tokens':{'input':1000000,'output':0,'cache':{'read':0,'write':0}}}
                    conn.execute('insert into part values (?,?,?)',(mid+kind,mid,json.dumps(part)))
            conn.commit()
        return spend(run, db)

    def test_crossing_peak_window_prices_each_finished_call(self):
        from datetime import datetime, timezone
        second = int(datetime(2026,9,21,1,30,tzinfo=timezone.utc).timestamp()*1000)
        result = self.account(second)
        self.assertTrue(result['complete'], result)
        self.assertEqual(result['derived'], .66)  # .22 off peak plus .44 peak, not .44 total
        self.assertEqual([c['window'] for c in result['cost']['calls']], ['off-peak','peak'])
        self.assertTrue(result['session_attribution']['per_attempt_attribution_established'])

    def test_missing_call_timestamp_keeps_spend_unknown(self):
        result = self.account(None)
        self.assertFalse(result['complete'])
        self.assertIsNone(result['derived'])
        self.assertIn('timestamp', result['cost']['reason'])
