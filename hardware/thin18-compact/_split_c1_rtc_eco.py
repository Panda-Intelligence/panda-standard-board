"""SD3078 + rechargeable KAMCAP backup prototype ECO; primary pin and envelope review."""
from pathlib import Path
import re,json,uuid
from _split_c1_sourcing import blocks,property_value
ROOT=Path(__file__).resolve().parent
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
RTC_NAME='SD3078'
RTC_SYMBOL='panda-standard:'+RTC_NAME
RTC_FP='panda-standard:WAVE_SD3078_SOP8_208mil'
RTC_DOC='https://www.whwave.com.cn/filedownload/3045413'
CAP_FP='panda-standard:KAMCAP_SE5R5_D105VYH'
CAP_DOC='https://atta.szlcsc.com/upload/public/pdf/source/20170717/C118887_1500269960558820748.pdf'
RTC_DESCRIPTION='WAVE SD3078 Rev4.4:1SCL,2F32K,3VDD,4NC,5VBAT,6GND,7INT,8SDA;integrated crystal;VDD2.7..5.5,VBAT2.3..3.6;0x32,100kHz at3.3V;MSL3,maxheight1.9. Derived engineering lands2.0x0.7 at1.27 pitch/7.3 row pitch;not manufacturer recommended. Retention/firmware/temperature qualification remains NOT_RUN.'
CAP_DESCRIPTION='KAMCAP SE-5R5-D105VYH primary2017:1F -20/+80%,5.5V,15ohm maxESR;maxbody19.2diameter/6.0height;leadpitch19+/-0.5,lead1.0+/-0.1. Engineering19mm pitch,platedslots1.8x1.4,lands2.4x2.0. Pin1=positive,2=GND:install actual marked+ terminal on PCB+;drawing has no numbered polarity view. Hand-solder after SMT;body must clear PCB0.2,cut lead belowCore B<=0.5. Prototype retention budget conditional on precharge/current;not physical validation.'
PINMAP={'1':'2','2':'7','3':'1','4':'8','5':'6','6':'5','7':'3','8':'4'}
PINS={'1':('SCL','input','I2C_SCL'),'2':('F32K','open_collector','unconnected-(U302-F32K-Pad2)'),'3':('VDD','power_in','3V3_AON'),'4':('NC','no_connect','unconnected-(U302-NC-Pad4)'),'5':('VBAT','power_in','RTC_VBACKUP'),'6':('GND','power_in','GND'),'7':('INT','open_collector','EXP_INT'),'8':('SDA','bidirectional','I2C_SDA')}
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/split-c1/sd3078/'+s))
def remove_graphics(f):
    for a,b,_ in reversed(list(blocks(f,r'\((?:fp_line|fp_arc|fp_circle|fp_rect|fp_poly|fp_text|model|pad)\s'))):f=f[:a]+f[b:]
    return f
def rect(layer,xy,w,tag):
    return '(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'%(*xy,w,layer,uid(tag))
def rtc_geometry(f):
    if property_value(f,'Reference')!='U302' or '(at 18.215 20.675 90)' not in f:raise ValueError('RTC predecessor pose differs')
    f=remove_graphics(f).replace('(at 18.215 20.675 90)','(at 73 27.5)',1)
    extra=[rect('F.Fab',(-2.69,-2.665,2.69,2.665),.1,'rtcFab'),rect('F.CrtYd',(-4.9,-2.915,4.9,2.915),.05,'rtcCourtyard')]
    extra.append('(fp_circle (center -2.2 -2.1) (end -2.0 -2.1) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab") (uuid "%s"))'%uid('rtcPin1'))
    for n,(name,typ,net) in PINS.items():
        i=int(n);x=-3.65 if i<=4 else 3.65;y=-1.905+(i-1)*1.27 if i<=4 else 1.905-(i-5)*1.27
        extra.append('(pad "%s" smd rect (at %.6f %.6f) (size 2.0 0.7) (layers "F.Cu" "F.Mask" "F.Paste") (net "%s") (pinfunction "%s") (pintype "%s") (uuid "%s"))'%(n,x,y,net,name,typ,uid('rtcPad'+n)))
    f=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)',lambda m:'(descr '+json.dumps(RTC_DESCRIPTION)+')',f,count=1)
    f=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)',lambda m:'(tags '+json.dumps('WAVE SD3078 SOP8 208mil integrated crystal RTC')+')',f,count=1)
    return f[:f.rfind(')')]+'\n'+'\n'.join(extra)+'\n)'
