#!/usr/bin/env python3
"""Public outcome checks, external to worker reports; not a reference implementation."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def check(project):
    project = Path(project).resolve()
    spec = importlib.util.spec_from_file_location('delivered_summary', project / 'summary.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    results = []
    def record(name, fn):
        try:
            fn(); results.append({'check': name, 'passed': True})
        except Exception as exc:
            results.append({'check': name, 'passed': False, 'detail': f'{type(exc).__name__}: {exc}'})
    def equal(actual, expected):
        if actual != expected: raise AssertionError(f'{actual!r} != {expected!r}')
    record('default compatibility', lambda: equal(module.totals(io.StringIO('category,amount\na,bad\na,2\n')), {'a':2}))
    record('strict aggregation', lambda: equal(module.totals(io.StringIO('amount,category\n +02 ,b\n-2,b\n0,a\n'), strict=True), {'b':0,'a':0}))
    record('header only valid', lambda: equal(module.totals(io.StringIO('category,amount\n'), strict=True), {}))
    invalid = [('', 'header'), ('category,category\na,2\n','header'),
               ('category,amount,extra\na,2,x\n','header'), ('category\na\n','header'),
               ('category,amount\n,2\n','2'), ('category,amount\na\n','2'),
               ('category,amount\na,2,x\n','2'), ('category,amount\na,2\nb,no\n','3'),
               ('category,amount\na,1_000\n','2'), ('category,amount\na,１２\n','2')]
    for n,(csv, marker) in enumerate(invalid):
        def rejected(csv=csv,marker=marker):
            try: module.totals(io.StringIO(csv), strict=True)
            except ValueError as exc:
                if marker not in str(exc).lower(): raise AssertionError('error lacks location')
            else: raise AssertionError('invalid input accepted')
        record(f'invalid input {n}', rejected)
    def cli():
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/'input data.csv'; file.write_text('category,amount\na,2\nb,bad\n')
            cp=subprocess.run([sys.executable,str(project/'cli.py'),'--strict',str(file)],capture_output=True,text=True,timeout=10)
            equal(cp.returncode,2); equal(cp.stdout,'')
            if '3' not in cp.stderr: raise AssertionError('CLI error lacks row location')
            file.write_text('category,amount\nb,2\na,1\n')
            cp=subprocess.run([sys.executable,str(project/'cli.py'),'--strict',str(file)],capture_output=True,text=True,timeout=10)
            equal(cp.returncode,0); equal(cp.stdout,'a: 1\nb: 2\n')
    record('CLI strict error and valid order',cli)
    cp=subprocess.run([sys.executable,'-m','unittest','discover'],cwd=project,capture_output=True,text=True,timeout=30)
    results.append({'check':'project checks','passed':cp.returncode==0,'detail':cp.stderr[-2000:]})
    return {'project':str(project),'checks':results,'passed':all(r['passed'] for r in results)}

if __name__=='__main__':
    report=check(sys.argv[1]); print(json.dumps(report,indent=2)); sys.exit(0 if report['passed'] else 1)
