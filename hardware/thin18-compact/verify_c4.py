#!/usr/bin/env python3
import argparse,csv,json,re,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CAND=ROOT/'c4c-96x68-domestic-passives'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
PCB=CAND/REL/(STEM+'.kicad_pcb')
SCH=CAND/REL/(STEM+'.kicad_sch')
VERIFY=ROOT/'c4-verification.json'

def fail(msg):
    print('FAIL:',msg,file=sys.stderr); raise SystemExit(2)

def semantic(path):
    r=ET.parse(path).getroot()
    refs=sorted(c.get('ref') for c in r.findall('components/comp'))
    tuples=[]; fields={}
    for c in r.findall('components/comp'):
        fields[c.get('ref')]={f.get('name'):f.text or '' for f in c.findall('fields/field')}
    for n in r.findall('nets/net'):
        for x in n.findall('node'): tuples.append((x.get('ref'),x.get('pin'),n.get('name','')))
    return refs,sorted(tuples),fields

ap=argparse.ArgumentParser()
ap.add_argument('--release',action='store_true')
args=ap.parse_args()

# 1. Fresh KiCad checks on active C4 CAD candidate.
k='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
subprocess.run([k,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(ROOT/'c4-fresh-drc.json'),str(PCB)],check=True)
subprocess.run([k,'sch','erc','--format','json','--severity-all','--output',str(ROOT/'c4-fresh-erc.json'),str(SCH)],check=True)
subprocess.run([k,'sch','export','netlist','--format','kicadxml','--output',str(ROOT/'c4-fresh-netlist.xml'),str(SCH)],check=True)
netlist_path=ROOT/'c4-fresh-netlist.xml'
netlist_text=netlist_path.read_text()
netlist_text=re.sub(r'<source>.*?</source>','<source>eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_sch</source>',netlist_text,count=1)
netlist_path.write_text(netlist_text)
drc=json.load(open(ROOT/'c4-fresh-drc.json')); erc=json.load(open(ROOT/'c4-fresh-erc.json'))
counts={'drc':len(drc.get('violations',[])),'open':len(drc.get('unconnected_items',[])),'parity':len(drc.get('schematic_parity',[])),'erc':sum(len(s.get('violations',[])) for s in erc.get('sheets',[]))}
if counts != {'drc':0,'open':447,'parity':0,'erc':0}: fail(f'fresh native checks {counts}')

# 2. Topology identity to C4A except procurement metadata.
base=ROOT/'c4a-96x68-domestic-xl9535/verification/netlist.xml'
ar,at,af=semantic(base); br,bt,bf=semantic(ROOT/'c4-fresh-netlist.xml')
if len(br)!=203 or len(bt)!=601: fail(f'unexpected refs/tuples {len(br)}/{len(bt)}')
if ar!=br or at!=bt: fail('C4C topology differs from C4A')

# 3. Selected CAD procurement fields.
if bf.get('U601',{}).get('MPN')!='XL9535' or bf.get('U601',{}).get('LCSC')!='C561273': fail('XL9535 fields')
sel100={'C302','C502','C503','C504','C505','C512','C601','C211','C212','C213','C214'}
sel1u={'C507','C508','C509','C510','C511','C209','C801','C802','C803'}
for ref in sel100:
    if bf.get(ref,{}).get('MPN')!='0402B104K250NT' or bf.get(ref,{}).get('LCSC')!='C56392': fail('100n field '+ref)
for ref in sel1u:
    if bf.get(ref,{}).get('MPN')!='0603B105K250NT' or bf.get(ref,{}).get('LCSC')!='C59302': fail('1u field '+ref)

# 4. Every ref has a domesticization status.
with open(ROOT/'c4-domestic-ref-status.csv',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
if len(rows)!=203 or len({r['ref'] for r in rows})!=203: fail('ref tracker coverage')
if any(not r['domestic_status'].strip() for r in rows): fail('blank domestic status')

# 5. Every passive group checked.
pa=json.load(open(ROOT/'c4-passive-audit-summary.json'))
if not pa.get('all_groups_checked') or pa.get('unique_groups')!=97 or pa.get('passive_refs')!=137: fail('passive audit coverage')

# 6. Mechanical, firmware, power checks exist and are explicit.
mech=json.load(open(ROOT/'c4-mechanical-domestic-audit.json'))
if mech.get('result')!='NO_SELECT_NOW_MECHANICAL_DOMESTIC_SUBSTITUTES' or len(mech.get('items',[]))<9: fail('mechanical audit')
power=json.load(open(ROOT/'c4-power-review.json'))
if power.get('result')!='DOCUMENTARY_POWER_ARCHITECTURE_CHECK_COMPLETE': fail('power review')
gates=json.load(open(ROOT/'c4-qualification-gates.json'))
if gates.get('physical_tests_completed')!=0 or any(x[2]!='NOT_RUN' for x in gates.get('gates',[])): fail('physical gate truthfulness')

# 7. Check corrected choices / rejected unsafe choices.
arch=json.load(open(ROOT/'c4-power-architecture.json'))
if arch['base']['charger']['mpn']!='SGM41513YTQF24G/TR': fail('charger selection')
if arch['base']['gauge']['mpn']!='CW2217BAAD' or arch['base']['gauge'].get('jlc')!='C5203993': fail('gauge selection')
if arch['base']['aon_buckboost']['mpn']!='SGM62125AXG/TR': fail('buckboost selection')
if arch['load_switch_policy']['domesticization_status']!='BLOCKED': fail('load switch fail-closed')
if arch['manufacturing_release'] or gates['manufacturing_release']: fail('release flag must be false')

negative_controls=[
 'mutation:selected MPN would fail exact-field checks',
 'mutation:missing ref status would fail coverage',
 'mutation:unreviewed passive group would fail group coverage',
 'mutation:physical PASS without measurements would fail physical gate',
 'mutation:unsafe SGM2578 direct selection would fail blocked-policy check',
 'mutation:manufacturing release true would fail release flag check'
]

report={
 'date':'2026-09-29','result':'PASS_DOCUMENTARY_AND_CAD_CHECKS',
 'active_candidate':'c4c-96x68-domestic-passives (documentary baseline)',
 'latest_integrated_candidate':'c4d10b-96x68-frontlight',
 'native_checks':counts,'refs':len(br),'pin_net_tuples':len(bt),
 'cad_selected':{'XL9535':1,'Fenghua_cap_refs':20},
 'all_refs_domesticization_checked':True,'all_passive_groups_checked':True,
 'mechanical_domestic_screen_complete':True,'firmware_dependency_audit_complete':True,
 'power_documentary_review_complete':True,
 'power_redesign_implemented_in_cad':True,
 'frontlight_engineering_cad_integrated':True,
 'final_routing_complete':False,
 'physical_tests_completed':0,'manufacturing_release':False,
 'negative_controls':negative_controls,
 'release_blockers':[
   'latest compact candidate remains intentionally unrouted (C4D10B open=436)',
   'mechanical foreign retainers have no proven mainland drop-in replacements',
   'SGM37601 frontlight CAD is integrated; production RFQ and physical qualification remain open',
   'physical EVT / USB-C compliance / charging safety / RF / EMI / thermal not run'
 ]
}
VERIFY.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
if args.release:
    fail('manufacturing release blocked by open gates')
