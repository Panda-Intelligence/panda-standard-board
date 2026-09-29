# C0 fold70x64 placement candidate

**Placement feasibility only — intentionally unrouted — NOT FOR FABRICATION.**

Generated from `thin18/routing142` by `../build_c0_fold.py`.

- outline: 70 × 64 mm, preserving the USB4500 mid-mount cutout
- 202 PCB footprints preserved
- 88 upper-cluster footprints moved by -64 mm in Y
- legacy tracks/vias/zones removed
- four mounting holes relocated
- schematic/netlist is unchanged

Current verification:

- DRC rule violations: 0
- expected unconnected items: 449
- schematic parity: 0
- ERC: 0
- schematic refs: 203
- pin/net tuples: 601
- netlist identical to routing142: yes
- new footprint bounding-box overlap pairs: 0

`routing142` remains the routing authority for the old 70 × 128.1 mm form factor. C0 must be routed from scratch if promoted.
