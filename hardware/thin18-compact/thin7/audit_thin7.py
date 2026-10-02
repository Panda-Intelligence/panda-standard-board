#!/usr/bin/env python3
"""Check a 7mm mechanical partition and explicitly reject incompatible native CAD."""
import argparse, hashlib, itertools, json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])

def in_rounded_cavity(x,y,w,h):
    # Outer corner R5, side wall0.65, minimum PCB/cell XY clearance0.25.
    r=5.0; inset=.9
    if not (inset<=x<=w-inset and inset<=y<=h-inset): return False
    cx=min(max(x,r),w-r); cy=min(max(y,r),h-r)
    return (x-cx)**2+(y-cy)**2 <= (r-inset)**2+1e-9

def finite_dimensions(value):
    if isinstance(value, dict):
        for v in value.values(): finite_dimensions(v)
    elif isinstance(value, list):
        for v in value: finite_dimensions(v)
    elif isinstance(value, (int,float)) and not isinstance(value,bool) and not math.isfinite(value):
        raise ValueError('Non-finite dimension')

def check(c, legacy=None):
    finite_dimensions(c)
    outer = c['outer_xyz_mm']; target = c['requested_outer_thickness_mm']
    if any(v<=0 for v in outer) or abs(target-7.0)>1e-6 or abs(outer[2]-target)>1e-6:
        raise ValueError('Thin7 requires a 7.0mm case; never scale the native parts')
    if c['board_count']!=2 or len(c['boards'])!=2: raise ValueError('Exactly two PCBs required')
    p=c['panel']; b=c['battery']; z=c['z_budget_mm']
    if any(v<=0 for v in z.values()): raise ValueError('Positive stack allowances required')
    if not p['front_bezel_overlaps_border_only'] or p['extra_front_cover_included']:
        raise ValueError('Any extra screen cover needs a new stack; bezel is not a full front slab')
    subtotal=round(sum(z.values()),6)
    if subtotal>target+1e-6: raise ValueError('Battery section exceeds target thickness')
    if abs(p['z_bottom_mm']+p['thickness_budget_mm']+p['front_recess_mm']-target)>1e-6:
        raise ValueError('Panel/recess planes do not close at 7mm')
    if abs(p['thickness_budget_mm']-z['panel_thickness'])>1e-6:
        raise ValueError('Panel budget mismatch')
    if abs(b['maximum_complete_pack_xyz_mm'][2]-z['maximum_complete_pack'])>1e-6:
        raise ValueError('Complete-pack budget mismatch')
    if abs(b['swelling_allowance_mm']-z['battery_swelling'])>1e-6:
        raise ValueError('Swelling budget mismatch')
    if abs(b['z_bottom_mm']-z['rear_wall']-z['battery_insulation'])>1e-6:
        raise ValueError('Battery insulation plane mismatch')
    battery_top=b['z_bottom_mm']+b['maximum_complete_pack_xyz_mm'][2]+b['swelling_allowance_mm']
    if battery_top+z['battery_to_panel_clearance_and_reserve']+z['panel_adhesive']>p['z_bottom_mm']+1e-6:
        raise ValueError('Swollen pack collides with panel')
    parts=[('battery',b['rect_xyxy_mm'])]; board_results={}
    for name,board in c['boards'].items():
        pts=board['outline_xy_mm']; xs=[v[0] for v in pts]; ys=[v[1] for v in pts]
        if not all(in_rounded_cavity(x,y,*outer[:2]) for x,y in pts): raise ValueError('Outline intersects rounded enclosure cavity')
        if max(max(xs)-min(xs),max(ys)-min(ys))>=100: raise ValueError('PCB coupon boundary exceeded')
        if board['component_side']!='front_only': raise ValueError('Rear components need a new section')
        component_top=board['z_bottom_mm']+board['thickness_mm']+board['maximum_mounted_component_height_mm']
        if component_top+z['panel_adhesive']>p['z_bottom_mm']: raise ValueError('PCB components collide with panel')
        area=abs(sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts))))/2
        rect_area=sum((r[2]-r[0])*(r[3]-r[1]) for r in board['partition_rects_xyxy_mm'])
        if abs(area-rect_area)>1e-6: raise ValueError('Partition and polygon area differ')
        for a,d in itertools.combinations(board['partition_rects_xyxy_mm'],2):
            if overlap(a,d): raise ValueError('Double-counted board area')
        parts.extend((name,r) for r in board['partition_rects_xyxy_mm'])
        board_results[name]={'bounding_size_mm':[max(xs)-min(xs),max(ys)-min(ys)],'area_mm2':area,'component_top_mm':component_top,'panel_gap_before_adhesive_mm':round(p['z_bottom_mm']-component_top,6)}
    for (an,a),(bn,d) in itertools.combinations(parts,2):
        if an!=bn and overlap(a,d): raise ValueError('Coplanar partition collision: '+an+'/'+bn)
    br=b['rect_xyxy_mm']; dims=b['maximum_complete_pack_xyz_mm']
    if abs(br[2]-br[0]-dims[0])>1e-6 or abs(br[3]-br[1]-dims[1])>1e-6: raise ValueError('Pack XY envelope mismatch')
    if not (0<br[0]<br[2]<outer[0] and 0<br[1]<br[3]<outer[1]): raise ValueError('Battery outside case')
    if not all(in_rounded_cavity(x,y,*outer[:2]) for x in [br[0],br[2]] for y in [br[1],br[3]]): raise ValueError('Battery intersects rounded enclosure cavity')
    blockers=[]
    if legacy:
        limits={v['ref']:v for v in legacy['published_component_height_screens'] if v['board']=='Core-C1'}
        for ref in ['C301','U501','J301','J302','J502']:
            item=limits[ref]; height=item.get('height_maximum_mm',item['height_nominal_mm'])
            mounted=height+(.2 if ref=='C301' else 0)
            if mounted>2.4:
                blockers.append({'ref':ref,'mpn':item['mpn'],'published_body_height_mm':height,'thin7_mounted_ceiling_mm':2.4,'required_action':'replace, not compress','height_basis':item['height_basis']})
        blockers += [{'ref':'J601/J1','required_action':'replace native 1.5mm stacked interconnect with qualified coplanar flex'}, {'ref':'Core-C1','required_action':'96x68 native outline overlaps battery/Display regions; re-place and re-route'}, {'ref':'main battery','required_action':'legacy 5.5mm pack input exceeds Thin7 whole-pack ceiling 3.1mm'}]
    evidence=c['release_evidence']
    ready=bool(legacy is not None and not blockers and all(evidence.values()) and all(e['implemented'] for e in c['required_ecos']) and b['selected_mpn'])
    return {'schema':'panda-thin7-audit-v1','outer_xyz_mm':outer,'board_count':2,'partition_xy_passed':True,'parameterized_stack_passed':True,'battery_section_mm':subtotal,'boards':board_results,'battery_top_with_swelling_mm':round(battery_top,6),'native_design_blockers':blockers,'native_thin7_ready':ready,'manufacturing_release':False,'supplier_or_physical_fit_verified':False,'basis':'Requirements/envelope calculation only. Blank KiCad outlines and render are not routed PCBs or accepted supply.'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--contract',type=Path,default=ROOT/'thin7-mechanical-contract.json')
    ap.add_argument('--legacy-inputs',type=Path,default=ROOT.parent/'split-c1-mechanical-inputs.json')
    ap.add_argument('--output',type=Path,default=ROOT/'thin7-mechanical-audit.json')
    ap.add_argument('--require-native-ready',action='store_true'); args=ap.parse_args()
    c=json.loads(args.contract.read_text()); legacy=json.loads(args.legacy_inputs.read_text()) if args.legacy_inputs.exists() else None
    report=check(c,legacy); report['contract_sha256']=hashlib.sha256(args.contract.read_bytes()).hexdigest()
    if legacy: report['legacy_inputs_sha256']=hashlib.sha256(args.legacy_inputs.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'outer_xyz_mm':report['outer_xyz_mm'],'partition_xy_passed':True,'parameterized_stack_passed':True,'native_thin7_ready':report['native_thin7_ready'],'native_blockers':[b['ref'] for b in report['native_design_blockers']]},indent=2))
    if args.require_native_ready and not report['native_thin7_ready']:
        raise SystemExit('BLOCKED: current native Core/Display CAD does not meet the user-required 7mm product. Read THIN7-REDESIGN.md; do not fabricate Thin7 outline templates.')
if __name__=='__main__': main()
