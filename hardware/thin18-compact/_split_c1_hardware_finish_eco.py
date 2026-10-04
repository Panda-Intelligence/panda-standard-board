"""Deterministic hardware-finish ECO for the isolated Split-C1 board candidate."""
from pathlib import Path
import json, re, subprocess, uuid
from _split_c1_common import ROOT, REL, STEM, kicad_python
from _split_c1_sourcing import blocks, property_value
from _split_c1_domestic_eco import set_prop
from _split_c1_power_integrity_eco import refill_zones, board_zones
ECO='SPLIT-C1-HARDWARE-FINISH-01'
MOS_MPN='NX3008NBK,215-JSM'
MOS_NAME='NX3008NBK_215_JSM'
MOS_FP='JSM_NX3008NBK_SOT23'
PIN_NETS={
 'Q907':{'1':'CHG_REQUEST','2':'CHG_nCE','3':'CHG_RETURN'},
 'Q908':{'1':'FL_HWEN','2':'CHG_RETURN','3':'GND'},
 'R930':{'1':'CHG_nCE','2':'SGM41513_REGN'},
 'R931':{'1':'HW_ARM_GPIO','2':'FL_HWEN'},
 'R932':{'1':'CHG_REQUEST','2':'GND'},
 'R933':{'1':'FL_HWEN','2':'GND'},
 'TP19':{'1':'FL_HWEN'},
}
DEFAULT_POSES={'Q907': [[53.25, 8.25], 180], 'Q908': [[52.75, 11.75], 90], 'R930': [[51.75, 5.25], 90], 'R932': [[51.0, 9.0], 90], 'R933': [[55.25, 11.25], 90], 'R931': [[73.5, 66.0], 0], 'TP19': [[58.0, 17.0], 0]}
def uid(tag):return str(uuid.uuid5(uuid.NAMESPACE_URL,'panda/split-c1/hardware-finish/'+tag))
def identity(block,tag):
 counter=iter(range(1000))
 return re.sub(r'\(uuid "[^\"]+"\)',lambda m:'(uuid "'+uid(tag+'-'+str(next(counter)))+'")',block)
def find_instance(text,ref):
 return next(b for _,_,b in blocks(text,r'\(symbol\s+\(lib_id\s') if property_value(b,'Reference')==ref)
def find_fp(text,ref):
 return next(b for _,_,b in blocks(text,r'\(footprint\s') if property_value(b,'Reference')==ref)
def append_root(text,addition):
 end=text.rfind(')');return text[:end]+'\n'+addition+'\n'+text[end:]
def label(net,x,y,tag,angle=0):
 return f'(global_label "{net}" (shape passive) (at {x:.6f} {y:.6f} {angle}) (effects (font (size 1 1)) (justify {"left" if angle==0 else "right"} bottom)) (uuid "{uid(tag)}"))\n'
def change_pad_net(fp,pin,net):
 count=0
 for a,b,pad in reversed(list(blocks(fp,r'\(pad\s'))):
  if re.match(r'\(pad\s+"'+pin+r'"\s',pad):
   pad=re.sub(r'\(net\s+"[^\"]+"\)','(net "'+net+'")',pad,count=1);fp=fp[:a]+pad+fp[b:];count+=1
 if count!=1:raise ValueError('Expected one pad '+pin)
 return fp

