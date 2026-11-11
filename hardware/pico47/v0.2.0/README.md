# Panda Standard 4.7 — Pico-class board (`v0.2.0` / `E03`)

- **Board**: `Panda47-v020.kicad_pcb`, 4 layers, 0.8 mm, L-shaped outline (63 × 32.8 mm strip below the cell + 11.5 × 78 mm side tab, 63 × 111 mm bounding box, ≈ 2960 mm²) for a 117.5 × 66.2 × 7.3 mm device. See [E03 note](../E03-V020-PICO-CLASS-REDESIGN-20261110.md).
- **Schematic**: `Panda47-v020.kicad_sch` (index) + 9 sheets `Panda47-v020-*.kicad_sch`, drawn by `readable_schematic.py`; netlist identical to the board.
- **Libraries**: `Panda47v2.pretty` (every footprint used, project-local) and `Panda7.kicad_sym`.
- **Native checks** (KiCad 10.0.7, this directory alone): ERC 0; DRC 0 violations / 0 unconnected / 0 schematic parity.
- **Status**: `manufacturing_release = false`. Before ordering: panel / touch / front-light FPC connector poses against the supplier drawing, SY7636ARMC (U810) consigned, resin-filled capped via-in-pad for 17 exposed-pad vias. JLC DFM fixes of 2026-11-11 are in the E03 note §10.

## Build path

The board is the result of an automated flow plus recorded local fixes, not a single replay:

1. `v020/dump_pcb_v020.py` on v0.1.3 and v0.1.2 → `r50.json`, `r49.json`; `v020/make_netlist_v020.py` rewrites the R50 netlist to the Read Pico architecture; `v020/bomcheck_v020.py` checks JLC stock and price.
2. `v020/place_v020.py` with `v020/layout/anchors_v020f.json` → `placement_v020f.json` (hand anchors, pin targets for switching loops and decoupling).
3. `v020/run_v020.sh` — board build, GND via stitching, Freerouting 2.5.0 (40 passes), SES import, zones, DRC.
4. `v020/finish_v020.py`, `touchup_v020.py`, `apply_router_v020.py` with the three small fix files in `v020/layout/` (REGN detour next to L402, one D1 stub, solid U302.4 pad), `silk_v020.py`.
   Then `v020/dfm_fix_v020.py` (JLC DFM fixes: U907 CPC5 land, switch locating holes, J820 hold-down pads, pin-1 dots), zone refill.
5. `v020/build_v020_sch.py`, `v020/sync_board_sch_v020.py`, `v020/set_fields_v020.py` — schematic and parity.
6. `v020/export_orderpack_v020.py` — Gerber / drill zip, BOM, CPL, via-in-pad and consign lists (written outside Git).

Treat this KiCad project as the source of truth for later edits.
