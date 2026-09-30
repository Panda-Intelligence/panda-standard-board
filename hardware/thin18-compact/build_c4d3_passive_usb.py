#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_c0_fold import parse,render,children,child,props,Quoted

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'c4d2-96x68-sgm62125'
DST=ROOT/'c4d3-96x68-passive-usbc'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
SCH=DST/REL/(STEM+'.kicad_sch')
USB=DST/REL/'usb-interface.kicad_sch'
PCB=DST/REL/(STEM+'.kicad_pcb')
KICAD='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'

REMOVE_USB={'U202','U203','U204','U205','U206','R205','R208','R209','R210','R211','R212','R213','R214',
            'C210','C211','C212','C213','C214','C215'}
REMOVE_ROOT={'R602','R603'}
LEGACY_NETS={'3V3_USB_CC','CC_OUT1_LOCAL','CC_OUT2_LOCAL','CC_OUT1_AON','CC_OUT2_AON',
             'TUSB_VBUS_DET','VBUS_SENSE','VBUS_VALID_CC','VBUS_VALID_AON'}

if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('verification','__pycache__','*.pyc'))
(DST/'verification').mkdir()

def set_prop(node,name,value):
    for p in children(node,'property'):
        if str(p[1])==name:
            p[2]=Quoted(value); return
    # Insert before pins if missing.
    node.append(['property',Quoted(name),Quoted(value),['at','0','0','0'],['hide','yes'],['effects',['font',['size','1','1']]]])

def xy(node):
    a=child(node,'at'); return (round(float(a[1]),5),round(float(a[2]),5))

def wire_points(w):
    pts=child(w,'pts')
    out=[]
    for q in children(pts,'xy'): out.append((round(float(q[1]),5),round(float(q[2]),5)))
    return out

def clean_sheet(path,remove_refs,label_rewrites=None):
    root=parse(path.read_text())
    # Remove component instances by reference.
    root[:]=[n for n in root if not (isinstance(n,list) and n and n[0]=='symbol' and props(n).get('Reference') in remove_refs)]
    rewrites=label_rewrites or {}
    # Rewrite exact labels at specific coordinate, while recording legacy label positions.
    legacy_positions=set()
    for n in root[1:]:
        if isinstance(n,list) and n and n[0]=='global_label':
            name=str(n[1]); pos=xy(n)
            if pos in rewrites:
                n[1]=Quoted(rewrites[pos])
            elif name in LEGACY_NETS:
                legacy_positions.add(pos)
    # Remove legacy global labels and the wire segment directly attached to each label.
    root[:]=[n for n in root if not (isinstance(n,list) and n and n[0]=='global_label' and str(n[1]) in LEGACY_NETS)]
    root[:]=[n for n in root if not (isinstance(n,list) and n and n[0]=='wire' and any(p in legacy_positions for p in wire_points(n)))]
    path.write_text(render(root)+'\n')

# R206/R207 pin endpoint labels: pin1 -> GND, pin2 -> connector CC.
usb_rewrites={
 (167.64,111.76):'GND',
 (167.64,119.38):'USB_CC1',
 (217.17,111.76):'GND',
 (217.17,119.38):'USB_CC2',
}
clean_sheet(USB,REMOVE_USB,usb_rewrites)
clean_sheet(SCH,REMOVE_ROOT)

# Change R206/R207 values and procurement metadata in the USB sheet.
ur=parse(USB.read_text())
for n in children(ur,'symbol'):
    ref=props(n).get('Reference')
    if ref in {'R206','R207'}:
        set_prop(n,'Value','5.1k / USB-C Rd')
        set_prop(n,'Description','USB Type-C sink Rd; 5.1k 1%; exact mainland MPN sourcing still open')
USB.write_text(render(ur)+'\n')

# Remove matching PCB footprints, retain R206/R207/J201/data ESD/data tuning.
pr=parse(PCB.read_text())
pr[:]=[n for n in pr if not (isinstance(n,list) and n and n[0]=='footprint' and props(n).get('Reference') in (REMOVE_USB|REMOVE_ROOT))]
# Update R206/R207 value now; net assignment follows schematic export below.
for fp in children(pr,'footprint'):
    ref=props(fp).get('Reference')
    if ref in {'R206','R207'}:
        set_prop(fp,'Value','5.1k / USB-C Rd')
        set_prop(fp,'Description','USB Type-C sink Rd; 5.1k 1%; exact mainland MPN sourcing still open')
PCB.write_text(render(pr)+'\n')

