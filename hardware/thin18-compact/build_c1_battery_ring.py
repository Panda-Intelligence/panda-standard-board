#!/usr/bin/env python3
from pathlib import Path
import json, shutil, hashlib, math
from build_c0_fold import parse, render, children, child, props, edge_item

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'hardware/thin18/routing142'
DST=ROOT/'hardware/thin18-compact/c1-96x68-battery-ring'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
BBOX=json.loads((ROOT/'hardware/thin18-compact/routing142-footprint-bboxes.json').read_text())

W,H=96.0,68.0
BAT=(21.0,4.0,85.0,64.0)  # 64 x 60 mm rear envelope; ~94% of legacy 60x68 plan area
CLEAR=0.35
BOTTOM_BANDS=[(0.8,2.0,20.2,66.0),(85.8,2.0,95.2,66.0)]
HOLES={'H801':(15.0,2.0),'H802':(81.0,2.0),'H803':(93.0,34.0),'H804':(3.0,34.0)}
ANCHORS={'J501':(88.8,18.75),'R809':(33.2,54.2),'J503':(17.0,7.0)}  # preserve original socket-to-right-edge datum

def bbox_at(ref,x,y):
    o=BBOX[ref]['bbox_offset']
    return (x+o[0],y+o[1],x+o[2],y+o[3])

def inflate(b,c=CLEAR):
    return (b[0]-c,b[1]-c,b[2]+c,b[3]+c)

def hit(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>0 and min(a[3],b[3])-max(a[1],b[1])>0

def in_rect(b,r):
    return b[0]>=r[0] and b[1]>=r[1] and b[2]<=r[2] and b[3]<=r[3]

def base_xy(ref,x,y):
    if ref in HOLES: return HOLES[ref]
    if ref in ANCHORS: return ANCHORS[ref]
    if y>=100.0: return (x+26.0,y-60.0)
    return (x,y)

def pack_bottom(refs, fixed_obstacles):
    placed=[]
    positions={}
    # largest first
    refs=sorted(refs,key=lambda r:(BBOX[r]['bbox_offset'][2]-BBOX[r]['bbox_offset'][0])*
                                  (BBOX[r]['bbox_offset'][3]-BBOX[r]['bbox_offset'][1]),reverse=True)
    for ref in refs:
        best=None
        srcx,srcy,_=BBOX[ref]['at']
        bx,by=base_xy(ref,srcx,srcy)
        for band_index,band in enumerate(BOTTOM_BANDS):
            # 0.5-mm reference grid; bbox itself must stay in band
            xi=int(math.ceil((band[0]-BBOX[ref]['bbox_offset'][0])*2))
            xj=int(math.floor((band[2]-BBOX[ref]['bbox_offset'][2])*2))
            yi=int(math.ceil((band[1]-BBOX[ref]['bbox_offset'][1])*2))
            yj=int(math.floor((band[3]-BBOX[ref]['bbox_offset'][3])*2))
            for ix in range(xi,xj+1):
                x=ix/2
                for iy in range(yi,yj+1):
                    y=iy/2
                    bb=bbox_at(ref,x,y)
                    ib=inflate(bb)
                    if not in_rect(bb,band): continue
                    if hit(ib,BAT): continue
                    if any(hit(ib,p[1]) for p in placed): continue
                    if any(hit(ib,o) for o in fixed_obstacles): continue
                    # prefer closest side and original transformed y; small edge penalty
                    cost=(y-by)**2 + 0.12*(x-bx)**2 + band_index*0.01
                    if best is None or cost<best[0]:
                        best=(cost,x,y,bb)
        if best is None:
            raise RuntimeError('Cannot pack bottom footprint '+ref)
        _,x,y,bb=best
        positions[ref]=(x,y)
        placed.append((ref,inflate(bb)))
    return positions

def main():
    if DST.exists(): shutil.rmtree(DST)
    shutil.copytree(SRC,DST)
    pcb=DST/REL/(STEM+'.kicad_pcb')
    root=parse(pcb.read_text())
    assert len(children(root,'footprint'))==202

    # Start from unrouted placement-only state.
    root[:]=[x for x in root if not (isinstance(x,list) and x and
             (x[0] in {'segment','via','zone'} or edge_item(x)))]

    fps={props(f).get('Reference'):f for f in children(root,'footprint')}
    # Base fold: lower cluster stays; upper cluster moves right and down.
    for ref,f in fps.items():
        at=child(f,'at');x=float(at[1]);y=float(at[2])
        nx,ny=base_xy(ref,x,y)
        at[1]=format(nx,'.9g');at[2]=format(ny,'.9g')

    # Obstacles on battery-side perimeter that penetrate the board mechanically.
    fixed=[]
    for ref in ['H801','H802','H803','H804','J501','J503','U501']:
        at=child(fps[ref],'at')
        fixed.append(inflate(bbox_at(ref,float(at[1]),float(at[2])),0.6))

    bottom=[r for r,v in BBOX.items() if v['layer']=='Bottom Layer' and r!='J503']
    packed=pack_bottom(bottom,fixed)
    for ref,(x,y) in packed.items():
        at=child(fps[ref],'at'); at[1]=format(x,'.9g');at[2]=format(y,'.9g')

    # New outline; J201 is shifted +26/-60 => reference (39,68);
    # preserve its local mid-mount Edge.Cuts gap endpoints x=34.38..43.62.
    for x1,y1,x2,y2 in [(0,0,W,0),(W,0,W,H),(W,H,43.62,H),(34.38,H,0,H),(0,H,0,0)]:
        root.append(parse(f'(gr_line (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts"))'))

    # Mechanical battery envelope only; it is not a copper keepout.
    root.append(parse(f'(gr_rect (start {BAT[0]} {BAT[1]}) (end {BAT[2]} {BAT[3]}) (stroke (width 0.15) (type dash)) (fill none) (layer "Dwgs.User"))'))
    root.append(parse(f'(gr_text "BATTERY REAR ENVELOPE 68x60 - C1 FEASIBILITY" (at 48 34 90) (layer "Dwgs.User") (effects (font (size 1 1) (thickness 0.15))))'))

    # Invariants.
    assert len(children(root,'segment'))==0 and len(children(root,'via'))==0 and len(children(root,'zone'))==0
    assert sum(edge_item(x) for x in root[1:])==5
    assert len(fps)==202
    j=child(fps['J201'],'at')
    assert abs(float(j[1])-39.0)<1e-9 and abs(float(j[2])-68.0)<1e-9
    for ref in bottom:
        at=child(fps[ref],'at'); bb=bbox_at(ref,float(at[1]),float(at[2]))
        assert not hit(inflate(bb,0.05),BAT), ref

    pcb.write_text(render(root)+'\n')
    report={
      'kind':'C1 placement feasibility, intentionally unrouted',
      'source':'thin18/routing142',
      'target_mm':[W,H],
      'battery_rear_envelope_mm':[BAT[2]-BAT[0],BAT[3]-BAT[1]],
      'battery_rect_xyxy_mm':BAT,
      'bottom_footprints_packed':len(bottom),
      'bottom_bands':BOTTOM_BANDS,
      'upper_cluster_transform':{'dx_mm':26,'dy_mm':-60,'condition':'source y>=100'},
      'anchors':ANCHORS,
      'mounting_holes':HOLES,
      'routing_authority':False,'manufacturing_release':False,'physical_qualification':False,
      'pcb_sha256':hashlib.sha256(pcb.read_bytes()).hexdigest()
    }
    (DST/'c1-placement-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
