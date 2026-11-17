# Panda Standard 4.7 — main board v0.2.7 / E11

- **Board**: `Panda47-v027.kicad_pcb`. v0.2.6 with a lower microSD socket and a smaller front-light output capacitor;
  see the [E11 note](../E11-V027-LOW-SD-SOCKET-20261117.md). Circuit and open items as in
  [v0.2.5](../v0.2.5/README.md) and [v0.2.6](../v0.2.6/README.md).
- **Changes from v0.2.6**:
  - J501: Hanbo TF-019, push-push, 1.45 mm (was about 2.0 mm). SD nets laid again; no other part moved.
  - C923: 0805 instead of 1206, moved 0.2 mm left.
  - Tallest parts on the board are now about 1.5 mm (was 2.0 mm). +$0.13 per board.
- **Native checks** (KiCad 10.0.7, in this directory): ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity.
- **Order pack** (outside Git, `.work/panda47-v0.2.7-deliverable/`): 160 placements, 73 BOM lines, U810 consigned.
- **Superseded by [v0.2.8](../v0.2.8/README.md)**: the user did not accept a card standing 1.3 mm out of the body.
- **Status**: `manufacturing_release = false`. New: the TF-019 land pattern and pin order come from the maker drawing
  and need a first-article check with a card; a latched card still stands about 1.3 mm out of the body.

## Build path

`../v027/build_v027.sh` rebuilds this directory from `../v0.2.6/`: `make_netlist_v020.py` with
`PANDA47_VARIANT=v027`, `v027/eco_sd.py`, the grid router with `v027/spec_sd.json`, `v027/prune_stubs.py`,
`v023/widen_v023.py` for 3V3_SD only, the silkscreen scripts with `v027/v027_silk.json`, then the schematic, parity
sync, fields, ERC and DRC.
