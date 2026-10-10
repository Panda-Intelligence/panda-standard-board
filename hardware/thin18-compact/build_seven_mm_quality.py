#!/usr/bin/env python3
"""Reproduce reviewed low-profile quality revision C from the routed donor.

Only writes to a NEW ignored/external candidate. This replays exact source ECOs,
not an autorouter result adopted on the basis of metadata. Native checks are run
after rebuilding. Supplier, impedance, mechanical and PCBA acceptance are separate.
"""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,sys
import xml.etree.ElementTree as ET
import wx
APP=wx.GetApp() or wx.App(False)
import pcbnew as P
from _split_c1_common import ROOT,REPO,kicad_cli
from _split_c1_sourcing import blocks
from _split_c1_power_integrity_eco import board_zones
from seven_mm_routing import native_semantic_fingerprint
from seven_mm_native_evidence import verify_native_clean
from seven_mm_process_rules import validate_rule_change, EXPECTED_RULE_CHANGES

SOURCE=ROOT/'seven_mm_quality_source.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require(ok,message):
    if not ok:raise ValueError(message)

def verify_plan(plan):
    require(plan.get('schema')=='panda-seven-mm-quality-source-v1' and plan.get('revision')=='C','Wrong quality source')
    require(plan.get('native_rules_relaxed') is False and plan.get('manufacturing_release') is False,'Unexpected release/rule declaration')
    require(plan.get('native_rule_changes')==EXPECTED_RULE_CHANGES,'Unreviewed rule delta')
    require(plan['native_checked_counts']=={'drc':0,'open':0,'parity':0,'erc':0},'Source did not have clean native checks')
    copper=plan['copper_items']
    require(hashlib.sha256('\n'.join(copper).encode()).hexdigest()==plan['copper_sha256'],'Copper source hash differs')
    require(sum(b.startswith('(segment') for b in copper)==plan['segment_count'] and sum(b.startswith('(via') for b in copper)==plan['via_count'],'Copper inventory differs')
    require(set(plan['pin_net_changes'])=={'U501'},'Unreviewed functional ECO')
    for name,entry in plan['library_replacements'].items():
        path=(ROOT/entry['source']).resolve();require(path.is_relative_to(ROOT.resolve()),'Library path escapes source')
        require(sha(path)==entry['sha256'],'Changed quality land '+name)
    return True

def patch_text(text,record,name):
    require(hashlib.sha256(text.encode()).hexdigest()==record['input_sha256'],'Predecessor text differs: '+name)
    for edit in record['edits']:
        require(text.count(edit['old'])==1,'Ambiguous/missing source edit: '+name)
        text=text.replace(edit['old'],edit['new'],1)
    require(hashlib.sha256(text.encode()).hexdigest()==record['output_sha256'],'Unexpected text ECO result: '+name)
    return text

def netlist(candidate,board):
    xml=candidate/(board+'-netlist.xml')
    subprocess.run([kicad_cli(),'sch','export','netlist','--format','kicadxml','--output',str(xml),str(candidate/(board+'.kicad_sch'))],cwd=candidate,check=True,stdout=subprocess.DEVNULL)
    tree=ET.parse(xml)
    nets={(n.get('ref'),n.get('pin')):v.get('name') for v in tree.findall('nets/net') for n in v.findall('node')}
    fields={c.get('ref'):{f.get('name'):f.text or '' for f in c.findall('fields/field')} for c in tree.findall('components/comp')}
    return nets,fields

