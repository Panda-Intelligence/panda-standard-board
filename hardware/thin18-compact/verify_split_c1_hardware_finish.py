#!/usr/bin/env python3
"""Independent native hardware-inhibit contract; topology is not a bench result."""
import argparse,copy,json,re
from pathlib import Path
from _split_c1_common import ROOT,REPO,REL,STEM,repo_entry
from _split_c1_sourcing import blocks,property_value
from verify_split_c1_power_integrity import parse_netlist,check
PINS={
 'Q907':{'1':'CHG_REQUEST','2':'CHG_nCE','3':'CHG_RETURN'},
 'Q908':{'1':'FL_HWEN','2':'CHG_RETURN','3':'GND'},
 'R930':{'1':'CHG_nCE','2':'SGM41513_REGN'},
 'R931':{'1':'HW_ARM_GPIO','2':'FL_HWEN'},
 'R932':{'1':'CHG_REQUEST','2':'GND'},'R933':{'1':'FL_HWEN','2':'GND'},
 'TP19':{'1':'FL_HWEN'},'R607':{'1':'CHG_REQUEST','2':'GND'},'R601':{'1':'FL_HWEN','2':'GND'},
}
IDENTITIES={
 'Q907':('JSMSEMI','NX3008NBK,215-JSM','C53113911'),
 'Q908':('JSMSEMI','NX3008NBK,215-JSM','C53113911'),
 'R930':('FH (Fenghua Advanced)','RC-02K1003FT','C140219'),
 'R931':('FH (Fenghua Advanced)','RS-03K1201FT','C118396'),
 'R932':('FH (Fenghua Advanced)','RC-02K1002FT','C140215'),
 'R933':('FH (Fenghua Advanced)','RC-02K1002FT','C140215'),
}

def verify(fields,pins,nets):
 for ref,expected in IDENTITIES.items():
  check(tuple(fields.get(ref,{}).get(k,'') for k in ['Manufacturer','MPN','LCSC'])==expected,'Wrong inhibit part '+ref)
 for ref,mapping in PINS.items():
  check({p:n for (r,p),n in pins.items() if r==ref}==mapping,'Wrong inhibit pin map '+ref)
 check(pins.get(('U901','9'))=='CHG_nCE','Charger nCE not isolated')
 check(pins.get(('U601','9'))=='CHG_REQUEST','Expander request polarity/net differs')
 check(pins.get(('U601','18'),'').startswith('unconnected-'),'P15 must not drive direct permit')
 check(pins.get(('U501','38'))=='HW_ARM_GPIO','Direct permit must use module GPIO2/pad38')
 check(pins.get(('U905','19'))=='FL_HWEN','Frontlight hardware EN not directly inhibited')
 check(nets.get('CHG_nCE')=={('U901','9'),('R930','1'),('Q907','2')},'Unexpected nCE driver/backfeed')
 check(nets.get('CHG_RETURN')=={('Q907','3'),('Q908','2')},'Series authorization bypassed')
 check(nets.get('CHG_REQUEST')=={('U601','9'),('R607','1'),('R932','1'),('Q907','1')},'Unexpected charge-request driver')
 check(nets.get('HW_ARM_GPIO')=={('U501','38'),('R931','1')},'Direct GPIO bypasses limiting resistor')
 check(nets.get('FL_HWEN')=={('R931','2'),('R601','1'),('R933','1'),('Q908','1'),('TP19','1'),('U905','19')},'Unexpected hardware-permit connection')
 check('BQ_CE' not in nets,'Obsolete active-low expander net remains')
 return True

def negative_controls(fields,pins,nets):
 cases=[]
 for ref,p in [('Q907','2'),('Q908','2'),('R930','2'),('R932','2'),('R933','2'),('R931','1'),('U501','38'),('U901','9'),('U601','18'),('U905','19')]:
  bad=pins.copy();bad[(ref,p)]='UNREVIEWED_NET';cases.append((fields,bad,nets))
 for ref in IDENTITIES:
  bad=copy.deepcopy(fields);bad[ref]['MPN']='LOOKALIKE';cases.append((bad,pins,nets))
 for net in ['CHG_nCE','CHG_RETURN','CHG_REQUEST','HW_ARM_GPIO','FL_HWEN']:
  bad=copy.deepcopy(nets);bad[net].add(('UNREVIEWED_DRIVER','1'));cases.append((fields,pins,bad))
 for args in cases:
  try:verify(*args)
  except ValueError:continue
  raise AssertionError('Bad inhibit fixture accepted')
 return len(cases)

def inspect(candidate,netlist):
 candidate=Path(candidate);pcb=candidate/REL/(STEM+'.kicad_pcb')
 fields,pins,nets=parse_netlist(netlist);verify(fields,pins,nets)
 fps={property_value(f,'Reference'):f for _,_,f in blocks(pcb.read_text(),r'\(footprint\s')}
 for ref,mapping in PINS.items():
  f=fps[ref];check('(dnp yes)' not in f,'Required inhibit part DNP')
  padnets={}
  for _,_,p in blocks(f,r'\(pad\s'):
   n=re.match(r'\(pad\s+"([^\"]*)"',p).group(1);net=re.search(r'\(net\s+"([^\"]+)"',p)
   if n and net:padnets[n]=net.group(1)
  check(padnets==mapping,'PCB inhibit connectivity differs '+ref)
  if ref in IDENTITIES:check(tuple(property_value(f,k) for k in ['Manufacturer','MPN','LCSC'])==IDENTITIES[ref],'PCB inhibit identity differs')
  if ref in ['Q907','Q908']:
   for _,_,p in blocks(f,r'\(pad\s'):
    n=re.match(r'\(pad\s+"([^\"]+)"',p).group(1)
    xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
    size=tuple(map(float,re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
    check(xy=={'1':(-1.01,-.95),'2':(-1.01,.95),'3':(1.01,0)}[n] and size==(.8,.6),'Wrong original-maker MOS lands/pins')
 # Truth table is an electrical topology model, not an analog measurement.
 truth=[{'request':a,'permit':b,'nCE_sink_allowed':bool(a and b),'frontlight_EN':bool(b)} for a in [0,1] for b in [0,1]]
 return {'schema':'panda-split-c1-hardware-finish-verification-v1','inputs':{'pcb':repo_entry(pcb),'schematic':repo_entry(pcb.with_suffix('.kicad_sch')),'checker':repo_entry(Path(__file__)),'contract':repo_entry(ROOT/'split-c1-hardware-finish.json')},
 'default_off_topology_passed':True,'non_i2c_shutdown_path_present':True,'new_exact_identities_verified':len(IDENTITIES),
 'mos_pin_land_check_passed':True,'negative_cases_rejected':negative_controls(fields,pins,nets),'truth_table':truth,
 'physical_ramp_and_shutdown_tested':False,'independent_autonomous_watchdog_present':False,'manufacturing_release':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,default=ROOT/'core-c1-96x68-split');p.add_argument('--netlist',type=Path);p.add_argument('--output',type=Path,default=ROOT/'split-c1-hardware-finish-verification.json');a=p.parse_args()
 report=inspect(a.candidate,a.netlist or a.candidate/'verification/netlist.xml');a.output.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='inputs'},indent=2))
if __name__=='__main__':main()