def apply_structure(candidate):
 candidate=Path(candidate);folder=candidate/REL
 sch=folder/(STEM+'.kicad_sch');pcb=folder/(STEM+'.kicad_pcb')
 original=sch.read_text()
 existing_refs={property_value(f,'Reference') for _,_,f in blocks(pcb.read_text(),r'\(footprint\s')}
 if existing_refs & set(PIN_NETS):raise ValueError('New hardware ref already exists: '+str(existing_refs & set(PIN_NETS)))
 root_id=re.search(r'\(uuid\s+"([^\"]+)"',original).group(1)
 text=original.replace('"BQ_CE"','"CHG_REQUEST"');seen=set()
 for a,b,item in reversed(list(blocks(text,r'\((?:global_label|wire|no_connect)\s'))):
  if 'f7429647-3d40-5d4c-aa18-d3cfb326821c' in item:
   item=item.replace('"CHG_REQUEST"','"CHG_nCE"');seen.add('charger')
  elif 'c081e9cc-b301-543a-932c-605e9054f6c3' in item:item='';seen.add('expander_label')
  elif item.startswith('(wire ') and re.search(r'\(xy 78\.74 83\.82\)',item) and re.search(r'\(xy 86\.36 83\.82\)',item):item='';seen.add('expander_wire')
  elif item.startswith('(no_connect ') and re.search(r'\(at 134\.62 38\.1\)',item):item='';seen.add('host_nc')
  text=text[:a]+item+text[b:]
 if seen!={'charger','expander_label','expander_wire','host_nc'}:raise ValueError('Unexpected enable-net predecessor: '+str(seen))
 text=append_root(text,label('HW_ARM_GPIO',134.62,38.1,'host-arm')+f'(no_connect (at 78.74 83.82) (uuid "{uid("nc-expander-p15")}"))')
 for a,b,inst in reversed(list(blocks(text,r'\(symbol\s+\(lib_id\s'))):
  ref=property_value(inst,'Reference')
  if ref=='R607':
   inst=set_prop(inst,'Value','100k / CHG_REQUEST_PD');inst=set_prop(inst,'Description','Default-low request at XL9535 P05; drives Q907 gate, never directly tied to nCE or REGN. Parallel R93210k strengthens low state.')
  elif ref=='R601':inst=set_prop(inst,'Description','Default-low direct hardware permit. R931 isolates GPIO2; low disables frontlight EN and charger authorization independently of I2C. Parallel R93310k strengthens low state.')
  text=text[:a]+inst+text[b:]
 display=ROOT/'display-c1-45x36-production-bom';ds=(display/'PANDA-EPD0426-SPI-EVT.kicad_sch').read_text()
 definition=next(s for _,_,s in blocks(ds,r'\(symbol\s+"') if s.startswith('(symbol "panda-r6-display:'+MOS_NAME+'"'))
 definition=definition.replace('panda-r6-display:', 'panda-standard:')
 _,end,_=next(blocks(text,r'\(lib_symbols\s'));text=text[:end-1]+definition+text[end-1:]
 lib=candidate/'lib/panda-standard.kicad_sym';s=lib.read_text();lib.write_text(append_root(s,definition.replace('"panda-standard:'+MOS_NAME+'"','"'+MOS_NAME+'"',1)))
 source_mod=display/'panda-r6-display.pretty'/(MOS_FP+'.kicad_mod')
 (candidate/'lib/panda-standard.pretty'/(MOS_FP+'.kicad_mod')).write_bytes(source_mod.read_bytes())
 fields={};sch_items=''
 configs=[('Q907',40.64,238.76),('Q908',86.36,238.76),('R930',40.64,213.36),('R931',127.0,238.76),('R932',86.36,213.36),('R933',127.0,213.36),('TP19',165.1,238.76)]
 for ref,x,y in configs:
  template=find_instance(ds,'Q1') if ref.startswith('Q') else find_instance(original,{'R930':'R607','R931':'R204','R932':'R510','R933':'R510','TP19':'TP16'}[ref])
  libid='panda-standard:'+MOS_NAME if ref.startswith('Q') else re.search(r'\(lib_id "([^\"]+)"',template).group(1)
  pin_def=definition if ref.startswith('Q') else next(v for _,_,v in blocks(original,r'\(symbol\s+"') if v.startswith('(symbol "'+libid+'"'))
  props={k:property_value(template,k) for k in ['Value','Footprint','Manufacturer','MPN','LCSC','Datasheet','Description']}
  if ref.startswith('Q'):props.update(Value=MOS_MPN,Footprint='panda-standard:'+MOS_FP,Description='JSM 1G/2D/3S NMOS in low-current two-permission charger inhibit; not the battery power path.')
  elif ref=='R930':props.update(Value='100k / nCE default OFF',Description='nCE pullup to pre-AON REGN; Q907 and Q908 must both conduct to authorize charging.')
  elif ref=='R931':props.update(Value='1.2k / hardware permit',Description='Series GPIO2 resistor limits manual clamp current. Low permit inhibits frontlight and charging without I2C.')
  elif ref in ['R932','R933']:props.update(Value='10k / gate default LOW',Description='Strong default-low gate bias, using the already reviewed FH10k exact part.')
  else:props.update(Value='HW_ARM / FORCE LOW',Description='Copper-only test access. Pull low to inhibit frontlight and charging. R931 limits GPIO contention; never inject voltage.')
  fields[ref]=props
  inst=f'(symbol (lib_id "{libid}") (at {x} {y} 0) (unit 1) (in_bom {"no" if ref.startswith("TP") else "yes"}) (on_board yes) (dnp no) (uuid "{uid(ref+"-instance")}"))'
  inst=inst[:-1]+'\n'
  for k,v in {'Reference':ref,**props}.items():
   if v is None:continue
   yy=y-8 if k=='Reference' else y-6 if k=='Value' else y
   inst+=f'(property {json.dumps(k)} {json.dumps(v)} (at {x} {yy} 0) {"" if k in ["Reference","Value"] else "(hide yes) "}(effects (font (size 0.9 0.9))))\n'
  for n in PIN_NETS[ref]:inst+=f'(pin "{n}" (uuid "{uid(ref+"-pin-"+n)}"))\n'
  inst+=f'(instances (project "{STEM}" (path "/{root_id}" (reference "{ref}") (unit 1)))))\n'
  for _,_,pin in blocks(pin_def,r'\(pin\s'):
   n=re.search(r'\(number "([^\"]+)"',pin).group(1)
   if n not in PIN_NETS[ref]:continue
   px,py,angle=map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',pin).groups())
   inst+=label(PIN_NETS[ref][n],x+px,y-py,ref+'-label-'+n,180 if angle==180 else 0)
  sch_items+=inst
 sch.write_text(append_root(text,sch_items))
 contract_path=candidate/'frontlight-firmware-contract.json'
 if contract_path.exists():
  d=json.loads(contract_path.read_text());d['hardware_enable_source']='ESP32-S3 GPIO2 through R931; no longer XL9535 P15';d['shutdown_sequence']=['drive GPIO2=0 immediately without I2C','best-effort clear XL9535 P16 PWM'];d['charging_request']='P05 CHG_REQUEST must remain0 unless the battery/charging configuration is separately qualified';contract_path.write_text(json.dumps(d,indent=2)+'\n')
 text=pcb.read_text().replace('"BQ_CE"','"CHG_REQUEST"')
 remove={'d974696a-1387-40ab-9a51-8451b5053465','3fd8a347-0dff-4fb6-ba30-24a37c37e4fc','f09d6024-e41f-4fb5-b8b3-72108abb91bd','f60881e8-3c80-4373-b497-790cfc066d0c'}
 found=set()
 for a,b,part in reversed(list(blocks(text,r'\((?:segment|via)\s'))):
  object_id=re.search(r'\(uuid "([^\"]+)"',part).group(1)
  if object_id in remove:found.add(object_id);text=text[:a]+text[b:]
 if found!=remove:raise ValueError('Unexpected old enable copper')
 for a,b,f in reversed(list(blocks(text,r'\(footprint\s'))):
  ref=property_value(f,'Reference')
  if ref=='U901':f=change_pad_net(f,'9','CHG_nCE')
  elif ref=='U601':f=change_pad_net(f,'18','unconnected-(U601-P15-Pad18)')
  elif ref=='U501':f=change_pad_net(f,'38','HW_ARM_GPIO')
  elif ref in ['R607','R601']:
   matching=find_instance(sch.read_text(),ref)
   for k in ['Value','Description']:f=set_prop(f,k,property_value(matching,k))
  text=text[:a]+f+text[b:]
 display_pcb=(display/'PANDA-EPD0426-SPI-EVT.kicad_pcb').read_text()
 for ref in PIN_NETS:
  fp=find_fp(display_pcb,'Q1') if ref.startswith('Q') else find_fp(text,{'R930':'R607','R931':'R204','R932':'R510','R933':'R510','TP19':'TP16'}[ref])
  fp=identity(fp,ref)
  fp=set_prop(fp,'Reference',ref)
  for k,v in fields[ref].items():
   if v is not None and k!='Footprint':fp=set_prop(fp,k,v)
  if ref.startswith('Q'):fp=fp.replace('"panda-r6-display:'+MOS_FP+'"','"panda-standard:'+MOS_FP+'"',1)
  fp=re.sub(r'\(path "[^\"]+"\)','(path "/'+root_id+'/'+uid(ref+'-instance')+'")',fp,count=1)
  for pin,net in PIN_NETS[ref].items():fp=change_pad_net(fp,pin,net)
  text=append_root(text,fp)
 pcb.write_text(text)
 return fields

