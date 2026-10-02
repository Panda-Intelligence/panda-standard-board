// Review-only space budget: no case ports, supports, exact bodies or fit signoff.
// Source: split-c1-mechanical-inputs.json; Core XY uses native KiCad coordinates.
outer=[112, 75, 21];
pack_rect=[1, 11, 37, 65];
pack_max=[36, 54, 5.5];
panel_back=8.0;
panel_thickness=2.2;
battery_top=-1.8;
swelling=0.7;
rear=-8.9;
module slab(r,z,h){translate([r[0],r[1],z])cube([r[2]-r[0],r[3]-r[1],h]);}
color([0.1,0.5,0.2])slab([0,0,96,68],0,.8); // Core-C1
color([0.1,0.25,0.7])slab([38,30,83,66],-2.3,.8); // Display-C1 mirrored
color([.85,.65,.1])slab(pack_rect,battery_top-pack_max[2],pack_max[2]);
color([1,.6,.2,.25])slab(pack_rect,battery_top-pack_max[2]-swelling,swelling);
color([.15,.15,.15])slab([-4.665,2.815,100.665,65.185],panel_back,panel_thickness);
color([.6,.8,1,.10])translate([48-outer[0]/2,34-outer[1]/2,rear])cube(outer);
// Engineering shell box112x75x21; no fabrication or3D-print approval.
color([.7,.3,.2])translate([59.4,43.5,1.0])cylinder(h=6.5,d=19.2,$fn=80); // C301 H3C primary overall H maximum plus0.2mm stand-off
// Component/lead/FPC/tool/antenna/speaker solids and mount bosses omitted.
