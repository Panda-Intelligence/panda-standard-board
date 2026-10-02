"""HCTL HC-HY-2AWT primary 2.0mm/3A right-angle battery connector ECO."""
import json,re,uuid
from pathlib import Path
from _split_c1_sourcing import blocks,property_value
FP='panda-standard:HCTL_HC_HY_2AWT'
DOC='https://www.hctldz.com/static/upload/2025/10/17/202510175810.pdf'
DESCRIPTION='HCTL HC-HY-2AWT Rev.A primary p22: 2.0mm pitch,3A,250V,-40..105C. Signal lands1.2x3.80,anchors1.2x3.70,rows7.60mm. Height5.2mm nominal/+0.3 general tolerance. Pin1=BAT_CONN_P,pin2=GND,MP no-net. Housing/mate AWG26 polarity and mounted clearance require EVT. Connector rating does not certify the existing battery copper or pack for3A.'

def uid(k):return str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/battery-hy/'+k))

def battery_geometry(fp):
    if property_value(fp,'Reference')!='J301':raise ValueError('Expected battery J301')
    pose=tuple(float(v or 0) for v in re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)',fp).groups())
    if pose!=(49.75,23,0):raise ValueError('Battery pose predecessor differs')
    fp=re.sub(r'\(at\s+49\.75\s+23\)','(at 62 12 90)',fp,count=1)
    found=[]
    for a,b,p in reversed(list(blocks(fp,r'\(pad\s'))):
        n=re.match(r'\(pad\s+"([^"]+)"',p).group(1)
        xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
        size=tuple(map(float,re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
        if n in ('1','2'):
            old=(-.6 if n=='1' else .6,-2.21)
            if xy!=old or size!=(.6,.65):raise ValueError('Battery signal predecessor differs')
            new=(-1 if n=='1' else 1,-2.21);newsize=(1.2,3.8)
        elif n=='MP':
            if abs(xy[0])!=2.025 or xy[1]!=1.495 or size!=(.85,1.34):raise ValueError('Battery anchor predecessor differs')
            new=(-3.2 if xy[0]<0 else 3.2,5.39);newsize=(1.2,3.7)
        else:raise ValueError('Unexpected battery pad')
        found.append(n)
        p=re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)','(at %s %s 90)'%new,p,count=1)
        p=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size %s %s)'%newsize,p,count=1)
        fp=fp[:a]+p+fp[b:]
    if sorted(found)!=['1','2','MP','MP']:raise ValueError('Battery pad coverage differs')
    for a,b,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_circle|fp_rect|fp_text|model)\s'))):fp=fp[:a]+fp[b:]
    fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)',lambda m:'(descr '+json.dumps(DESCRIPTION)+')',fp,count=1)
    fp=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)','(tags "HCTL HY2.0 3A domestic battery")',fp,count=1)
    # Conservative land + housing envelope; not a STEP-based exact housing solid.
    extras=[]
    for layer,x,top,bottom,w in [('F.Fab',4.2,-4.11,9.59,.1),('F.CrtYd',4.45,-4.36,9.84,.05)]:
        extras.append('(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(-x,top,x,bottom,w,layer,uid(layer)))
    extras.append('(fp_circle (center -1 -4.5) (end -.9 -4.5) (stroke (width .1) (type solid)) (fill yes) (layer "F.SilkS") (uuid "%s"))'%uid('pin1'))
    return fp[:fp.rfind(')')].rstrip()+'\n'+'\n'.join(extras)+'\n)'

def apply_battery_routing(candidate):
    from _split_c1_domestic_eco import REL
    path=next((Path(candidate)/REL).glob('*.kicad_pcb'));text=path.read_text()
    deleted={
      'd59d51ba-9681-41b8-b9a5-fbf76c4c6ae0':((49.15,20.79),(48.5983,20.79)),
      '16bbbdb3-adb1-47a4-8bc8-810e9baa3b5f':((48.5983,20.79),(48.5861,20.8022)),
      'b5898d9b-4634-4d73-adc5-49626f35271d':((48.5861,20.8022),(48.4546,20.8022)),
      'becfaeb3-09a8-4721-b569-237ac0d24873':((48.4546,20.8022),(48.4546,20.8023)),
      'e19e6a90-9576-4aa2-b367-900f4431dcf8':((50.35,20.79),(49.7983,20.79)),
      'a3665be7-0ac9-4ea4-b254-1ccecbd6a5f8':((49.7983,20.4405),(49.7983,20.79)),
      'aa1d3500-24a0-4b99-8f35-19fc336fbdf7':((48.6586,19.3008),(49.7983,20.4405)),
      'e8eec420-2290-46ae-8611-878f7672a3f5':((48.5,19.3008),(48.6586,19.3008))}
    seen=set()
    for a,b,cu in reversed(list(blocks(text,r'\(segment\s'))):
        u=re.search(r'\(uuid "([^"]+)"\)',cu).group(1)
        if u not in deleted:continue
        endpoints=tuple(tuple(map(float,re.search(r'\('+k+r'\s+([-\d.]+)\s+([-\d.]+)\)',cu).groups())) for k in ('start','end'))
        if endpoints!=deleted[u] or ('(net "BAT_CONN_P")' not in cu and '(net "GND")' not in cu):raise ValueError('Battery routing predecessor differs')
        seen.add(u);text=text[:a]+text[b:]
    if seen!=set(deleted):raise ValueError('Battery routing deletion coverage differs')
    extras=[]
    routes=[((59.79,13),(55,13),'BAT_CONN_P',1.2),
            ((55,13),(55,23),'BAT_CONN_P',1.2),
            ((55,23),(49,23),'BAT_CONN_P',1.2),
            ((49,23),(48.4546,22.4546),'BAT_CONN_P',1.2),
            ((48.4546,22.4546),(48.4546,21.25),'BAT_CONN_P',.8),
            ((48.4546,21.25),(48.4546,20.8023),'BAT_CONN_P',.2),
            ((59.79,11),(64.5,11),'GND',.8),
            ((64.5,11),(64.5,5),'GND',.8),
            ((64.5,5),(67.5,5),'GND',.8)]
    for i,(s,e,net,w) in enumerate(routes):
        extras.append('(segment (start %s %s) (end %s %s) (width %s) (layer "F.Cu") (net "%s") (uuid "%s"))'%(*s,*e,w,net,uid('track'+str(i))))
    path.write_text(text[:text.rfind(')')]+'\n'+'\n'.join(extras)+'\n)\n')