def apply_native(candidate,poses=None):
 import wx
 app=wx.App(False)
 import pcbnew as P
 import tempfile
 candidate=Path(candidate);pcb=candidate/REL/(STEM+'.kicad_pcb')
 fields=apply_structure(candidate);original=pcb.read_text();board=P.LoadBoard(str(pcb))
 for ref,(xy,angle) in (poses or DEFAULT_POSES).items():
  f=board.FindFootprintByReference(ref)
  if f is None:raise ValueError('New footprint missing: '+ref)
  f.SetPosition(P.VECTOR2I(P.FromMM(xy[0]),P.FromMM(xy[1])));f.SetOrientationDegrees(angle);f.SetLocked(True)
  f.Reference().SetVisible(False)
 board.BuildConnectivity()
 for z in board.Zones():z.SetNeedRefill(True)
 P.ZONE_FILLER(board).Fill(board.Zones())
 with tempfile.TemporaryDirectory(prefix='split-c1-finish-') as temp:
  saved=Path(temp)/'native.kicad_pcb';P.SaveBoard(str(saved),board);text=saved.read_text()
 for a,b,f in reversed(list(blocks(original,r'\(footprint\s'))):
  ref=property_value(f,'Reference')
  if ref in PIN_NETS:original=original[:a]+find_fp(text,ref)+original[b:]
 fresh=board_zones(text);old=board_zones(original)
 if len(fresh)!=len(old):raise ValueError('Zone inventory changed')
 for (a,b,z),(_,_,replacement) in reversed(list(zip(old,fresh))):original=original[:a]+replacement+original[b:]
 pcb.write_text(original)
 (candidate/'hardware-finish-fields.json').write_text(json.dumps(fields,indent=2)+'\n')

