# C4D-20 CAD / Production Closure

Date: 2026-10-01

## Closed
- Board target: 96 x 68 mm, 4 layers.
- Routing: complete; open=0.
- Native KiCad: DRC=0, schematic parity=0, ERC=0.
- C4D-19 -> C4D-20 semantic equivalence: 2518 tracks/vias, 189 footprint poses,
  and 642 pad geometry/net records are identical.
- Production BOM: 113 grouped rows / 153 designators; Manufacturer and exact MPN
  are populated for every row, including external NTC TH301=103JT-025-600AY.
- Production CPL: 152 placed designators (143 top / 9 bottom).
- Gerber + PTH/NPTH drill outputs generated and zipped.
- JLCPCB BOM/CPL headers generated from the generic manufacturing files.

## JLCPCB sourcing state
- 113 designators have an LCSC/JLC library ID already populated.
- 39 placed designators have exact MPN but no LCSC ID; these require JLC manual
  mapping or consigned/customer-supplied parts.
- 1 BOM designator is manual/off-board: TH301 external battery NTC.
- No CPL designator is missing from the BOM.

## Still open — physical EVT only
Q04 USB-C/USB2; Q05 charge/NTC/ship/deep-sleep; Q06 14.5 mA front-light
accuracy; Q07 18 V OVP/open-string; Q08 COUT DC-bias; Q09 Schottky hot leakage;
Q10 inductor thermal/EMI/acoustic; Q11 touch/front-light FPC fit; Q12 RF,
thermal and complete EVT soak.

manufacturing_release=false is intentional until all Q04-Q12 gates are
MEASURED_PASS with sample identity, calibrated instruments, raw evidence and
independent release approval.