def apply(candidate,source=SOURCE):
    candidate=Path(candidate).resolve();plan=json.loads(Path(source).read_text());verify_plan(plan)
    require(candidate.is_dir(),'Build the routed donor first')
    require(not candidate.is_relative_to(REPO) or candidate.is_relative_to(REPO/'.work'),'Output must be ignored/external')
    pcb=candidate/'Core.kicad_pcb';before=pcb.read_bytes()
    require(native_semantic_fingerprint(pcb)==plan['input_semantic_sha256'],'Wrong native predecessor geometry')
    old_nets,_=netlist(candidate,'Core')
    original=P.LoadBoard(str(pcb));footprints={f.GetReference():f for f in original.GetFootprints()}
    require(set(footprints)==set(plan['footprint_poses']),'Part inventory differs')
    pro_before=json.loads((candidate/'Core.kicad_pro').read_text())
    for name,patch in plan['source_text_patches'].items():
        path=candidate/name;path.write_text(patch_text(path.read_text(),patch,name))
    pro_after=json.loads((candidate/'Core.kicad_pro').read_text())
    validate_rule_change(pro_before,pro_after,plan['native_rule_changes'])
    for name,entry in plan['library_replacements'].items():shutil.copy2(ROOT/entry['source'],candidate/'Panda7.pretty'/(name+'.kicad_mod'))
    new_nets,new_fields=netlist(candidate,'Core')
    changed={ref:{pin:{'old':old_nets.get((ref,pin)),'new':net} for (r,pin),net in new_nets.items() if r==ref and net!=old_nets.get((r,pin))} for ref in footprints}
    changed={r:v for r,v in changed.items() if v}
    require(changed==plan['pin_net_changes'],'Actual schematic net ECO differs from source')
    text=before.decode();spans=list(blocks(text,r'\(footprint\s'))+list(blocks(text,r'\((?:segment|via|gr_[a-z_]+|dimension)\s'))+board_zones(text)
    for a,b,_ in sorted(spans,reverse=True):text=text[:a]+text[b:]
    pcb.write_text(text);board=P.LoadBoard(str(pcb));objects={}
    for name in sorted(set(new_nets.values())):
        obj=board.FindNet(name)
        if obj is None:obj=P.NETINFO_ITEM(board,name);board.Add(obj)
        objects[name]=obj
    for ref,pose in plan['footprint_poses'].items():
        old=footprints[ref];partname=ref+'_Core'
        f=P.FootprintLoad(str(candidate/'Panda7.pretty'),partname) if partname in plan['library_replacements'] else P.Cast_to_FOOTPRINT(old.Duplicate(False))
        require(f is not None,'Missing footprint '+ref)
        f.SetReference(ref);f.SetValue(pose['value']);f.SetPath(old.GetPath());f.SetFPIDAsString('Panda7:'+partname)
        for field in f.GetFields():
            if field.GetName() in new_fields[ref]:field.SetText(new_fields[ref][field.GetName()])
        target=P.F_Cu if pose['side']=='F.Cu' else P.B_Cu
        if f.GetLayer()!=target:f.SetLayerAndFlip(target)
        f.SetOrientationDegrees(pose['angle_deg']);f.SetPosition(P.VECTOR2I(*[P.FromMM(v) for v in pose['xy_mm']]))
        f.SetLocked(pose['locked']);f.SetDNP(pose['dnp'])
        require(f.IsExcludedFromBOM()==pose['excluded_from_bom'],'BOM inclusion changed '+ref)
        for pad in f.Pads():
            num=pad.GetNumber()
            if not num:pad.SetNetCode(0);continue
            require((ref,num) in new_nets,'Missing schematic terminal '+ref+'.'+num)
            pad.SetNet(objects[new_nets[(ref,num)]])
        board.Add(f)
    for a,b in plan['edges_mm']:
        e=P.PCB_SHAPE(board);e.SetShape(P.SHAPE_T_SEGMENT);e.SetLayer(P.Edge_Cuts);e.SetWidth(P.FromMM(.05))
        e.SetStart(P.VECTOR2I(*[P.FromMM(v) for v in a]));e.SetEnd(P.VECTOR2I(*[P.FromMM(v) for v in b]));board.Add(e)
    project=(candidate/'Core.kicad_pro').read_bytes();P.SaveBoard(str(pcb),board);(candidate/'Core.kicad_pro').write_bytes(project)
    require(native_semantic_fingerprint(pcb)==plan['output_semantic_sha256'],'Replayed geometry/net assignment differs')
    text=pcb.read_text();end=text.rfind(')');pcb.write_text(text[:end]+'\n'+'\n'.join(plan['copper_items']+plan['zones'])+'\n'+text[end:])
    # The authority is a current native calculation, not source_checked_counts.
    evidence={name:verify_native_clean(candidate/(name+'.kicad_pcb')) for name in ['Core','Display']}
    result={'schema':'panda-seven-mm-quality-rebuild-v1','revision':'C','source_sha256':sha(source),'native':evidence,'source_inventory_preserved':True,'native_rules_relaxed':False,'native_rule_changes':plan['native_rule_changes'],'quality_routing_reproduced':True,'manufacturing_release':False}
    (candidate/'QUALITY-REBUILD.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'revision':'C','native':{k:v['counts'] for k,v in evidence.items()},'manufacturing_release':False},indent=2))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    from build_seven_mm_candidate import build
    require(not a.output.exists(),'Choose a fresh candidate directory')
    build(a.output);apply(a.output)

if __name__=='__main__':main()
