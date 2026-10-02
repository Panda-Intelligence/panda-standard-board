"""MUP U20405-01 primary Rev4 geometry and guarded USB layout ECO."""
from pathlib import Path
import json,re
from _split_c1_sourcing import blocks,property_value
from _split_c1_domestic_eco import eco_uuid,native_block_hash,ROOT,REL

def usb_geometry(fp):
    if re.search(r'\(at\s+39\s+68\)',fp) is None:raise ValueError('USB predecessor pose differs')
    expected_x={'A1':-3.2,'B12':-3.2,'A4':-2.4,'B9':-2.4,'B8':-1.75,'A5':-1.25,'B7':-.75,'A6':-.25,'A7':.25,'B6':.75,'A8':1.25,'B5':1.75,'B4':2.4,'A9':2.4,'B1':3.2,'A12':3.2}
    previous=list(blocks(fp,r'\(pad\s'))
    if len(previous)!=20:raise ValueError('USB predecessor pad count differs')
    for _,_,pad in previous:
        n=re.match(r'\(pad\s+"([^"]+)"',pad).group(1)
        xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',pad).groups()))
        size=tuple(map(float,re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)',pad).groups()))
        if n=='SH':
            if xy not in [(-5.62,-5.6),(-5.62,-1.6),(5.62,-5.6),(5.62,-1.6)] or size!=(1,1.8 if xy[1]==-5.6 else 2.2):raise ValueError('USB predecessor shell lands differ')
        elif n not in expected_x or xy!=(expected_x[n],-6.77) or size!=(.6 if abs(expected_x[n])>=2.4 else .3,1.1):raise ValueError('USB predecessor signal lands differ')
    for a,b,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_arc|fp_circle|fp_rect|fp_poly|fp_text|model)\s'))):fp=fp[:a]+fp[b:]
    order=['B12','A1','B9','A4','A5','A6','A7','A8','B8','B7','B6','B5','B4','A9','B1','A12']
    for a,b,pad in reversed(list(blocks(fp,r'\(pad\s'))):
        n=re.match(r'\(pad\s+"([^"]+)"',pad).group(1)
        if n=='SH':
            x,y=map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',pad).groups())
            xx=-4.32 if x<0 else 4.32;yy=-6.2 if y<-3 else -1.7
            size=(1.2,2.0 if y<-3 else 2.1);drill=(.6,1.4 if y<-3 else 1.5)
            pad=re.sub(r'\(drill oval [^)]+\)','(drill oval %s %s)'%drill,pad,count=1)
        else:
            if n not in order:raise ValueError('Unexpected USB pin '+n)
            xx=round(-3+order.index(n)*.4,6);yy=-6.55;size=(.25,.8)
        pad=re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)','(at %s %s)'%(xx,yy),pad,count=1)
        pad=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size %s %s)'%size,pad,count=1)
        fp=fp[:a]+pad+fp[b:]
    extra=[]
    for layer,x,y1,y2,w in [('F.Fab',4.57,-6.9,.5,.1),('F.CrtYd',5.17,-7.45,.75,.05)]:
        extra.append('(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(-x,y1,x,y2,w,layer,eco_uuid('MUPUSB/'+layer)))
    extra.append('(fp_text user "B12" (at -3 -7.45) (layer "F.Fab") (uuid "%s") (effects (font (size .5 .5) (thickness .08))))'%eco_uuid('MUPUSB/pin1'))
    return fp[:fp.rfind(')')]+'\n'+'\n'.join(extra)+'\n)'

def apply_usb_layout(candidate):
    path=next((Path(candidate)/REL).glob('*.kicad_pcb'));text=path.read_text()
    layout=json.loads((ROOT/'split-c1-domestic-eco.json').read_text())['usb_layout']
    changes={v['uuid']:v for v in layout['changes']};seen=set()
    for a,b,k in reversed(list(blocks(text,r'\((?:segment|via)\s'))):
        uid=re.search(r'\(uuid "([^"]+)"\)',k).group(1)
        if uid not in changes:continue
        v=changes[uid]
        if native_block_hash(k)!=v['predecessor_sha256']:raise ValueError('USB copper predecessor differs '+uid)
        seen.add(uid);text=text[:a]+(v['new_block'] or '')+text[b:]
    if seen!=set(changes):raise ValueError('USB copper predecessor missing')
    for k in layout['new_copper']:
        uid=re.search(r'\(uuid "([^"]+)"\)',k).group(1)
        if '(uuid "'+uid+'")' in text:raise ValueError('USB layout already applied')
    text=text[:text.rfind(')')]+'\n'+'\n'.join(layout['new_copper'])+'\n)\n';path.write_text(text)
    dru=path.with_suffix('.kicad_dru');s=dru.read_text()
    if native_block_hash(s)!=layout['rules_predecessor_sha256']:raise ValueError('USB rule predecessor differs')
    removed=set()
    for a,b,r in reversed(list(blocks(s,r'\(rule\s'))):
        h=native_block_hash(r)
        if h in layout['removed_rules']:removed.add(h);s=s[:a]+s[b:]
    if removed!=set(layout['removed_rules']):raise ValueError('USB rule removal differs')
    dru.write_text(s)
