"""SGM05HU1AL Rev.A polarized VBUS protection and primary land pattern."""
import json,re,uuid
from _split_c1_sourcing import blocks,property_value,balanced

MPN='SGM05HU1ALXUGY2G/TR'
SYMBOL='SGM05HU1ALXUGY2G_TR'
FP='panda-standard:SGM05HU1AL_UTDFN_1006_2BL'
DOC='https://www.sg-micro.com/rect/assets/eb558bde-b3be-44cb-ae7e-2a8337e06580/SGM05HU1AL.pdf'
DESCRIPTION='SGMICRO SGM05HU1ALXUGY2G/TR, August2024 Rev.A. Unidirectional5.5V VRWM;1=cathode/VBUS,2=anode/GND. Primary0.25x0.50mm lands at0.65mm pitch.5V USB sink only/no PD; board ESD, leakage and exact assembly supply pending.'

def clone_vbus_symbol(text,cache):
    from _split_c1_domestic_eco import set_prop
    old=('panda-standard:' if cache else '')+'TPD1E10B06DPYR'
    new=('panda-standard:' if cache else '')+SYMBOL
    if '(symbol "'+new+'"' in text:return text
    a=text.index('(symbol "'+old+'"');b=balanced(text,a)
    symbol=text[a:b].replace('TPD1E10B06DPYR',SYMBOL)
    for field,value in [('Value',MPN),('Footprint',FP),('Datasheet',DOC),('Description',DESCRIPTION)]:
        symbol=set_prop(symbol,field,value)
    if symbol.count('(name "IO"')!=1 or symbol.count('(name "GND"')!=1:
        raise ValueError('VBUS symbol predecessor pin names differ')
    symbol=symbol.replace('(name "IO"','(name "K"',1).replace('(name "GND"','(name "A"',1)
    end=balanced(text,text.index('(lib_symbols'))-1 if cache else text.rfind(')')
    return text[:end]+'\n'+symbol+'\n'+text[end:]

def vbus_geometry(fp):
    pose=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)',fp).groups()))
    if property_value(fp,'Reference')!='D202' or pose!=(48.6,60,180):
        raise ValueError('VBUS protector predecessor pose differs')
    pads=list(blocks(fp,r'\(pad\s'));found=set()
    if len(pads)!=2:raise ValueError('VBUS protector predecessor pad count differs')
    for a,b,p in reversed(pads):
        n=re.match(r'\(pad\s+"([^"]+)"',p).group(1)
        xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
        size=tuple(map(float,re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
        net=re.search(r'\(net\s+"([^"]+)"\)',p).group(1)
        if n not in {'1','2'} or n in found or xy!=(-.35 if n=='1' else .35,0) or size!=(.3,.5) or net!=('VBUS_USB' if n=='1' else 'GND'):
            raise ValueError('VBUS protector predecessor land/net differs')
        found.add(n)
        p=re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)', '(at %s 0 180)'%(-.325 if n=='1' else .325),p,count=1)
        p=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size 0.25 0.50)',p,count=1)
        p=p.replace('smd roundrect','smd rect');p=re.sub(r'\s*\(roundrect_rratio\s+[-\d.]+\)','',p)
        fp=fp[:a]+p+fp[b:]
    for a,b,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_circle|fp_rect|fp_text|model)\s'))):fp=fp[:a]+fp[b:]
    fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)', '(descr '+json.dumps(DESCRIPTION)+')',fp,count=1)
    fp=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)', '(tags "SGMICRO VBUS unidirectional cathode-pin1 UTDFN1006")',fp,count=1)
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'panda-split-c1/SGM05HU1AL/'+label))
    extra=[]
    for layer,x,y,w in [('F.Fab',.525,.325,.1),('F.CrtYd',.75,.55,.05)]:
        extra.append('(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(-x,-y,x,y,w,layer,uid(layer)))
    extra.append('(fp_line (start -0.4 -0.3) (end -0.4 0.3) (stroke (width .1) (type solid)) (layer "F.Fab") (uuid "%s"))'%uid('cathode-bar'))
    extra.append('(fp_circle (center -.8 0) (end -.69 0) (stroke (width .1) (type solid)) (fill yes) (layer "F.SilkS") (uuid "%s"))'%uid('pin1-dot'))
    return fp[:fp.rfind(')')].rstrip()+'\n'+'\n'.join(extra)+'\n)'
