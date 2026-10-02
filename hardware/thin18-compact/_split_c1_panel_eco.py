"""XKB X05A10L24G A1; ordered panel contacts and bottom-contact entry."""
import json,re,uuid
from _split_c1_sourcing import blocks,property_value

DOC='https://atta.szlcsc.com/upload/public/pdf/source/20260728/26BC46881D4A63071423AF10299E60A3.pdf'
FP='panda-r6-display:XKB_X05A10L24G'
DESCRIPTION='XKB X05A10L24G A1 2024-11-29; 24x0.5mm bottom contacts, 0.3mm FPC, height1.0+/-0.1mm. Signal lands0.30x0.65; support lands0.30x0.76, D13.27mm. Entry local+Y; board contact1 at local-X, preserving panel contact order. Primary does not label terminal1: board numbering is the panel interface contract, not a manufacturer marking. Insertion/orientation remains EVT.'

def panel_geometry(fp):
    if property_value(fp,'Reference')!='J2':
        raise ValueError('Expected J2')
    pose=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\)',fp).groups()))
    if pose!=(23,29):raise ValueError('Panel connector pose changed')
    pads=list(blocks(fp,r'\(pad\s'));found=[];supports=0
    for a,b,p in reversed(pads):
        n=re.match(r'\(pad\s+"([^"]+)"',p).group(1)
        xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
        size=tuple(map(float,re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
        if n=='MP':
            if abs(xy[0])!=7.65 or xy[1]!=1.4 or size!=(1.8,2.2):
                raise ValueError('Panel support predecessor differs')
            newxy=(6.635 if xy[0]>0 else -6.635,.005)
            p=re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+\)','(at %s %s)'%newxy,p,count=1)
            newsize=(.3,.76);supports+=1
        else:
            k=int(n)
            if k not in range(1,25) or xy!=(-5.75+(k-1)*.5,-1.85) or size!=(.3,1.3):
                raise ValueError('Panel signal predecessor differs: '+n)
            newsize=(.3,.65);found.append(k)
        p=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size %s %s)'%newsize,p,count=1)
        fp=fp[:a]+p+fp[b:]
    if sorted(found)!=list(range(1,25)) or supports!=2:
        raise ValueError('Panel pad coverage differs')
    for a,b,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_circle|fp_rect|fp_poly|fp_text|model)\s'))):
        fp=fp[:a]+fp[b:]
    fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)',lambda m:'(descr '+json.dumps(DESCRIPTION)+')',fp,count=1)
    fp=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)','(tags "XKB FPC24 bottom contact local+Y")',fp,count=1)
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/split-c1/panel24/'+label))
    extra=[]
    for layer,x,y0,y1,w in [('F.Fab',6.885,-1.525,1.822,.1),('F.CrtYd',7.25,-2.425,2.275,.05)]:
        extra.append('(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(-x,y0,x,y1,w,layer,uid(layer)))
    extra.append('(fp_circle (center -5.75 -2.60) (end -5.65 -2.60) (stroke (width .1) (type solid)) (fill yes) (layer "F.SilkS") (uuid "%s"))'%uid('board-contact1'))
    extra.append('(fp_text user "FPC ENTRY" (at 0 2.6) (layer "F.Fab") (effects (font (size .6 .6) (thickness .1))) (uuid "%s"))'%uid('entry'))
    return fp[:fp.rfind(')')].rstrip()+'\n'+'\n'.join(extra)+'\n)'


def apply_panel_routing(candidate):
    from pathlib import Path
    path=Path(candidate)/'PANDA-EPD0426-SPI-EVT.kicad_pcb'
    text=path.read_text()
    routes={
      '4879fc9d-7cd4-423c-931f-5cf689436ef5':[(11.6639,23.7729),(15.7,27.809),(15.7,29.8),(22.0267,29.8),(23.0116,28.8151)],
      '8b32b5b4-8e69-427e-b350-12e7c39807bc':[],
      '0d01e982-ffee-4bdb-aa96-3944e458374f':[(25.6017,28.4284),(26.9733,29.8),(33.15,29.8),(34.5216,28.4284)]}
    predecessors={
      '4879fc9d-7cd4-423c-931f-5cf689436ef5':((11.6639,23.7729),(16.7061,28.8151)),
      '8b32b5b4-8e69-427e-b350-12e7c39807bc':((16.7061,28.8151),(23.0116,28.8151)),
      '0d01e982-ffee-4bdb-aa96-3944e458374f':((25.6017,28.4284),(34.5216,28.4284))}
    found=set()
    for a,b,seg in reversed(list(blocks(text,r'\(segment\s'))):
        uid=re.search(r'\(uuid "([^"]+)"',seg).group(1)
        if uid not in routes:continue
        if '(layer "F.Cu")' not in seg or '(width 0.15)' not in seg:
            raise ValueError('Panel escape predecessor changed')
        old=tuple(tuple(map(float,re.search(r'\('+key+r'\s+([-\d.]+)\s+([-\d.]+)',seg).groups())) for key in ['start','end'])
        if old!=predecessors[uid]:raise ValueError('Panel escape endpoints changed')
        found.add(uid);points=routes[uid];pieces=[]
        for i,(start,end) in enumerate(zip(points,points[1:])):
            new=seg
            for field,xy in [('start',start),('end',end)]:
                new=re.sub(r'\('+field+r'\s+[-\d.]+\s+[-\d.]+\)','('+field+' %s %s)'%xy,new,count=1)
            newuid=uid if i==0 else str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/panel24/'+uid+'/'+str(i)))
            new=re.sub(r'\(uuid "[^"]+"\)','(uuid "'+newuid+'")',new,count=1);pieces.append(new)
        text=text[:a]+'\n'.join(pieces)+text[b:]
    if found!=set(routes):raise ValueError('Panel escape coverage differs')
    path.write_text(text)
