# Panda Standard 4.7 — main board v0.2.5 / E09

- **Board**: `Panda47-v025.kicad_pcb`. The v0.2.4 board with the three fixes of the pre-order review; see the
  [E09 note](../E09-V024-PRE-ORDER-REVIEW-20261117.md). For everything else the
  [v0.2.4 README](../v0.2.4/README.md) and the [E07 note](../E07-V024-HAND-LAYOUT-SPEAKER-NOTCH-20261113.md) apply.
- **Changes from v0.2.4**:
  - U903 pin 9 (fuel gauge TS) is disconnected from BQ_TS. The gauge profile must use host-reported temperature.
  - C305, 22 pF 0402 (same part as C404), from RTC_OSCI to ground at (46.4, 71.3).
  - R516, 100 k 0402 (same part as R604), from AUDIO_EN to ground at (2.3, 90.1).
  - Copper: 9 BQ_TS items removed, 17 added (RTC_OSCI 8, AUDIO_EN 5, GND 4). No existing part moved, no other pad
    net changed. Silkscreen text and title block updated.
- **Native checks** (KiCad 10.0.7, in this directory): ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity
  (`--severity-all`).
- **Order pack** (outside Git, `.work/panda47-v0.2.5-deliverable/`): 160 placements, 75 BOM lines, 444 vias, 22
  via-in-pad, U810 consigned. Against the v0.2.4 pack only the C305 and R516 lines are new.
- **Superseded for ordering by [v0.2.6](../v0.2.6/README.md)** (same circuit, cheaper and lower parts, E10).
- **Status**: `manufacturing_release = false`. Still open: panel / touch / front-light connector pin maps and poses
  against the panel-module drawing, SY7636A not checked against a datasheet, and the E07 §6 items.

## Build path

`../v025/build_v025.sh` rebuilds this directory from `../v0.2.4/` (work files in `.work/v025`):
`make_netlist_v020.py` with `PANDA47_VARIANT=v025`, `v025/eco_review.py`, `v025/prune_stubs.py`, the grid router with
`v025/spec_review.json`, `v025/finish_v025.py`, `silk_v020.py`, `info_silk_v02x.py` with `v025/v025_silk.json`, then
the schematic, parity sync, fields, ERC and DRC. The order pack is `v020/export_orderpack_v020.py`.