def cap_geometry(f):
    if property_value(f,'Reference')!='C301' or '(at 45 22.5 90)' not in f:raise ValueError('CAP predecessor pose differs')
    f=remove_graphics(f).replace('(at 45 22.5 90)','(at 58.9 43.5)',1).replace('(attr smd)','(attr through_hole)',1)
    extra=[rect('F.CrtYd',(-10.95,-9.85,10.95,9.85),.05,'capCourtyard')]
    extra.append('(fp_circle (center 0 0) (end 9.6 0) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab") (uuid "%s"))'%uid('capFab'))
    for n,x,net in [('1',-9.5,'RTC_VBACKUP'),('2',9.5,'GND')]:
        extra.append('(pad "%s" thru_hole oval (at %s 0) (size 2.4 2.0) (drill oval 1.8 1.4) (layers "*.Cu" "*.Mask") (net "%s") (pinfunction "%s") (pintype "passive") (uuid "%s"))'%(n,x,net,'+' if n=='1' else '-',uid('capPad'+n)))
    extra.append('(fp_text user "+" (at -8 -1.8 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))) (uuid "%s"))'%uid('capPlus'))
    f=re.sub(r'\(descr\s+"(?:\\.|[^"\\])*"\)',lambda m:'(descr '+json.dumps(CAP_DESCRIPTION)+')',f,count=1)
    f=re.sub(r'\(tags\s+"(?:\\.|[^"\\])*"\)',lambda m:'(tags '+json.dumps('KAMCAP SE-5R5-D105VYH horizontal THT rechargeable RTC backup')+')',f,count=1)
    return f[:f.rfind(')')]+'\n'+'\n'.join(extra)+'\n)'
def clone_rtc_symbol(text):
    if '(symbol "'+RTC_SYMBOL+'"' in text:return text
    a,b,s=next((a,b,s) for a,b,s in blocks(text,r'\(symbol\s+"') if s.startswith('(symbol "Timer_RTC:RV-3028-C7"'))
    s=s.replace('Timer_RTC:RV-3028-C7',RTC_SYMBOL).replace('RV-3028-C7_',RTC_NAME+'_')
    for c,d,p in reversed(list(blocks(s,r'\(pin\s'))):
        old=re.search(r'\(number "([^"]+)"',p).group(1);n=PINMAP[old];name,typ,_=PINS[n]
        p=re.sub(r'^\(pin \S+','(pin '+typ,p,count=1)
        p=re.sub(r'\(name "(?:\\.|[^"\\])*"',lambda m:'(name '+json.dumps(name),p,count=1)
        p=p.replace('(number "'+old+'"','(number "'+n+'"')
        s=s[:c]+p+s[d:]
    for k,v in [('Value',RTC_NAME),('Footprint',RTC_FP),('Datasheet',RTC_DOC),('Description',RTC_DESCRIPTION)]:
        s=re.sub(r'\(property "'+k+r'" "(?:\\.|[^"\\])*"',lambda m:'(property '+json.dumps(k)+' '+json.dumps(v),s,count=1)
    return text[:b]+'\n'+s+text[b:]
def rtc_instance(s):
    s=s.replace('(lib_id "Timer_RTC:RV-3028-C7")','(lib_id "'+RTC_SYMBOL+'")',1)
    for a,b,p in reversed(list(blocks(s,r'\(pin\s+"'))):
        old=re.match(r'\(pin "([^"]+)"',p).group(1);p=p.replace('(pin "'+old+'"','(pin "'+PINMAP[old]+'"',1);s=s[:a]+p+s[b:]
    return s
