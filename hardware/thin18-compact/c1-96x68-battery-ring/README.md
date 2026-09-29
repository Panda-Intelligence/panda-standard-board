# C1 96×68 battery-ring placement candidate

**Placement feasibility only — intentionally unrouted — NOT FOR FABRICATION.**

C1 is the preferred compact architecture candidate after the C0 area proof.

## Geometry

- PCB outline: **96 × 68 mm**
- layers/thickness inherited from routing142: 4 layers / 0.8 mm
- USB-C J201 remains a mid-mount edge connector at the y=68 edge
- microSD J501 is anchored near the right edge for external card access
- rear battery envelope: **64 × 60 mm**, x=21..85, y=4..64
- this battery plan area is about **94.1%** of the previous ~60 × 68 mm envelope
- 30 movable bottom-side footprints are packed outside the battery envelope
- J503 stays at its original routing142 coordinate to retain its validated debug-footprint/library state

## Electrical invariants

Fresh checks on this candidate:

- DRC rule violations: **0**
- expected unconnected items: **449** (all legacy routing was intentionally removed)
- schematic parity: **0**
- ERC: **0**
- schematic refs: **203**
- pin/net tuples: **601**
- netlist identical to routing142: **yes**
- new same-layer footprint bounding-box overlap pairs: **0**

The 449 unconnected items are not failures of the architecture proof; they are the explicit routing backlog for C1.

## Next gates

Before routing:

1. freeze exact 4.26-inch panel suffix and FPC drawing;
2. freeze front-light / touch configuration;
3. select the actual battery around the 64 × 60 envelope and validate thickness, swelling, NTC and harness;
4. validate enclosure Z-stack and connector openings;
5. manually refine functional placement for power loops, display HV, RF/coax, SDMMC and USB before copper routing.

routing142 remains the old-form-factor routing authority.
