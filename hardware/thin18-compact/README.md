# Thin18 Compact EVT

## Current authoritative state — C4D-20 (2026-10-01)

The current PCB authority is c4d20-96x68-production-bom, derived from the
C4D-19 routing closure without changing tracks, vias, footprint poses or pad
geometry/nets. Native KiCad checks are DRC=0 / open=0 / parity=0 / ERC=0.

Production outputs are under production/c4d20-96x68/: generic BOM/CPL,
Gerber + drill ZIP, and JLCPCB-formatted BOM/CPL. All populated BOM groups now
have Manufacturer + exact MPN. JLC/LCSC coverage is partial by design: rows
without an LCSC ID remain explicit MPN-only mapping/consigned-part items.

This is an EVT fabrication candidate, not manufacturing release. Q04-Q12
physical tests still require a real assembled sample, calibrated instruments,
raw evidence, independent review and release approval. Older C0/C2/C4 notes
below are retained as design-history records and do not override C4D-20.


Thin18 Compact is an architecture fork of the validated `thin18/routing142` baseline.

## Goal

Reduce the main PCB below the JLC 100 × 100 mm coupon boundary while making the product materially shorter, without changing the electrical feature set.

C0 target:

- PCB: **70 × 64 mm** placement-feasibility candidate
- hard coupon boundary: every PCB side < 100 mm
- layers: 4
- thickness: 0.8 mm
- finish target: ENIG
- production solder mask target: green
- display architecture: raw 4.26-inch SSD1677 panel through 24-pin / 0.5-mm FPC
- display candidate family: Good Display GDEY0426T82; front-light/touch derivatives require separate stack-up and pin/FPC qualification
- screen, battery and PCB are separate mechanical objects; the PCB no longer follows the panel length

## C0 fold strategy

The routing142 placement already has two dense functional regions:

- y < 31 mm: power, battery/gauge/RTC, audio, microSD, switches
- y > 100 mm: USB-C, ESP32, display power/FPC, protection

Only five footprints occupy the 30–100 mm middle band, two of which are mounting holes. C0 folds the upper region down by 64 mm, keeps the lower region, relocates mounting holes, reduces the board outline to 70 × 64 mm, and intentionally removes all legacy tracks/vias/zones.

This candidate is **placement-only and NOT routed**. routing142 remains the authority for the old form factor.

## Gates before routing

1. no footprint/edge impossibility after connector-specific edge allowances;
2. no unintended footprint overlap;
3. schematic population and pin/net parity unchanged;
4. ERC remains zero;
5. battery/display/enclosure Z-stack is frozen;
6. exact display FPC pinout and front-light/touch variant are frozen;
7. USB-C, microSD, side switches, display FPC and antenna cable exits are mechanically frozen.

Do not fabricate the C0 board.
