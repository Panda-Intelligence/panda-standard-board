# Panda Standard 4.7 — main board v0.2.6 / E10

- **Board**: `Panda47-v026.kicad_pcb`. v0.2.5 with three lower-cost, lower-profile part changes; see the
  [E10 note](../E10-V026-COST-HEIGHT-20261117.md). The circuit is the v0.2.5 one
  ([E09 note](../E09-V024-PRE-ORDER-REVIEW-20261117.md), [v0.2.4 README](../v0.2.4/README.md)).
- **Changes from v0.2.5**:
  - C207, C208, C525: 22 µF 0805 → 0603 (the C401 part). C203: 10 µF 1206 → 0805 (the C206 part).
  - H2, H3: 1.0 mm high nuts instead of 2.0 mm.
  - No copper changed. −$0.49 per board, 75 → 73 BOM lines.
- **Native checks** (KiCad 10.0.7, in this directory): ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity.
- **Order pack** (outside Git, `.work/panda47-v0.2.6-deliverable/`): 160 placements, 73 BOM lines, U810 consigned.
- **Superseded for ordering by [v0.2.8](../v0.2.8/README.md)** (lower, recessed microSD socket, E11 / E12).
- **Status**: `manufacturing_release = false`; the open items of v0.2.5 are unchanged.

## Build path

`../v026/build_v026.sh` rebuilds this directory from `../v0.2.5/`: `make_netlist_v020.py` with
`PANDA47_VARIANT=v026`, `v026/eco_cost.py`, the silkscreen scripts with `v026/v026_silk.json`, then the schematic,
parity sync, fields, ERC and DRC.
