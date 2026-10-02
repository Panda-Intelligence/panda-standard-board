// Thin7 MECHANICAL PARTITION; empty PCB outlines, not fabrication inputs.
// Panel/pouch/connector/support tolerances and routing are not qualified.
module slab(r,z,h){translate([r[0],r[1],z])cube([r[2]-r[0],r[3]-r[1],h]);}
module rounded(w,h,r,z){translate([r,r,0])linear_extrude(height=z)offset(r=r)square([w-2*r,h-2*r]);}
color([.1,.12,.14])rounded(112,75,5,.55);
color([.1,.12,.14])translate([0,0,.55])difference(){rounded(112,75,5,5.75);translate([.65,.65,-.01])rounded(110.7,73.7,4.35,5.77);}
color([.1,.12,.14])translate([0,0,6.8])difference(){rounded(112,75,5,.2);translate([10.2,5.945,-.01])linear_extrude(height=.22)offset(r=1.1)square([91.6,54.48]);}
color([.1,.12,.14])translate([0,0,6.3])difference(){rounded(112,75,5,.5);translate([3.085,1.75,-.01])cube([105.83,62.87,.52]);}
color([.05,.4,.22])translate([0,0,0.7])linear_extrude(height=.8)polygon([[5, 57], [66, 57], [66, 42], [104, 42], [104, 72], [5, 72]]); // Core-Thin7 EMPTY TEMPLATE
color([.06,.23,.38])translate([0,0,0.7])linear_extrude(height=.8)polygon([[65.9, 4], [110.9, 4], [110.9, 40], [65.9, 40]]); // Display-Thin7 EMPTY TEMPLATE
color([.65,.66,.63])slab([3, 3, 65, 54],.7,3.1); // complete-pack MAX requirement; not selected SKU
color([1,.6,.1,.20])slab([3, 3, 65, 54],3.8,.5); // swelling space, must remain empty
color([.17,.17,.17,.35])slab([3.335, 2.0, 108.665, 64.37],4.6,2.2); // panel thickness budget
// Border frame covers the inactive panel area ABOVE6.8 only; underside pocket avoids solid overlap.
// Uniform outer thickness7.0mm; no scaled native PCB/module/component bodies.
