"""Outcome-check sensitivity, not real-agent evaluation or a reference answer."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]/'examples/csv-summary'
spec=importlib.util.spec_from_file_location('pilot_checker',HERE/'check_outcome.py')
checker=importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)

class PilotChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix='pb-pilot-mutant-'))
        self.addCleanup(shutil.rmtree,self.tmp,True)
        self.project=self.tmp/'project'
        shutil.copytree(HERE/'project',self.project,ignore=shutil.ignore_patterns('__pycache__'))

    def test_ignoring_strict_is_detected_without_breaking_default_compatibility(self):
        path=self.project/'summary.py'
        path.write_text(path.read_text().replace('def totals(stream):','def totals(stream, strict=False):'))
        report=checker.check(self.project)
        by={r['check']:r['passed'] for r in report['checks']}
        self.assertTrue(by['default compatibility'])
        self.assertTrue(by['strict aggregation'])
        self.assertFalse(by['invalid input 0'])
        self.assertFalse(by['invalid input 7'])
        self.assertFalse(report['passed'])

    def test_rejecting_valid_input_is_detected(self):
        path=self.project/'summary.py'
        path.write_text(path.read_text().replace('def totals(stream):','def totals(stream, strict=False):\n    if strict: raise ValueError("header")'))
        by={r['check']:r['passed'] for r in checker.check(self.project)['checks']}
        self.assertFalse(by['strict aggregation'])
        self.assertFalse(by['header only valid'])

    def test_partial_cli_output_on_error_is_detected(self):
        (self.project/'cli.py').write_text('import sys\nprint("partial summary")\nprint("invalid row 3",file=sys.stderr)\nsys.exit(2)\n')
        by={r['check']:r['passed'] for r in checker.check(self.project)['checks']}
        self.assertFalse(by['CLI strict error and valid order'])
