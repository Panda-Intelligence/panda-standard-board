"""XUNPU TF-122-CCP9 RevA primary; controlled card detect, lands and copper."""
from pathlib import Path
import re,json,uuid
from _split_c1_sourcing import blocks,property_value
from _split_c1_common import ROOT,REL,STEM
DOC='https://atta.szlcsc.com/upload/public/pdf/source/20240813/A78F94B574A12E0EF5650C3B7EED35AF.pdf'
FP='panda-standard:XUNPU_TF_122_CCP9'
SYMBOL='XUNPU_TF_122_CCP9'
DESCRIPTION='XUNPU TF-122-CCP9 RevA;8 SD contacts,CD closes to grounded shell on insertion.0.5A,-40..85C,5000 cycles,height2.00mm max. Component-side lands:signals/CD0.60x1.60,left-front1.20x1.80,right-front1.60x1.50,rear1.20x2.20;two1.00mm NPTH,8.00mm pitch. Datum connector center X/signal-land bottom Y;entry local+Y. Engineering9=CD,10 andSH=grounded shell,not additional numbered vendor contacts. Contact order preserved; card travel/ESD/insertion EVT remains NOT_RUN.'

def microsd_geometry(fp):
    if property_value(fp,'Reference')!='J501' or '(at 88.8 18.75 -90)' not in fp:
        raise ValueError('MicroSD predecessor pose differs')
    ns=[re.match(r'\(pad\s+"([^"]+)"',p).group(1) for _,_,p in blocks(fp,r'\(pad\s')]
    if sorted(ns)!=sorted([str(n) for n in range(1,11)]+['SH']*4):
        raise ValueError('MicroSD predecessor contacts differ')
    fp=re.sub(r'\(at 88.8 18.75 -90\)','(at 81.75 17.315 90)',fp,count=1)
    for c,d,_ in reversed(list(blocks(fp,r'\((?:fp_line|fp_arc|fp_circle|fp_rect|fp_poly|fp_text|model)\s'))):fp=fp[:c]+fp[d:]
    sh=0
    for c,d,p in reversed(list(blocks(fp,r'\(pad\s'))):
     n=re.match(r'\(pad\s+"([^"]+)"',p).group(1)
     if n.isdigit() and 1<=int(n)<=8:x,y,w,h=2.27-(int(n)-1)*1.1,-.8,.6,1.6
     elif n=='9':x,y,w,h=-6.53,-.8,.6,1.6
     elif n=='10':x,y,w,h=-7.73,.5,1.2,1.8
     elif n=='SH':
      coords=[(7.77,9.8,1.2,2.2),(-7.73,9.8,1.2,2.2),(6.87,.25,1.6,1.5)]
      if sh==3:fp=fp[:c]+fp[d:];sh+=1;continue
      x,y,w,h=coords[sh];sh+=1
     else:raise ValueError(n)
     p=re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)','(at %.6f %.6f 90)'%(x,y),p,count=1)
     p=re.sub(r'\(size\s+[-\d.]+\s+[-\d.]+\)','(size %s %s)'%(w,h),p,count=1)
     p=p.replace('roundrect','rect');p=re.sub(r'\s*\(roundrect_rratio[^)]+\)','',p)
     fp=fp[:c]+p+fp[d:]
    def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/split-c1/tf122/'+s))
    extra=[]
    for x in [-4.93,3.07]:extra.append('(pad "" np_thru_hole circle (at %s 10.2 90) (size 1 1) (drill 1) (layers "*.Cu" "*.Mask") (uuid "%s"))'%(x,uid('post'+str(x))))
    for layer,xy,w in [('F.Fab',(-7.375,-.55,7.375,13.95),.1),('F.CrtYd',(-8.63,-2.0,8.67,14.25),.05)]:extra.append('(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(*xy,w,layer,uid(layer)))
    fp=fp[:fp.rfind(')')]+'\n'+'\n'.join(extra)+'\n)'
    fp=fp.replace('(pinfunction "CD1")','(pinfunction "CD")').replace('(pinfunction "CD2")','(pinfunction "GROUND_SHELL")')
    fp=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)',lambda m:'(descr '+json.dumps(DESCRIPTION)+')',fp,count=1)
    fp=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)','(tags "XUNPU microSD detect local+Y")',fp,count=1)
    return fp

def clone_microsd_symbol(text,embedded):
    target='panda-standard:'+SYMBOL if embedded else SYMBOL
    if '(symbol "'+target+'"' in text:return text
    source='Connector:Micro_SD_Card_Det2'
    if not embedded:raise ValueError('Clone primary symbol from original embedded Connector library first')
    a,b,s=next((a,b,s) for a,b,s in blocks(text,r'\(symbol\s+"') if s.startswith('(symbol "'+source+'"'))
    s=s.replace(source,target).replace('Micro_SD_Card_Det2_',SYMBOL+'_')
    s=s.replace('(name "CD1"','(name "CD"').replace('(name "CD2"','(name "GROUND_SHELL"')
    for k,v in [('Value',SYMBOL),('Footprint',FP),('Datasheet',DOC),('Description',DESCRIPTION)]:
        s=re.sub(r'\(property "'+k+r'" "(?:\\.|[^"\\])*"',lambda m:'(property '+json.dumps(k)+' '+json.dumps(v),s,count=1)
    return text[:b]+'\n'+s+text[b:]

def install_symbol_library(candidate):
    lib=Path(candidate)/'lib/panda-standard.kicad_sym';t=lib.read_text()
    if '(symbol "'+SYMBOL+'"' in t:return
    sch=Path(candidate)/REL/(STEM+'.kicad_sch')
    s=next(s for _,_,s in blocks(sch.read_text(),r'\(symbol\s+"') if s.startswith('(symbol "panda-standard:'+SYMBOL+'"'))
    s=s.replace('(symbol "panda-standard:'+SYMBOL+'"','(symbol "'+SYMBOL+'"',1)
    e=t.rfind(')');lib.write_text(t[:e]+'\n'+s+'\n'+t[e:])

def apply_microsd_routing(candidate):
    from _core_c1_pcb_patch import copper,digest
    p=Path(candidate)/REL/(STEM+'.kicad_pcb');t=p.read_text()
    d=json.loads((ROOT/'split-c1-microsd-layout.json').read_text())
    if digest(t)!=d['source_copper_sha256']:raise ValueError('MicroSD copper predecessor differs')
    existing=copper(t);norm=lambda s:re.sub(r'\s+',' ',s)
    for a,b,s in reversed(list(blocks(t,r'\((?:segment|via)\s'))):
        uid=re.search(r'\(uuid "([^"]+)"',s).group(1)
        if uid in d['removed_copper']:
            if norm(s)!=norm(d['removed_copper'][uid]):raise ValueError('MicroSD removed copper differs')
            t=t[:a]+t[b:]
        elif uid in d['modified_copper']:
            pair=d['modified_copper'][uid]
            if norm(s)!=norm(pair['old']):raise ValueError('MicroSD modified copper differs')
            t=t[:a]+pair['new']+t[b:]
    if any(uid in existing for uid in d['added_copper']):raise ValueError('MicroSD copper UUID already exists')
    e=t.rfind(')');t=t[:e]+'\n'+'\n'.join(d['added_copper'].values())+'\n'+t[e:]
    if digest(t)!=d['routed_copper_sha256']:raise ValueError('MicroSD copper replay differs')
    p.write_text(t)
