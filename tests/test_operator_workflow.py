"""Credential-free public front door. Stand-ins validate mechanics, never agent quality."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/pb_workflow.py"
FAKE = r'''#!PYTHON
import hashlib, json, os, pathlib, re, sqlite3, sys, time
args = sys.argv[1:]
db = pathlib.Path(os.environ['OPENCODE_DB'])
if args[:2] == ['session', 'list']:
    with sqlite3.connect(db) as conn:
        print(json.dumps([{'id': s, 'title': t} for s,t in conn.execute('select id,title from session')]))
    sys.exit()
title = args[args.index('--title')+1]
sid = 'ses_' + hashlib.sha256(title.encode()).hexdigest()[:12]
role = title.split(':')[2]
report = pathlib.Path(re.search(r'^Report: (.+)$', args[-1], re.M).group(1))
if role == 'spec-author':
    next(pathlib.Path('specs').glob('*/requirements.md')).write_text('# Requirements\n\nR1: add greeting(name) returning Hello, followed by the name. Preserve existing APIs.\nR2: test it with unittest.\n')
if role in ('implementer', 'fixer'):
    pathlib.Path('greeting.py').write_text('def greeting(name):\n    return "Hello, " + name\n')
    pathlib.Path('test_greeting.py').write_text('import unittest\nfrom greeting import greeting\nclass GreetingTest(unittest.TestCase):\n    def test_name(self): self.assertEqual(greeting("Ada"), "Hello, Ada")\n')
report.write_text('# Stand-in report\n\nDeterministic mechanics only, no semantic review performed.\n')
db.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(db) as conn:
    conn.execute('create table if not exists session (id text, title text)')
    conn.execute('create table if not exists message (id text, session_id text, time_created integer, data text)')
    conn.execute('create table if not exists part (id text, message_id text, data text)')
    conn.execute('insert into session values (?,?)', (sid,title))
    conn.execute('insert into message values (?,?,?,?)', (sid,sid,int(time.time()*1000),json.dumps({'role':'assistant'})))
    for kind in ('step-start','step-finish'):
        conn.execute('insert into part values (?,?,?)',(sid+kind,sid,json.dumps({'type':kind,'cost':0,'tokens':{'input':10,'output':5,'cache':{'read':0,'write':0}}})))
'''

class OperatorWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb first use "))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = self.tmp / "ordinary project"; self.project.mkdir()
        (self.project / '.gitignore').write_text('DeepSeekAndDestroy/\n__pycache__/\n')
        (self.project / 'README.md').write_text('# Greeting library\n')
        for args in [('init','-q'), ('config','user.name','Test Owner'), ('config','user.email','owner@example.invalid'), ('add','.'), ('commit','-qm','initial')]:
            subprocess.run(['git', '-C', str(self.project), *args], check=True)
        self.fake = self.tmp / 'bin/opencode'; self.fake.parent.mkdir()
        self.fake.write_text(FAKE.replace('PYTHON',sys.executable)); self.fake.chmod(0o755)
        result = self.cli('start','--project',self.project,'--goal','Add a greeting function and tests.','--check',f'{sys.executable} -m unittest discover','--executor',self.fake)
        self.runroot = Path(result['run'])
        c = json.loads((self.runroot / 'run-config.json').read_text())
        self.addCleanup(shutil.rmtree, Path(c['home']).parent, True)
        # Test-only injected stand-in: exact executable, empty HOME, no auth or real PATH fallback.
        c['mode'] = 'offline-test'
        c['policy'] = dict(aggregate_limit=1, reserve=.05, launch_ceiling=12, repair_cycles=1)
        c['auto_flag'] = ''
        (self.runroot / 'run-config.json').write_text(json.dumps(c))
        self.config = c

    def cli(self, *args, ok=True):
        cp = subprocess.run([sys.executable,str(CLI),*map(str,args)],capture_output=True,text=True)
        if ok: self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
        else: self.assertNotEqual(cp.returncode,0,cp.stdout)
        return json.loads(cp.stdout)

    def action(self, name='status', *extra, ok=True):
        return self.cli(name,'--run',self.runroot,*extra,ok=ok)

    def reach(self, name):
        for _ in range(25):
            s=self.action()
            if s.get('task')==name and s['action']=='adjudicate': return s
            if s['action']=='adjudicate': self.action('decide','--decision','accept','--reason','TEST ONLY: scripted decision, not agent evidence')
            else:
                result=self.action('continue')
                if 'launch' in result:
                    self.assertEqual(result['launch'].get('returncode'),0,result)
        self.fail('did not reach '+name)

    def test_goal_to_delivery_and_fresh_process_continuation(self):
        initial=json.loads((self.runroot/'state.json').read_text())
        self.assertFalse(initial['phases']['design']['tasks'])
        self.reach('implementation')
        self.action('decide','--decision','accept','--reason','TEST ONLY scripted acceptance')
        report=self.tmp/'final.md'; report.write_text('Added greeting and regression check. No unresolved issues in stand-in; not a real-agent trial.')
        result=self.action('finish','--report',report,'--report-source','relayed')
        delivery=Path(result['delivery'])
        self.assertIn('greeting.py',(delivery/'change.patch').read_text())
        self.assertEqual(json.loads((delivery/'handoff.json').read_text())['report_source'],'relayed')
        self.assertTrue(list(self.runroot.rglob('reviewer-1/terminal.json')))
        self.assertTrue(list(self.runroot.rglob('spec-reflector-1/terminal.json')))

    def test_never_earned_consistency_refuses_then_legitimately_earns_it(self):
        self.reach('consistency')  # clean gate is present, but no semantic acceptance
        state=(self.runroot/'state.json').read_bytes()
        self.action('admit',ok=False)
        self.assertEqual((self.runroot/'state.json').read_bytes(),state)
        self.assertFalse(list(self.runroot.rglob('implementer-*/terminal.json')))
        refusals=[json.loads(p.read_text()) for p in (self.runroot/'receipts').glob('*.json')]
        self.assertTrue(any(r['action']=='pb_execution admit' and r['result'].get('refused') for r in refusals))
        self.action('decide','--decision','accept','--reason','TEST ONLY consistency judgment')
        self.action('continue')
        self.action('admit')
        self.action('continue')
        self.assertTrue(list(self.runroot.rglob('implementer-1/terminal.json')))

    def test_missing_derived_record_recovers_from_accepted_evidence(self):
        self.reach('consistency')
        self.action('decide','--decision','accept','--reason','TEST ONLY consistency judgment')
        self.action('continue')
        records=list(Path(self.config['paths']['consistency']).glob('*.json')); self.assertEqual(len(records),1)
        records[0].unlink()
        self.action('admit',ok=False)
        self.assertEqual(self.action()['action'],'record-consistency')
        self.action('continue')
        self.action('admit')
        self.action('continue')
        self.assertTrue(list(self.runroot.rglob('implementer-1/terminal.json')))

    def test_admitted_c1_continues_after_later_requirement_movement(self):
        self.reach('consistency')
        self.action('decide','--decision','accept','--reason','TEST ONLY consistency')
        self.action('continue')
        self.action('admit')
        original=json.loads((self.runroot/'state.json').read_text())['phases']['build']['tasks']['implementation']['admission']
        req=Path(self.config['requirements']); req.write_text(req.read_text()+'\nLater intent, outside C1.\n')
        launched=self.action('continue')['launch']
        self.assertEqual(launched['returncode'],0,launched)
        current=json.loads((self.runroot/'state.json').read_text())['phases']['build']['tasks']['implementation']['admission']
        self.assertEqual(original,current)
        self.assertTrue(list(self.runroot.rglob('implementer-1/terminal.json')))

    def test_project_edit_after_review_cannot_be_accepted(self):
        self.reach('implementation')
        (self.project/'greeting.py').write_text('def greeting(name): return "wrong"\n')
        result=self.action('decide','--decision','accept','--reason','TEST ONLY stale attempt',ok=False)
        self.assertIn('changed since',result['error'])
        state=json.loads((self.runroot/'state.json').read_text())
        self.assertNotEqual(state['phases']['build']['tasks']['implementation']['status'],'accepted')

    def test_consistency_defect_can_return_to_requirements_without_json_editing(self):
        self.reach('consistency')
        old=list(self.runroot.rglob('requirements/contracts/*.md'))[0].read_bytes()
        self.action('revise','--reason','Within goal: make greeting punctuation explicit.')
        state=json.loads((self.runroot/'state.json').read_text())
        self.assertEqual(state['phases']['design']['tasks']['requirements']['current_contract']['revision'],2)
        self.assertEqual(list(self.runroot.rglob('requirements/contracts/r0001.md'))[0].read_bytes(),old)
        self.reach('requirements')

    def test_c1_record_recovers_after_admission_and_later_intent(self):
        self.reach('consistency')
        self.action('decide','--decision','accept','--reason','TEST ONLY consistency')
        self.action('continue'); self.action('admit')
        records=list(Path(self.config['paths']['consistency']).glob('*.json'))
        original=records[0].read_bytes(); records[0].unlink()
        req=Path(self.config['requirements']); req.write_text(req.read_text()+'\nLater C2 intent.\n')
        self.assertEqual(self.action()['action'],'record-consistency')
        self.action('continue')
        self.assertEqual(records[0].read_bytes(),original)
        self.assertEqual(self.action('continue')['launch']['returncode'],0)

    def test_requirements_edit_after_review_cannot_be_accepted(self):
        self.reach('requirements')
        req=Path(self.config['requirements']); req.write_text(req.read_text()+'\nUnreviewed requirement.\n')
        result=self.action('decide','--decision','accept','--reason','TEST ONLY stale',ok=False)
        self.assertIn('changed since',result['error'])

    def test_requirements_edit_after_acceptance_cannot_enter_ledger(self):
        self.reach('requirements')
        self.action('decide','--decision','accept','--reason','TEST ONLY fresh')
        req=Path(self.config['requirements']); req.write_text(req.read_text()+'\nUnreviewed requirement.\n')
        result=self.action('continue',ok=False)
        self.assertIn('changed since',result['error'])
        self.assertFalse(json.loads(Path(self.config['paths']['ledger']).read_text())['artifacts'])

    def test_owner_request_survives_fresh_status_until_explicit_resolution(self):
        self.reach('requirements')
        self.action('decide','--decision','owner','--reason','Owner must resolve contradictory compatibility constraints.')
        blocked=self.action()
        self.assertEqual(blocked['action'],'blocked')
        self.assertIn('contradictory',blocked['owner_request'])
        self.action('decide','--decision','accept','--reason','No owner response yet',ok=False)
        restored=self.action('resolve-owner','--owner-response','TEST ONLY owner resolves the public constraint.')
        self.assertEqual(restored['action'],'adjudicate')

    def test_deterministic_preflight_refusal_keeps_slot_available(self):
        self.action('continue')
        path=self.runroot/'run-config.json'; c=json.loads(path.read_text())
        c['interpreter']['version']='0.0.0'; path.write_text(json.dumps(c))
        refused=self.action('continue')['launch']
        self.assertFalse(refused['executor_reached'])
        self.assertFalse((self.runroot/'launch-ledger.json').exists())
        c['interpreter']['version']='.'.join(map(str,sys.version_info[:3])); path.write_text(json.dumps(c))
        original=self.fake.read_bytes(); self.fake.write_bytes(original+b'\n# changed bytes\n')
        refused=self.action('continue')['launch']
        self.assertFalse(refused['executor_reached'])
        self.assertFalse((self.runroot/'launch-ledger.json').exists())
        self.fake.write_bytes(original)
        self.assertEqual(self.action('continue')['launch']['returncode'],0)
        receipts=[json.loads(p.read_text()) for p in (self.runroot/'receipts').glob('*.json')]
        self.assertEqual(sum(r['action']=='launch preflight' for r in receipts),2)

    def test_repeat_start_is_safe_and_goal_change_is_refused(self):
        """Repeating `start` identically is safe; a changed goal is refused."""
        same=self.cli('start','--project',self.project,'--goal','Add a greeting function and tests.',
                      '--check',self.config['check_command'],'--executor',self.fake)
        self.assertTrue(same['existing'])
        self.assertTrue(same['configuration_unchanged'])
        self.cli('start','--project',self.project,'--goal','A different goal','--check','unused',ok=False)

    def test_repeat_start_with_a_different_check_names_the_conflict(self):
        """It used to return `existing: true` and silently keep the old command.

        The caller had no way to learn their new `--check` had been discarded, and the run went on
        validating acceptance with a command they thought they had replaced.
        """
        cp=subprocess.run([sys.executable,str(CLI),'start','--project',str(self.project),
                           '--goal','Add a greeting function and tests.',
                           '--check',f'{sys.executable} -m pytest -q','--executor',str(self.fake)],
                          capture_output=True,text=True)
        self.assertEqual(cp.returncode,2,cp.stdout)
        error=json.loads(cp.stdout)['error']
        self.assertIn('NOT applied',error)
        self.assertIn('--check',error)
        self.assertIn('pytest',error)
        # And nothing changed.
        self.assertEqual(json.loads((self.runroot/'run-config.json').read_text())['check_command'],
                         self.config['check_command'])

    def test_unresolved_launch_blocks_spending_on_resume(self):
        self.action('continue')
        sys.path.insert(0,str(ROOT/'scripts'))
        from _launch_budget import LaunchLedger
        ledger=LaunchLedger(self.runroot/'launch-ledger.json',limit=1,reserve=.05,ceiling=12)
        ledger.reserve(phase='design',task='requirements',role='spec-author')
        result=self.action('continue')['launch']
        self.assertFalse(result['admitted']); self.assertIn('never classified',' '.join(result['why']))
        self.assertFalse(list(self.runroot.rglob('terminal.json')))

    def test_pending_repair_survives_a_fresh_status_until_it_is_carried_out(self):
        """A decided repair used to vanish the moment the deciding process exited.

        `decide --decision repair` on consistency returns a `revise` instruction and changes no
        task state, so a fresh `status` re-proposed adjudication as though nothing had been
        decided — inviting a resuming coordinator to adjudicate the same evidence twice.
        """
        self.reach('consistency')
        self.action('decide','--decision','repair','--reason','REPAIR: requirement R2 contradicts R1 on ordering')
        fresh=self.action()
        self.assertEqual(fresh['action'],'blocked')
        self.assertIn('R2 contradicts R1',fresh['pending_repair'])
        self.assertTrue(fresh['request_receipt'])
        self.assertIn('revise',fresh['next'])
        # It survives repeated fresh reads, because it is derived from durable receipts.
        self.assertEqual(self.action()['pending_repair'],fresh['pending_repair'])
        # And carrying it out clears it.
        self.action('revise','--reason','R2 reworded to defer ordering to R1; witness: both claimed precedence')
        self.assertNotEqual(self.action().get('action'),'blocked')

    def test_a_sealed_delivery_reports_completion_not_another_finish(self):
        """`status` used to propose `finish`, which then refused to overwrite the delivery.

        The next action a resuming coordinator was told to take could not succeed.
        """
        self.reach('implementation')
        self.action('decide','--decision','accept','--reason','TEST ONLY scripted acceptance')
        report=self.tmp/'final.md'; report.write_text('Stand-in mechanics; not real-agent evidence.')
        sealed=self.action('finish','--report',report,'--report-source','relayed')
        after=self.action()
        self.assertEqual(after['action'],'complete')
        self.assertEqual(after['delivery'],sealed['delivery'])
        self.assertIsNone(after['next'])
        self.assertTrue(Path(after['inspect']['patch']).is_file())
        self.assertIn('git',after['inspect']['apply'])
        self.assertEqual(after['report_source'],'relayed')
        # A second finish says it is already done, not that acceptance is missing.
        again=self.action('finish','--report',report,'--report-source','relayed',ok=False)
        self.assertIn('already has a sealed delivery',again['error'])

    def test_acceptance_check_does_not_invalidate_the_review_it_checks(self):
        """An ordinary Python project that does not gitignore bytecode could not be accepted.

        `decide accept` runs the project check, which wrote `__pycache__/*.pyc` into the project;
        the stale-review guard then saw those bytes as a change and refused. Every fixture here
        gitignored `__pycache__`, so the suite never noticed. This project deliberately does not.
        """
        (self.project/'.gitignore').write_text('DeepSeekAndDestroy/\n')
        subprocess.run(['git','-C',str(self.project),'add','.gitignore'],check=True)
        subprocess.run(['git','-C',str(self.project),'commit','-qm','stop ignoring bytecode'],check=True)
        self.reach('implementation')
        accepted=self.action('decide','--decision','accept','--reason','TEST ONLY scripted acceptance')
        self.assertEqual(accepted['action'],'finish')
        stray=sorted(p.name for p in self.project.rglob('*.pyc'))
        self.assertEqual(stray,[],'the acceptance check must not write bytecode into the project')

    def test_a_bounded_check_that_hangs_is_unknown_not_failed(self):
        c=dict(self.config); c['check_command']=f'{sys.executable} -c "import time; time.sleep(600)"'
        c['check_timeout_seconds']=3
        (self.runroot/'run-config.json').write_text(json.dumps(c))
        self.reach('implementation')
        blocked=self.action('decide','--decision','accept','--reason','TEST ONLY scripted acceptance',ok=False)
        self.assertIn('did not finish within 3s',blocked['error'])
        receipts=[json.loads(p.read_text()) for p in (self.runroot/'receipts').glob('*.json')]
        timed=[r for r in receipts if r['result'].get('timed_out')]
        self.assertTrue(timed)
        self.assertIsNone(timed[0]['result']['returncode'],'a check that did not finish has no verdict')
        self.assertIn('is unknown',timed[0]['result']['note'])


if __name__=='__main__': unittest.main()
