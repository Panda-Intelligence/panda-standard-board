"""JSM Q1 ECO: primary 1G/2D/3S and manufacturer p5 recommended lands."""
from pathlib import Path
import re,json,uuid
from _split_c1_sourcing import blocks,property_value
ROOT=Path(__file__).resolve().parent
NAME='NX3008NBK_215_JSM'
SYMBOL='panda-r6-display:'+NAME
FP='panda-r6-display:JSM_NX3008NBK_SOT23'
DOC='https://atta.szlcsc.com/upload/public/pdf/source/20251224/924281F171127EE15B457A61AD43416B.pdf'
DESCRIPTION='JSM NX3008NBK,215-JSM V1.0 p1:1=G,2=D,3=S;30V;Rds max0.6ohm at2.5V/200mA;Qg max0.87nC at4.5V/15V/1A;p5 suggested lands0.8x0.6,1.9mm pair pitch,2.02mm row pitch. Prototype selection; measured polarity/GDR/boost/thermal qualification remains NOT_RUN.'

def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/split-c1/jsm-q1/'+s))

def mos_geometry(fp):
    if property_value(fp,'Reference')!='Q1' or '(at 10 12)' not in fp:raise ValueError('Q1 predecessor pose differs')
    for a,b,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_arc|fp_circle|fp_rect|fp_poly|fp_text|model)\s'))):fp=fp[:a]+fp[b:]
    for a,b,p in reversed(list(blocks(fp,r'\(pad\s'))):
        n=re.match(r'\(pad\s+"([^"]+)"',p).group(1)
        data={'1':(-1.01,-.95,'/GDR','G_1'),'2':(-1.01,.95,'/BOOST_SW','D_2'),'3':(1.01,0,'/RESE','S_3')}
        if n not in data:raise ValueError('Q1 predecessor pad differs')
        x,y,net,function=data[n]
        old={'1':('/GDR','G_1'),'2':('/RESE','S_2'),'3':('/BOOST_SW','D_3')}[n]
        if '(net "'+old[0]+'")' not in p or '(pinfunction "'+old[1]+'")' not in p:raise ValueError('Q1 predecessor pin/net differs')
        p=re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)','(at %s %s)'%(x,y),p,count=1)
        p=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size 0.8 0.6)',p,count=1)
        p=p.replace('smd roundrect','smd rect');p=re.sub(r'\s*\(roundrect_rratio[^)]+\)','',p)
        p=p.replace('(net "'+old[0]+'")','(net "'+net+'")').replace('(pinfunction "'+old[1]+'")','(pinfunction "'+function+'")')
        fp=fp[:a]+p+fp[b:]
    extra=[]
    for layer,xy,w in [('F.Fab',(-.7,-1.5,.7,1.5),.1),('F.CrtYd',(-1.66,-1.75,1.66,1.75),.05)]:
        extra.append('(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(*xy,w,layer,uid(layer)))
    extra.append('(fp_circle (center -1.6 -1.3) (end -1.5 -1.3) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab") (uuid "%s"))'%uid('pin1'))
    fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)',lambda m:'(descr '+json.dumps(DESCRIPTION)+')',fp,count=1)
    return fp[:fp.rfind(')')]+'\n'+'\n'.join(extra)+'\n)'

def clone_mos_symbol(text):
    if '(symbol "'+SYMBOL+'"' in text:return text
    a,b,s=next((a,b,s) for a,b,s in blocks(text,r'\(symbol\s+"') if s.startswith('(symbol "Transistor_FET:Q_NMOS_GSD"'))
    s=s.replace('Transistor_FET:Q_NMOS_GSD',SYMBOL).replace('Q_NMOS_GSD_',NAME+'_')
    for c,d,p in reversed(list(blocks(s,r'\(pin\s'))):
        if '(name "S"' in p:p=p.replace('(number "2"','(number "3"')
        elif '(name "D"' in p:p=p.replace('(number "3"','(number "2"')
        s=s[:c]+p+s[d:]
    for k,v in [('Value',NAME),('Footprint',FP),('Datasheet',DOC),('Description',DESCRIPTION)]:
        s=re.sub(r'\(property "'+k+r'" "(?:\\.|[^"\\])*"',lambda m:'(property '+json.dumps(k)+' '+json.dumps(v),s,count=1)
    return text[:b]+'\n'+s+text[b:]

def install_mos_library(candidate):
    p=Path(candidate);lib=p/'panda-r6-display.kicad_sym';t=lib.read_text()
    if '(symbol "'+NAME+'"' in t:return
    s=next(s for _,_,s in blocks((p/'PANDA-EPD0426-SPI-EVT.kicad_sch').read_text(),r'\(symbol\s+"') if s.startswith('(symbol "'+SYMBOL+'"'))
    s=s.replace('(symbol "'+SYMBOL+'"','(symbol "'+NAME+'"',1)
    e=t.rfind(')');lib.write_text(t[:e]+'\n'+s+'\n'+t[e:])

def apply_mos_routing(candidate):
    from _core_c1_pcb_patch import copper,digest
    p=Path(candidate)/'PANDA-EPD0426-SPI-EVT.kicad_pcb';t=p.read_text()
    d=json.loads((ROOT/'split-c1-mos-layout.json').read_text())
    if digest(t)!=d['source_copper_sha256']:raise ValueError('MOS copper predecessor differs')
    norm=lambda s:re.sub(r'\s+',' ',s)
    existing=copper(t)
    for a,b,s in reversed(list(blocks(t,r'\((?:segment|via)\s'))):
        u=re.search(r'\(uuid "([^"]+)"',s).group(1)
        if u in d['removed_copper']:
            if norm(s)!=norm(d['removed_copper'][u]):raise ValueError('MOS removed copper differs')
            t=t[:a]+t[b:]
        elif u in d['modified_copper']:
            q=d['modified_copper'][u]
            if norm(s)!=norm(q['old']):raise ValueError('MOS modified copper differs')
            t=t[:a]+q['new']+t[b:]
    if any(u in existing for u in d['added_copper']):raise ValueError('MOS copper UUID collision')
    e=t.rfind(')');t=t[:e]+'\n'+'\n'.join(d['added_copper'].values())+'\n'+t[e:]
    if digest(t)!=d['routed_copper_sha256']:raise ValueError('MOS copper replay differs')
    p.write_text(t)
