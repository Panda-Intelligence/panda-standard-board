# Panda Standard 4.7 — main board v0.2.9 / E14

- **Board**: `Panda47-v029.kicad_pcb`, 63 × 48 mm, 4 layers, 0.8 mm. See the
  [E14 note](../E14-V029-A03-PANEL-TWO-FL-DRIVERS-20261118.md).
- **Replaces v0.2.8**, whose panel connector cannot be reached by the panel tail.
- **Changes from v0.2.8**:
  - J820: X05A10H34G for the E0470A03 panel (8-bit), at (32.0, 76.6) on the centre line, mouth down.
  - D8–D15 removed; GPIO13–18 free; GPIO12 is FL_C_PWM.
  - Front light: two AW9967DNR stages (U905 warm, U906 cool) at the bottom right; SGM3732, Q901 and R601 removed.
  - 3.3 V buck re-laid 0.85 mm to the left; fuel gauge U903 moved beside the battery connector.
- **Schematic**: `Panda47-v029.kicad_sch` (index) + sheets, generated from the netlist.
- **Native checks** (KiCad 10.0.7, in this directory): ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity
  (`--severity-all`).
- **Status**: `manufacturing_release = false`. Open items in §7 of the E14 note. No order pack was made.

## Build path

`../v029/build_v029.sh` rebuilds this directory from `../v0.2.8/` (work files in `.work/v029`):

1. `make_netlist_v020.py` with `PANDA47_VARIANT=v029`; `v029/make_fp_v029.py` adds the two new footprints.
2. `v029/eco_a03.py`: placement and hand copper; `v029/prune_stubs.py`.
3. Grid router (`router_v020.py` + `apply_router_v020.py`) with `v029/spec_a03.json` (40 nets).
4. `v029/eco_gnd.py`, `fix_thermals.py`, `trim_dangling.py`, `finish_v029.py`, `v023/widen_v023.py`, `silk_v020.py`,
   `info_silk_v02x.py` with `v029/v029_silk.json`.
5. `build_v020_sch.py`, `sync_board_sch_v020.py`, `set_fields_v020.py`, then ERC and DRC.
