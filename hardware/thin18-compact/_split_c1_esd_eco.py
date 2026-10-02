"""LRC8804FDT1G Rev.B USB2/CC protection; 5V working rating."""
import json,re,uuid
from _split_c1_sourcing import blocks,property_value,balanced
SYMBOL='LRC8804FDT1G'
FP='panda-standard:LRC8804F_DFN2510'
DOC='https://www.lrc.cn/Upload/PDF/Product/ESD/LRC8804FDT1G.pdf'
DESCRIPTION='LRC8804FDT1G Jan2023 Rev.B; VRWM5V (not5.5V), +/-15kV contact/air, Cio0.3pF max. Pins1/2/4/5=IO,3/8=GND,6/7/9/10=NC. Reviewed only for non-PD5V sink: CC has5.1k+/-5% Rd and normal CC is below5V; VBUS uses separate5.5V D202. No CC-to-VBUS fault or board ESD certification inferred. Primary unequal GND lands; board ESD/USB qualification remains NOT_RUN.'

def clone_esd_symbol(text,cache):
    from _split_c1_domestic_eco import set_prop
    prefix='panda-standard:' if cache else ''
    old=prefix+'TPD4E05U06DQAR';new=prefix+SYMBOL
    if '(symbol "'+new+'"' in text:return text
    a=text.index('(symbol "'+old+'"');b=balanced(text,a)
    s=text[a:b].replace('TPD4E05U06DQAR',SYMBOL)
    for f,v in [('Value',SYMBOL),('Footprint',FP),('Datasheet',DOC),('Description',DESCRIPTION)]:
        s=set_prop(s,f,v)
    end=balanced(text,text.index('(lib_symbols'))-1 if cache else text.rfind(')')
    return text[:end]+'\n'+s+'\n'+text[end:]

def esd_geometry(fp):
    if property_value(fp,'Reference')!='D201':raise ValueError('Expected D201')
    pose=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)',fp).groups()))
    if pose!=(39,57.5,90):raise ValueError('ESD pose changed')
    pads=list(blocks(fp,r'\(pad\s'));found=set()
    for a,b,p in reversed(pads):
        n=int(re.match(r'\(pad\s+"([^"]+)"',p).group(1))
        xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
        expected=(-.385,-1+(n-1)*.5) if n<=5 else (.385,1-(n-6)*.5)
        if n not in range(1,11) or xy!=expected:raise ValueError('ESD predecessor differs')
        found.add(n);newxy=xy;size=(.625,.25)
        if n==3:newxy=(-.35,0);size=(.7,.45)
        elif n==8:newxy=(.4125,0);size=(.575,.45)
        else:newxy=(-.3875 if n<=5 else .3875,xy[1])
        p=re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)','(at %s %s 90)'%newxy,p,count=1)
        p=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size %s %s)'%size,p,count=1)
        p=p.replace('smd roundrect','smd rect');p=re.sub(r'\s*\(roundrect_rratio\s+[-\d.]+\)','',p)
        fp=fp[:a]+p+fp[b:]
    if found!=set(range(1,11)):raise ValueError('ESD pad coverage differs')
    for a,b,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_circle|fp_rect|fp_text|model)\s'))):fp=fp[:a]+fp[b:]
    fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)',lambda m:'(descr '+json.dumps(DESCRIPTION)+')',fp,count=1)
    fp=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)','(tags "LRC USB2 CC DFN2510")',fp,count=1)
    def uid(k):return str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/esd4/'+k))
    extras=[]
    for layer,x,y,w in [('F.Fab',.525,1.275,.1),('F.CrtYd',.95,1.55,.05)]:
        extras.append('(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(-x,-y,x,y,w,layer,uid(layer)))
    extras.append('(fp_circle (center -.95 -1.1) (end -.84 -1.1) (stroke (width .1) (type solid)) (fill yes) (layer "F.SilkS") (uuid "%s"))'%uid('pin1'))
    return fp[:fp.rfind(')')].rstrip()+'\n'+'\n'.join(extras)+'\n)'
