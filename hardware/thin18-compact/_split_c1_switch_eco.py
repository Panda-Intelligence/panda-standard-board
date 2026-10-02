"""XKB TS-1186E-B-B A1 side-switch lands and guarded copper replay."""
from pathlib import Path
import json,re
from _split_c1_sourcing import blocks,property_value
from _split_c1_domestic_eco import eco_uuid,native_block_hash,ROOT,REL

def switch_geometry(fp):
    ref=property_value(fp,'Reference')
    pose=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)',fp).groups()))
    if ref not in {'SW201','SW202'} or pose!=(2.3,6.75 if ref=='SW201' else 13.25,-90):
        raise ValueError('Side-switch predecessor pose differs')
    pads=list(blocks(fp,r'\(pad\s'))
    expected={('1',-1.8,-.65),('1',1.8,-.65),('2',-1.8,.65),('2',1.8,.65)}
    found=set()
    for _,_,p in pads:
        number=re.match(r'\(pad\s+"([^"]+)"',p).group(1)
        x,y=map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',p).groups())
        found.add((number,x,y))
    if len(pads)!=4 or found!=expected:raise ValueError('Side-switch predecessor lands differ')
    kept=set()
    for a,b,p in reversed(pads):
        n=re.match(r'\(pad\s+"([^"]+)"',p).group(1)
        if n in kept:fp=fp[:a]+fp[b:];continue
        kept.add(n)
        p=re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)',
                 '(at %s 0 270)'%(-2.45 if n=='1' else 2.45),p,count=1)
        p=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size 0.6 1.6)',p,count=1)
        p=p.replace('smd roundrect','smd rect');p=re.sub(r'\s*\(roundrect_rratio\s+[-\d.]+\)','',p)
        fp=fp[:a]+p+fp[b:]
    for a,b,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_arc|fp_circle|fp_rect|fp_poly|fp_text|model)\s'))):
        fp=fp[:a]+fp[b:]
    fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)',
              '(descr "XKB TS-1186E-B-B A1 2025-06-06, without locating posts. Two0.6x1.6mm lands,4.3mm inner gap/5.5mm outer span; centers+/-2.45mm. Drawing height1.50+/-0.10mm; H3.55 is the top-view actuator depth, not board height. Fab is conservative envelope, not a3D body.")',fp,count=1)
    fp=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)', '(tags "XKB TS-1186E-B-B side-actuated no-post 160gf")',fp,count=1)
    extra=[]
    for layer,x,top,bottom,w in [('F.Fab',2.8,-1.55,2.2,.1),('F.CrtYd',3.05,-1.8,2.45,.05)]:
        extra.append('(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(-x,top,x,bottom,w,layer,eco_uuid('XKBSW/'+ref+'/'+layer)))
    extra.append('(fp_text user "1" (at -2.45 -1.3) (layer "F.Fab") (uuid "%s") (effects (font (size .5 .5) (thickness .08))))'%eco_uuid('XKBSW/'+ref+'/pin1'))
    return fp[:fp.rfind(')')]+'\n'+'\n'.join(extra)+'\n)'

def apply_switch_layout(candidate):
    path=next((Path(candidate)/REL).glob('*.kicad_pcb'));text=path.read_text()
    layout=json.loads((ROOT/'split-c1-domestic-eco.json').read_text())['switch_layout']
    for move in layout['move_footprints']:
        a,b,fp=next(v for v in blocks(text,r'\(footprint\s') if property_value(v[2],'Reference')==move['ref'])
        m=re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)',fp)
        if list(map(float,m.groups()))!=move['old']:raise ValueError('Side-switch capacitor predecessor pose differs')
        fp=fp[:m.start()]+'(at %s %s %s)'%tuple(move['new'])+fp[m.end():]
        text=text[:a]+fp+text[b:]
    changes={v['uuid']:v for v in layout['changes']};seen=set()
    for a,b,k in reversed(list(blocks(text,r'\((?:segment|via)\s'))):
        uid=re.search(r'\(uuid "([^"]+)"\)',k).group(1)
        if uid not in changes:continue
        v=changes[uid]
        if native_block_hash(k)!=v['predecessor_sha256']:raise ValueError('Side-switch copper predecessor differs '+uid)
        seen.add(uid);text=text[:a]+(v['new_block'] or '')+text[b:]
    if seen!=set(changes):raise ValueError('Side-switch copper predecessor missing')
    for k in layout['new_copper']:
        uid=re.search(r'\(uuid "([^"]+)"\)',k).group(1)
        if '(uuid "'+uid+'")' in text:raise ValueError('Side-switch layout already applied')
    text=text[:text.rfind(')')]+'\n'+'\n'.join(layout['new_copper'])+'\n)\n'
    path.write_text(text)
