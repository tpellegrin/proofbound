#!/usr/bin/env python3
"""Freeze an unrun paired pilot; makes isolated repositories, launches no agents."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def prepare(into):
    into=Path(into).resolve(); into.mkdir(parents=True,exist_ok=False)
    owner={k:subprocess.check_output(['git','-C',str(ROOT),'config','--local',k],text=True).strip() for k in ('user.name','user.email')}
    seed=into/'starting-project'; shutil.copytree(HERE/'project',seed,ignore=shutil.ignore_patterns('__pycache__'))
    for args in [('init','-q'),('config','user.name',owner['user.name']),('config','user.email',owner['user.email']),('add','.'),('commit','-qm','CSV summary pilot starting project')]:
        subprocess.run(['git','-C',str(seed),*args],check=True)
    baseline=subprocess.check_output(['git','-C',str(seed),'rev-parse','HEAD'],text=True).strip()
    for arm in ('direct','proofbound'):
        subprocess.run(['git','clone','--quiet','--no-hardlinks',str(seed),str(into/arm)],check=True)
    files=['goal.md','protocol.md','check_outcome.py']
    for name in files: shutil.copyfile(HERE/name,into/name)
    freeze={'format':'proofbound-paired-pilot-freeze-v1','status':'prepared-not-run',
            'starting_revision':baseline,
            'harness_revision':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
            'files':{name:hashlib.sha256((into/name).read_bytes()).hexdigest() for name in files},
            'starting_files':{str(p.relative_to(seed)):hashlib.sha256(p.read_bytes()).hexdigest() for p in seed.rglob('*') if p.is_file() and '.git' not in p.parts},
            'authorization':'none; preparation never launches a provider request'}
    (into/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    print(json.dumps({'prepared':str(into),'starting_revision':baseline,'launches':0},indent=2))

if __name__=='__main__': prepare(sys.argv[1])
