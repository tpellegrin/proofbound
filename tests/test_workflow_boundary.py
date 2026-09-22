"""Bounded host/staged-home observation, no credentials and no provider calls."""
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from _execution_view import Policy, SYSTEM_EXECS, _profile
from _workflow_boundary import probe, stage_interpreter, profile_text

@unittest.skipUnless(sys.platform=='darwin','macOS sandbox-exec only; no Linux qualification')
class BoundaryProbe(unittest.TestCase):
    def test_real_absolute_path_is_denied_and_staged_home_is_permitted(self):
        root=Path(tempfile.mkdtemp(prefix='pb-boundary-',dir='/private/tmp'))
        self.addCleanup(shutil.rmtree,root,True)
        allowed=root/'view'; allowed.mkdir()
        home=allowed/'home'; home.mkdir()
        outside=root/'host-sentinel'; outside.write_text('private marker, never returned')
        tools=allowed/'tools'; tools.mkdir()
        reads=[str(Path(sys.prefix).resolve()),str(Path(sys.executable).resolve().parents[1]),'/opt/homebrew/Cellar','/opt/homebrew/opt','/opt/homebrew/lib']
        profile=allowed/'boundary.sb'; profile.write_text(profile_text(allowed,tools,allowed,Policy(extra_reads=reads,system_execs=(*SYSTEM_EXECS,*reads))))
        result=probe(profile,home=home,cwd=allowed,paths={'real_host':outside,'staged_home':home})
        self.assertEqual(result.get('returncode'),0,result)
        self.assertFalse(result['checks']['real_host']['readable'])
        self.assertIn(result['checks']['real_host']['errno'],(1,13))
        self.assertTrue(result['checks']['staged_home']['readable'])
        self.assertNotIn('private marker',json.dumps(result))
        stage_interpreter(tools)
        child=subprocess.run(['/usr/bin/sandbox-exec','-f',str(profile),'/bin/sh','-c',
                              'python3 -c "import sys; print(sys.executable)"'],
                             cwd=allowed,env={'HOME':str(home),'PATH':str(tools)+':/usr/bin:/bin'},
                             capture_output=True,text=True,timeout=20)
        self.assertEqual(child.returncode,0,child.stderr)
        self.assertEqual(Path(child.stdout.strip()).resolve(),Path(sys.executable).resolve())
        original=root/'host-tool'; original.write_text('original executable bytes')
        staged=tools/'executor'; os.link(original,staged)
        for protected in (staged, profile):
            attempted=subprocess.run(['/usr/bin/sandbox-exec','-f',str(profile),sys.executable,
                                      '-c','import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("changed")',str(protected)],
                                     cwd=allowed,env={'HOME':str(home),'PATH':str(tools)+':/usr/bin:/bin'},
                                     capture_output=True,text=True,timeout=20)
            self.assertNotEqual(attempted.returncode,0)
            self.assertIn('PermissionError',attempted.stderr)
        self.assertEqual(original.read_text(),'original executable bytes')
