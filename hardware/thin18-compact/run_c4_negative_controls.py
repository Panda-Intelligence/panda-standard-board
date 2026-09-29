#!/usr/bin/env python3
import csv,json,shutil,subprocess,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
VERIFY=ROOT/'verify_c4.py'
tests=[]

def run_expect_fail(name, mutator, paths):
    backups={}
    try:
        for p in paths:
            p=ROOT/p
            backups[p]=p.read_bytes()
        mutator()
        cp=subprocess.run(['python3',str(VERIFY)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        ok=cp.returncode==2
        tests.append({'name':name,'exit':cp.returncode,'passed':ok})
        if not ok: raise SystemExit(f'negative control did not fail: {name}, exit={cp.returncode}')
    finally:
        for p,b in backups.items(): p.write_bytes(b)

def mut_mpn():
    base=ROOT/'c4c-96x68-domestic-passives/eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16'
    # C302 is in the root schematic. Mutate source metadata, not generated verification evidence.
    p=base/'PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_sch'
    s=p.read_text()
    marker='(property "Reference" "C302"'
    i=s.index(marker)
    j=s.find('(property "MPN" "0402B104K250NT"',i)
    if j < 0: raise SystemExit('C302 selected MPN source field not found')
    s=s[:j]+s[j:].replace('0402B104K250NT','BROKEN_MPN',1)
    p.write_text(s)
run_expect_fail('selected schematic MPN mutation rejected',mut_mpn,['c4c-96x68-domestic-passives/eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_sch'])

def mut_ref():
    p=ROOT/'c4-domestic-ref-status.csv'
    rows=list(csv.reader(p.open(encoding='utf-8-sig')))
    rows=rows[:-1]
    with p.open('w',newline='',encoding='utf-8') as f: csv.writer(f,lineterminator='\n').writerows(rows)
run_expect_fail('missing ref status rejected',mut_ref,['c4-domestic-ref-status.csv'])

def mut_phy():
    p=ROOT/'c4-qualification-gates.json'; d=json.load(open(p)); d['gates'][0][2]='PASS'; d['physical_tests_completed']=1; p.write_text(json.dumps(d,indent=2)+'\n')
run_expect_fail('physical PASS without raw measurements rejected',mut_phy,['c4-qualification-gates.json'])

def mut_switch():
    p=ROOT/'c4-power-architecture.json'; d=json.load(open(p)); d['load_switch_policy']['domesticization_status']='SELECTED'; p.write_text(json.dumps(d,indent=2)+'\n')
run_expect_fail('unsafe load-switch selection rejected',mut_switch,['c4-power-architecture.json'])

cp=subprocess.run(['python3',str(VERIFY),'--release'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
tests.append({'name':'release gate blocked','exit':cp.returncode,'passed':cp.returncode==2})
if cp.returncode!=2: raise SystemExit('release gate negative control failed')

report={'date':'2026-09-29','tests':tests,'passed':all(t['passed'] for t in tests)}
(ROOT/'c4-negative-controls.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
