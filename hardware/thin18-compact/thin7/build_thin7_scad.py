"""Replay an exact envelope SCAD from the mechanical contract, without fit signoff."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
c=json.loads((ROOT/'thin7-mechanical-contract.json').read_text())
lines=['// Thin7 MECHANICAL PARTITION; empty PCB outlines, not fabrication inputs.',
       '// Panel/pouch/connector/support tolerances and routing are not qualified.',
       'module slab(r,z,h){translate([r[0],r[1],z])cube([r[2]-r[0],r[3]-r[1],h]);}',
       'module rounded(w,h,r,z){translate([r,r,0])linear_extrude(height=z)offset(r=r)square([w-2*r,h-2*r]);}',
       'color([.1,.12,.14])rounded(112,75,5,.55);',
       'color([.1,.12,.14])translate([0,0,.55])difference(){rounded(112,75,5,5.75);translate([.65,.65,-.01])rounded(110.7,73.7,4.35,5.77);}',
       'color([.1,.12,.14])translate([0,0,6.8])difference(){rounded(112,75,5,.2);translate([10.2,5.945,-.01])linear_extrude(height=.22)offset(r=1.1)square([91.6,54.48]);}',
       'color([.1,.12,.14])translate([0,0,6.3])difference(){rounded(112,75,5,.5);translate([3.085,1.75,-.01])cube([105.83,62.87,.52]);}']
for name,b in c['boards'].items():
    color='[.05,.4,.22]' if name.startswith('Core') else '[.06,.23,.38]'
    lines.append('color('+color+')translate([0,0,'+str(b['z_bottom_mm'])+'])linear_extrude(height=.8)polygon('+json.dumps(b['outline_xy_mm'])+'); // '+name+' EMPTY TEMPLATE')
b=c['battery'];p=c['panel']
lines += ['color([.65,.66,.63])slab('+json.dumps(b['rect_xyxy_mm'])+',.7,3.1); // complete-pack MAX requirement; not selected SKU',
          'color([1,.6,.1,.20])slab('+json.dumps(b['rect_xyxy_mm'])+',3.8,.5); // swelling space, must remain empty',
          'color([.17,.17,.17,.35])slab('+json.dumps(p['rect_xyxy_mm'])+',4.6,2.2); // panel thickness budget',
          '// Border frame covers the inactive panel area ABOVE6.8 only; underside pocket avoids solid overlap.',
          '// Uniform outer thickness7.0mm; no scaled native PCB/module/component bodies.']
(ROOT/'THIN7-ENCLOSURE-STUDY.scad').write_text('\n'.join(lines)+'\n')