# Export schematic netlist first, then sync changed PCB pads to authoritative schematic nets.
subprocess.run([KICAD,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc-prepcb.json'),str(SCH)],check=True)
subprocess.run([KICAD,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)
nr=ET.parse(DST/'verification/netlist.xml').getroot()
pin_net={}
for net in nr.findall('nets/net'):
    for node in net.findall('node'):
        pin_net[(node.get('ref'),node.get('pin'))]=net.get('name','')

# Expected USB electrical result.
expected={('R206','1'):'GND',('R206','2'):'USB_CC1',('R207','1'):'GND',('R207','2'):'USB_CC2'}
wrong={k:(pin_net.get(k),v) for k,v in expected.items() if pin_net.get(k)!=v}
if wrong: raise SystemExit(f'USB Rd schematic mismatch {wrong}')
for ref in REMOVE_USB|REMOVE_ROOT:
    if any(k[0]==ref for k in pin_net): raise SystemExit(f'retired ref still in netlist: {ref}')
# D+/D-/VBUS connector nets must remain.
for pin,net in [('A6','USB_DP'),('B6','USB_DP'),('A7','USB_DM'),('B7','USB_DM'),('A4','VBUS_USB'),('B4','VBUS_USB')]:
    if pin_net.get(('J201',pin))!=net: raise SystemExit(f'J201 {pin} changed')

# Clean dangling schematic objects created by retiring the legacy USB/status chain.
# KiCad ERC JSON coordinates are schematic coordinates divided by 100, not mm/inch.
pre=json.load(open(DST/'verification/erc-prepcb.json'))
dangling=set()
released=[]
for sheet in pre.get('sheets',[]):
    for v in sheet.get('violations',[]):
        typ=v.get('type')
        if typ in {'wire_dangling','unconnected_wire_endpoint','no_connect_dangling',
                   'label_dangling','global_label_dangling','hierarchical_label_dangling'}:
            for item in v.get('items',[]):
                if item.get('uuid'): dangling.add(item['uuid'])
        elif typ=='pin_not_connected':
            for item in v.get('items',[]):
                desc=item.get('description','')
                if any(x in desc for x in ['Symbol U601 Pin 19','Symbol U601 Pin 20','Symbol U501 Pin 38']):
                    pos=item.get('pos',{})
                    released.append((round(float(pos['x'])*100,5),round(float(pos['y'])*100,5),desc))

def node_uuid(n):
    us=children(n,'uuid')
    return str(us[0][1]) if us else None

removable_types={'wire','no_connect','global_label','label','hierarchical_label','junction'}
for sp in (DST/REL).glob('*.kicad_sch'):
    rt=parse(sp.read_text())
    rt[:]=[n for n in rt if not (isinstance(n,list) and n and n[0] in removable_types and node_uuid(n) in dangling)]
    if sp==SCH:
        existing={xy(n) for n in children(rt,'no_connect')}
        import uuid
        for x,y,desc in released:
            if (x,y) not in existing:
                rt.append(parse(f'(no_connect (at {x} {y}) (uuid "{uuid.uuid5(uuid.NAMESPACE_URL,"thin18-c4d3-nc-"+desc)}"))'))
    sp.write_text(render(rt)+'\n')

# Re-run ERC after cleanup. Some labels become dangling only after their connected
# legacy symbols/wires are removed, so perform a bounded second-stage UUID cleanup.
def remove_erc_dangling_objects(report_path):
    rep=json.load(open(report_path))
    uuids=set()
    for sheet in rep.get('sheets',[]):
        for v in sheet.get('violations',[]):
            if v.get('type') in {'wire_dangling','unconnected_wire_endpoint','no_connect_dangling',
                                 'label_dangling','global_label_dangling','hierarchical_label_dangling'}:
                for item in v.get('items',[]):
                    if item.get('uuid'): uuids.add(item['uuid'])
    if not uuids: return 0
    for sp in (DST/REL).glob('*.kicad_sch'):
        rt=parse(sp.read_text())
        before=len(rt)
        rt[:]=[n for n in rt if not (isinstance(n,list) and n and n[0] in removable_types and node_uuid(n) in uuids)]
        if len(rt)!=before: sp.write_text(render(rt)+'\n')
    return len(uuids)

for pass_no in range(20):
    rp=DST/'verification'/f'erc-clean-{pass_no}.json'
    subprocess.run([KICAD,'sch','erc','--format','json','--severity-all','--output',str(rp),str(SCH)],check=True)
    removed=remove_erc_dangling_objects(rp)
    if not removed: break

subprocess.run([KICAD,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc-clean.json'),str(SCH)],check=True)
subprocess.run([KICAD,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)
nr=ET.parse(DST/'verification/netlist.xml').getroot()
pin_net={}
for net in nr.findall('nets/net'):
    for node in net.findall('node'): pin_net[(node.get('ref'),node.get('pin'))]=net.get('name','')

# Rewrite PCB pad net subtrees for R206/R207 and reclaimed GPIOs.
pr=parse(PCB.read_text())
def set_pad_net(fp,padnum,netname):
    pads=[x for x in children(fp,'pad') if str(x[1])==padnum]
    if len(pads)!=1: raise SystemExit(f'{props(fp).get("Reference")} pad {padnum} missing')
    pad=pads[0]
    pad[:]=[x for x in pad if not (isinstance(x,list) and x and x[0]=='net')]
    if netname: pad.append(['net',Quoted(netname)])
refs={props(f).get('Reference'):f for f in children(pr,'footprint')}
for ref in ('R206','R207'):
    set_pad_net(refs[ref],'1',pin_net.get((ref,'1')))
    set_pad_net(refs[ref],'2',pin_net.get((ref,'2')))
set_pad_net(refs['U601'],'19',pin_net.get(('U601','19')))
set_pad_net(refs['U601'],'20',pin_net.get(('U601','20')))
set_pad_net(refs['U501'],'38',pin_net.get(('U501','38')))
# Keep R206/R207 fields in parity with their schematic symbols.
for ref in ('R206','R207'):
    set_prop(refs[ref],'Value','5.1k / USB-C Rd')
    set_prop(refs[ref],'Description','USB Type-C sink Rd; 5.1k 1%; exact mainland MPN sourcing still open')
PCB.write_text(render(pr)+'\n')

# Fresh native checks.
subprocess.run([KICAD,'sch','erc','--format','json','--severity-all','--output',str(DST/'verification/erc.json'),str(SCH)],check=True)
subprocess.run([KICAD,'sch','export','netlist','--format','kicadxml','--output',str(DST/'verification/netlist.xml'),str(SCH)],check=True)
subprocess.run([KICAD,'pcb','drc','--format','json','--severity-all','--schematic-parity','--output',str(DST/'verification/drc.json'),str(PCB)],check=True)
erc=json.load(open(DST/'verification/erc.json')); drc=json.load(open(DST/'verification/drc.json'))
counts={'erc':sum(len(x.get('violations',[])) for x in erc.get('sheets',[])),
        'drc':len(drc.get('violations',[])),'parity':len(drc.get('schematic_parity',[])),
        'open':len(drc.get('unconnected_items',[]))}
if counts['erc'] or counts['drc'] or counts['parity']: raise SystemExit(f'native checks not clean {counts}')

# Recheck retired refs and exact surviving connector nets in final export.
nr=ET.parse(DST/'verification/netlist.xml').getroot()
comps={c.get('ref'):c for c in nr.findall('components/comp')}
for ref in REMOVE_USB|REMOVE_ROOT:
    if ref in comps: raise SystemExit(f'retired BOM ref remains {ref}')
pin_net={}
for net in nr.findall('nets/net'):
    for node in net.findall('node'): pin_net[(node.get('ref'),node.get('pin'))]=net.get('name','')
for k,v in expected.items():
    if pin_net.get(k)!=v: raise SystemExit(f'final Rd mapping {k}')
for pin,net in [('A6','USB_DP'),('B6','USB_DP'),('A7','USB_DM'),('B7','USB_DM'),('A4','VBUS_USB'),('B4','VBUS_USB')]:
    if pin_net.get(('J201',pin))!=net: raise SystemExit(f'final J201 {pin}')
for key in [('U601','19'),('U601','20'),('U501','38')]:
    net=pin_net.get(key)
    if not (net and net.startswith('unconnected-')):
        raise SystemExit(f'released pin not explicit NC {key}: {net}')

report={
 'date':'2026-09-29','kind':'C4D-3 passive USB-C sink cleanup',
 'source':'c4d2-96x68-sgm62125',
 'retired_refs':sorted(REMOVE_USB|REMOVE_ROOT),
 'retired_count':len(REMOVE_USB|REMOVE_ROOT),
 'rd':{'R206':'USB_CC1 -> 5.1k -> GND','R207':'USB_CC2 -> 5.1k -> GND'},
 'retained':['J201 USB4500-03-0-A','D201 USB data/CC ESD','D202 VBUS ESD','R529/R530 USB data series','C514/C515 DNP tuning'],
 'released_gpio':['U601.P16','U601.P17','U501.IO2'],
 'status_source':'SGM41513 nPG/nINT + I2C status',
 'native_checks':counts,
 'physical_qualification':False,'manufacturing_release':False,
 'pcb_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest()
}
(DST/'c4d3-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(DST/'README.md').write_text('# Thin18 Compact C4D-3 — passive USB-C sink\n\nThe legacy Type-C controller/LDO/comparator/buffer status chain is removed from the product netlist and PCB. R206/R207 become 5.1k Rd from CC1/CC2 to GND. USB D+/D-, VBUS, ESD and tuning remain intact. Charging status comes from SGM41513. U601 P16/P17 and ESP32 IO2 are explicitly no-connected in this D3 candidate; C4D4 will reclaim P16/P17 for the touch connector. Not a manufacturing release.\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