def apply_routing(candidate):
 from _core_c1_pcb_patch import copper,digest
 p=Path(candidate)/REL/(STEM+'.kicad_pcb');text=p.read_text()
 plan=json.loads((ROOT/'split-c1-hardware-finish-layout.json').read_text())
 if digest(text)!=plan['source_copper_sha256']:raise ValueError('Hardware-finish copper predecessor differs')
 existing=copper(text)
 for a,b,part in reversed(list(blocks(text,r'\((?:segment|via)\s'))):
  object_id=re.search(r'\(uuid "([^\"]+)"',part).group(1)
  if object_id in plan['removed_copper']:
   if re.sub(r'\s+',' ',part)!=re.sub(r'\s+',' ',plan['removed_copper'][object_id]):raise ValueError('Removed stub predecessor differs')
   text=text[:a]+text[b:]
 if set(existing)&set(plan['added_copper']):raise ValueError('Route UUID collision')
 text=append_root(text,'\n'.join(plan['added_copper'].values()))
 if digest(text)!=plan['routed_copper_sha256']:raise ValueError('Hardware-finish route digest differs')
 p.write_text(text);refill_zones(p)
 p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')

def apply_hardware_finish_eco(candidate):
 subprocess.run([kicad_python(),str(Path(__file__).resolve()),'--candidate',str(Path(candidate).resolve()),'--with-routing'],check=True)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--with-routing',action='store_true');parser.add_argument('--poses',type=Path)
 args=parser.parse_args();poses=json.loads(args.poses.read_text()) if args.poses else None
 apply_native(args.candidate,poses)
 if args.with_routing:apply_routing(args.candidate)
