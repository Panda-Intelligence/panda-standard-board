#!/usr/bin/env python3
"""Prepare an explicitly UNROUTED native placement candidate, never official CAD.

Keeps every source footprint/pin/net. Pending low-profile ECOs remain visible in
an outside-board review area; they are not removed from BOM or silently scaled.
The packing screen is an initial XY allocation, not final electrical placement,
maximum-height proof, final port drawing or fabrication approval.
"""
from pathlib import Path
import argparse,hashlib,json,math,shutil,subprocess,sys
from seven_mm_layout import CONTRACT,validate_plan
from _split_c1_common import ROOT,REPO,REL,STEM,kicad_cli,native_input
import wx
APP=wx.App(False)
import pcbnew as P


def xy(v):return [round(P.ToMM(v.x),6),round(P.ToMM(v.y),6)]
def pt(x,y):return P.VECTOR2I(P.FromMM(x),P.FromMM(y))
def bounds(f):
    b=f.GetBoundingBox(False,False)
    return [P.ToMM(b.GetX()),P.ToMM(b.GetY()),P.ToMM(b.GetRight()),P.ToMM(b.GetBottom())]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin_contract(b):
    return sorted((f.GetReference(),p.GetNumber(),str(p.GetNetname())) for f in b.GetFootprints() for p in f.Pads())
def touch(a,b,gap=.25):
    return not (a[2]+gap<=b[0] or b[2]+gap<=a[0] or a[3]+gap<=b[1] or b[3]+gap<=a[1])
def inside(r,regions):
    return any(a+.20<=r[0] and b+.20<=r[1] and r[2]<=c-.20 and r[3]<=d-.20 for a,b,c,d in regions)