def support(candidate):
    from _split_c1_domestic_eco import set_prop
    folder=Path(candidate)/REL
    p=folder/(STEM+'.kicad_sch');t=p.read_text()
    # These independent global-label stubs belong only to removed R303/R304 and old EVI.
    ends={(302.26,49.53),(302.26,52.07),(302.26,59.69),(302.26,62.23),(340.36,44.45),(340.36,46.99),(340.36,54.61),(340.36,57.15),(312.42,71.12)}
    for a,b,s in reversed(list(blocks(t,r'\((?:symbol\s+\(lib_id|wire\s|global_label\s)'))):
        ref=property_value(s,'Reference')
        pts=[tuple(map(float,m)) for m in re.findall(r'\((?:xy|at) ([-\d.]+) ([-\d.]+)',s)]
        if ref in {'R303','R304'} or (s.startswith('(wire ') and any(p in ends for p in pts)) or (s.startswith('(global_label ') and any(p in ends for p in pts)):t=t[:a]+t[b:]
    for a,b,z in reversed(list(blocks(t,r'\(symbol\s+\(lib_id\s'))):
        if property_value(z,'Reference')=='C302':
            z=set_prop(z,'Datasheet',RTC_DOC);z=set_prop(z,'Description','FH100nF/25V X7R local SD3078 VDD bypass.');t=t[:a]+z+t[b:]
    e=t.rfind(')');t=t[:e]+'\n(no_connect (at 317.5 71.12) (uuid "'+uid('nc4')+'"))\n'+t[e:];p.write_text(t)
    p=folder/(STEM+'.kicad_pcb');t=p.read_text()
    for a,b,s in reversed(list(blocks(t,r'\(footprint\s'))):
        r=property_value(s,'Reference')
        if r in {'R303','R304'}:t=t[:a]+t[b:]
        elif r=='C302':
            s=re.sub(r'\(at 16.815 17.975(?: [-\d.]+)?\)','(at 66.8 28.135 180)',s,count=1)
            for c,d,pad in reversed(list(blocks(s,r'\(pad\s'))):
                pad=re.sub(r'\(at ([-\d.]+) ([-\d.]+)(?: [-\d.]+)?\)',r'(at \1 \2 180)',pad,count=1);s=s[:c]+pad+s[d:]
            s=set_prop(s,'Datasheet',RTC_DOC);s=set_prop(s,'Description','FH100nF/25V X7R local SD3078 VDD bypass.')
            t=t[:a]+s+t[b:]
    p.write_text(t)
    lib=Path(candidate)/'lib/panda-standard.kicad_sym';t=lib.read_text()
    if '(symbol "SD3078"' not in t:
        s=next(s for _,_,s in blocks((folder/(STEM+'.kicad_sch')).read_text(),r'\(symbol\s+"') if s.startswith('(symbol "'+RTC_SYMBOL+'"'))
        s=s.replace('(symbol "'+RTC_SYMBOL+'"','(symbol "SD3078"',1);e=t.rfind(')');lib.write_text(t[:e]+'\n'+s+'\n'+t[e:])

def apply_rtc_routing(candidate):
    from _core_c1_pcb_patch import copper,digest
    p=Path(candidate)/REL/(STEM+'.kicad_pcb');t=p.read_text()
    d=json.loads((ROOT/'split-c1-rtc-layout.json').read_text())
    if digest(t)!=d['source_copper_sha256']:raise ValueError('RTC copper predecessor differs')
    norm=lambda s:re.sub(r'\s+',' ',s)
    existing=copper(t)
    for a,b,s in reversed(list(blocks(t,r'\((?:segment|via)\s'))):
        u=re.search(r'\(uuid "([^"]+)"',s).group(1)
        if u in d['removed_copper']:
            if norm(s)!=norm(d['removed_copper'][u]):raise ValueError('RTC removed copper differs')
            t=t[:a]+t[b:]
        elif u in d['modified_copper']:
            q=d['modified_copper'][u]
            if norm(s)!=norm(q['old']):raise ValueError('RTC modified copper differs')
            t=t[:a]+q['new']+t[b:]
    if any(u in existing for u in d['added_copper']):raise ValueError('RTC copper UUID collision')
    e=t.rfind(')');t=t[:e]+'\n'+'\n'.join(d['added_copper'].values())+'\n'+t[e:]
    if digest(t)!=d['routed_copper_sha256']:raise ValueError('RTC copper replay differs')
    p.write_text(t)
