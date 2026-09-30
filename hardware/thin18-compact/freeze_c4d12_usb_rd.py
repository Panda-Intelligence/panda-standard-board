#!/usr/bin/env python3
from pathlib import Path
import re,sys
cand=Path(sys.argv[1]).resolve()
rel=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
sch=cand/rel/'usb-interface.kicad_sch'
pcb=cand/rel/'PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_pcb'
def balanced(s,a):
 d=0;q=False;esc=False
 for i in range(a,len(s)):
  c=s[i]
  if q:
   if esc:esc=False
   elif c=='\\':esc=True
   elif c=='"':q=False
  else:
   if c=='"':q=True
   elif c=='(':d+=1
   elif c==')':
    d-=1
    if d==0:return i+1
 raise RuntimeError
def prop(name,val):
 return f'(property "{name}" "{val}" (at 0 0 0) (hide yes) (show_name no) (do_not_autoplace no) (effects (font (size 1 1))))'
s=sch.read_text()
for ref in ['R206','R207']:
 i=s.index(f'(property "Reference" "{ref}"');a=s.rfind('(symbol ',0,i);b=balanced(s,a);z=s[a:b]
 z=z.replace('(property "Value" "5.1k / USB-C Rd"','(property "Value" "5.1k ±5% / USB-C Rd"',1)
 z=z.replace('(property "Datasheet" ""','(property "Datasheet" "https://www.lcsc.com/product-detail/C453708.html"',1)
 z=z.replace('(property "Description" "USB Type-C sink Rd; 5.1k 1%; exact mainland MPN sourcing still open"','(property "Description" "USB Type-C sink Rd; Fenghua 5.1k ±5% 0402, mainland exact production MPN"',1)
 pin=z.index('(pin "1"')
 z=z[:pin]+' '.join([prop('Manufacturer','FH (Guangdong Fenghua Advanced Tech)'),prop('MPN','RC-02K512JT'),prop('LCSC','C453708'),prop('Tolerance','5%'),prop('Power_Rating','62.5mW'),prop('ECO_ID','THIN18-C4D12-USB-RD')])+' '+z[pin:]
 s=s[:a]+z+s[b:]
sch.write_text(s)
s=pcb.read_text()
for ref in ['R206','R207']:
 i=s.index(f'(property "Reference" "{ref}"');a=s.rfind('(footprint ',0,i);b=balanced(s,a);z=s[a:b]
 z=z.replace('(property "Value" "5.1k / USB-C Rd"','(property "Value" "5.1k ±5% / USB-C Rd"',1)
 z=z.replace('(property "Datasheet" ""','(property "Datasheet" "https://www.lcsc.com/product-detail/C453708.html"',1)
 z=z.replace('(property "Description" "USB Type-C sink Rd; 5.1k 1%; exact mainland MPN sourcing still open"','(property "Description" "USB Type-C sink Rd; Fenghua 5.1k ±5% 0402, mainland exact production MPN"',1)
 attr=z.index('(attr smd)')
 extras=' '.join(f'(property "{k}" "{v}" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))' for k,v in {
  'Manufacturer':'FH (Guangdong Fenghua Advanced Tech)','MPN':'RC-02K512JT','LCSC':'C453708','Tolerance':'5%','Power_Rating':'62.5mW','ECO_ID':'THIN18-C4D12-USB-RD'}.items())
 z=z[:attr]+extras+' '+z[attr:]
 s=s[:a]+z+s[b:]
pcb.write_text(s)
print('R206/R207 -> FH RC-02K512JT / C453708')