def prepare(out):
    plan=json.loads(CONTRACT.read_text());validate_plan(plan)
    out=out.resolve()
    if out.exists():raise ValueError('Choose a fresh output directory; never overwrite a candidate')
    if out.is_relative_to(REPO) and not out.is_relative_to(REPO/'.work'):
        raise ValueError('Candidate must be external or under ignored .work')
    source_pcbs={'Core':ROOT/'core-c1-96x68-split'/REL/(STEM+'.kicad_pcb'),
                 'Display':ROOT/'display-c1-45x36-production-bom/PANDA-EPD0426-SPI-EVT.kicad_pcb'}
    sources={n:digest(p) for n,p in source_pcbs.items()};out.mkdir(parents=True)
    report={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
            'source_hashes':sources,'contract_sha256':digest(CONTRACT),'status':'INITIAL_PLACEMENT_UNROUTED_NOT_FOR_FAB',
            'manufacturing_release':False,'source_native_changed':False,'boards':{}}
    for name,source in source_pcbs.items():
        srcroot=ROOT/('core-c1-96x68-split' if name=='Core' else 'display-c1-45x36-production-bom')
        destroot=out/name
        for p in srcroot.rglob('*'):
            if p.is_file() and native_input(p):
                dest=destroot/p.relative_to(srcroot);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        pcb=destroot/source.relative_to(srcroot);board=P.LoadBoard(str(pcb));before=pin_contract(board)
        origins={f.GetReference():xy(f.GetPosition()) for f in board.GetFootprints()}
        refs=sorted(origins)
        # Old routes, zones and board-level annotations cannot remain credible
        # after the new geometry. Footprint-local definitions/pin maps are retained.
        from _split_c1_sourcing import blocks
        from _split_c1_power_integrity_eco import board_zones
        text=pcb.read_text()
        ranges=list(blocks(text,r'\((?:segment|via)\s'))+board_zones(text)
        ranges+=list(blocks(text,r'\(gr_[a-z_]+\s'))+list(blocks(text,r'\(dimension\s'))
        for start,end,_ in sorted(ranges,reverse=True):text=text[:start]+text[end:]
        pcb.write_text(text);board=P.LoadBoard(str(pcb))
        outline=plan['boards'][name]['outline_xy_mm']
        for a,b in zip(outline,outline[1:]+outline[:1]):
            edge=P.PCB_SHAPE(board);edge.SetShape(P.SHAPE_T_SEGMENT);edge.SetLayer(P.Edge_Cuts)
            edge.SetStart(pt(*a));edge.SetEnd(pt(*b));edge.SetWidth(P.FromMM(.05));board.Add(edge)
        title=board.GetTitleBlock();title.SetTitle('SEVEN-MM '+name+' INITIAL PLACEMENT - NOT FOR FAB')
        title.SetRevision('UNROUTED / LOW-PROFILE ECOS PENDING')
        review={'C301','U501','J301','J302','J502','J601'} if name=='Core' else {'J1'}
        service=[];pending=[];placed=[];occupied=[]
        targets={'U901':(48,101),'U902':(64,43),'U601':(64,30),'U302':(64,60),
                 'U903':(64,51),'U904':(64,76),'U905':(64,19),'U503':(64,8),'U906':(48,70)}
        # Reserve bare-chip/Flash/crystal/RF and low-profile flex workspaces.
        if name=='Core':occupied.extend([[41,74,55,89],[40,90,49,100]])
        else:occupied.append([30,78,38,98])
        for f in board.GetFootprints():
            f.SetLocked(False)
            if f.GetLayer()!=P.F_Cu:f.SetLayerAndFlip(P.F_Cu)
        if name=='Core':
            # The retained old USB footprint is only an XY datum preview, and is
            # still flagged as an unqualified high-body/mid-mount replacement.
            for ref,position,angle in [('J201',(37.5,111.45),0),('J501',(61,96),90)]:
                f=board.FindFootprintByReference(ref);f.SetOrientationDegrees(angle);f.SetPosition(pt(*position))
                occupied.append(bounds(f));placed.append(ref)
            pending.append({'ref':'J201','reason':'Old top-mount shown for XY only; exact new mid-mount footprint/cutout/height still required'})
        candidates=[]
        for f in board.GetFootprints():
            ref=f.GetReference()
            if ref in placed:continue
            if ref in review or f.IsDNP() or f.IsExcludedFromBOM():service.append(ref);continue
            r=bounds(f);candidates.append(((r[2]-r[0])*(r[3]-r[1]),ref))
        regions=plan['boards'][name]['regions_xyxy_mm']
        anchors={ref:origins[ref] for ref in targets if ref in origins}
        for _,ref in sorted(candidates,reverse=True):
            f=board.FindFootprintByReference(ref)
            if name=='Core':
                group=ref if ref in targets else min(anchors,key=lambda k:math.dist(origins[ref],anchors[k]))
                target=targets[group]
            else:target=(20,82)
            best=None
            for angle in [0,90,180,270]:
                f.SetOrientationDegrees(angle);f.SetPosition(pt(0,0));offset=bounds(f)
                for x0,y0,x1,y1 in regions:
                    minx=math.ceil((x0+.2-offset[0])*2)/2;maxx=x1-.2-offset[2]
                    miny=math.ceil((y0+.2-offset[1])*2)/2;maxy=y1-.2-offset[3]
                    for xi in range(max(0,int((maxx-minx)*2)+1)):
                        x=minx+xi*.5
                        for yi in range(max(0,int((maxy-miny)*2)+1)):
                            y=miny+yi*.5;r=[offset[0]+x,offset[1]+y,offset[2]+x,offset[3]+y]
                            score=math.dist((x,y),target)
                            if best and score>=best[0]:continue
                            if inside(r,regions) and not any(touch(r,o) for o in occupied):best=(score,x,y,angle,r)
            if best:
                _,x,y,angle,r=best;f.SetOrientationDegrees(angle);f.SetPosition(pt(x,y));occupied.append(r);placed.append(ref)
            else:service.append(ref);pending.append({'ref':ref,'reason':'No clear first-pass XY allocation; not omitted'})
        # Review area is deliberately outside the outline so native DRC cannot
        # confuse unimplemented ECOs with a completed board. No DNP conversion.
        for i,ref in enumerate(service):
            f=board.FindFootprintByReference(ref);f.SetOrientationDegrees(0);f.SetPosition(pt(110+(i%4)*25,15+(i//4)*25))
            if ref in review:pending.append({'ref':ref,'reason':'Thin-profile/interface ECO pending; exact original footprint kept for review'})
        assert pin_contract(board)==before,'Native pad-to-net assignments changed'
        assert sorted(f.GetReference() for f in board.GetFootprints())==refs,'Source footprint inventory changed'
        P.SaveBoard(str(pcb),board);reload=P.LoadBoard(str(pcb));assert pin_contract(reload)==before
        report['boards'][name]={'pcb':str(pcb),'sha256':digest(pcb),'source_footprints':len(refs),'first_pass_placed_refs':sorted(placed),
                              'outside_outline_review_refs':sorted(service),'blocking_items':pending,'pin_net_contract_preserved':True,
                              'all_copper_requires_reroute':True,'physical_mating_verified':False,'port_datums_are_preliminary':True}
    assert all(digest(p)==sources[n] for n,p in source_pcbs.items()),'Official source PCB changed'
    (out/'PLACEMENT-STATUS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'candidate':str(out),'status':report['status'],'boards':{n:{'placed':len(b['first_pass_placed_refs']),
          'review':len(b['outside_outline_review_refs']),'pin_net_contract_preserved':b['pin_net_contract_preserved']} for n,b in report['boards'].items()}},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.output)
