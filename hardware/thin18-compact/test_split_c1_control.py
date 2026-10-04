#!/usr/bin/env python3
"""Compile and run portable Split-C1 control tests; never connect to hardware."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from _split_c1_common import ROOT, REPO, repo_entry

SOURCES = [REPO/'firmware/split_c1'/name for name in
           ['board_control.hpp', 'board_control.cpp', 'tests/board_control_test.cpp']]
OUTPUT = ROOT/'split-c1-control-host-tests.json'


def main():
    # A failed rerun must not leave an older success report available for release.
    OUTPUT.unlink(missing_ok=True)
    compiler = shutil.which(os.environ.get('CXX', 'clang++'))
    if not compiler:
        raise RuntimeError('A C++17 compiler with address/undefined sanitizers is required; set CXX')
    inputs = {p.relative_to(REPO).as_posix(): repo_entry(p) for p in SOURCES+[Path(__file__).resolve()]}
    flags = ['-std=c++17', '-Wall', '-Wextra', '-Werror', '-pedantic', '-g', '-O1',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    version = subprocess.check_output([compiler, '--version'], text=True, timeout=10).splitlines()[0]
    work = REPO/'.work/split-c1-control'; work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='host-', dir=work) as temp:
        executable = Path(temp)/'board-control-test'
        subprocess.run([compiler, *flags, str(SOURCES[1]), str(SOURCES[2]), '-o', str(executable)],
                       check=True, cwd=REPO, timeout=90)
        result = subprocess.run([str(executable)], check=True, cwd=REPO, text=True,
                                capture_output=True, timeout=30)
        (work/'host-tests.log').write_text(result.stdout+result.stderr)
        counts = json.loads(result.stdout.splitlines()[-1])
        if counts.get('passed') is not True or counts.get('physical_hardware_tested') is not False:
            raise ValueError('Unexpected host test result')
    for name, entry in inputs.items():
        if repo_entry(REPO/name) != entry:
            raise RuntimeError('Control source changed while tests were executing: '+name)
    report = {'schema':'panda-split-c1-control-host-tests-v1', 'inputs':inputs,
              'compiler':version, 'flags':flags, **counts,
              'compiled_and_executed':True, 'target_firmware_integration_verified':False,
              'manufacturing_release':False}
    OUTPUT.write_text(json.dumps(report, indent=2)+'\n')
    print(result.stdout, end='')


if __name__=='__main__':
    main()
