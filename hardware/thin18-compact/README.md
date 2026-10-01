# Thin18 Compact EVT

## Current authoritative state — Split-C1 (2026-10-01)

The current PCB authorities are core-c1-96x68-split and
display-c1-45x36-production-bom. The Core is 96 x 68 mm / four copper layers;
Display is 45 x 36 mm / two layers. Both boards are 0.8 mm thick and pass
native KiCad DRC/open/parity/ERC = 0/0/0/0.

Production packages are under production/core-c1-96x68 and
production/display-c1-45x36, with production/split-c1-release.json as the combined
hash-checked record. Every populated BOM ref has Manufacturer and exact MPN.
Catalog mappings cover 111 Core refs and 36 Display refs; six Core SMT refs,
one Display SMT ref and the manual TH301 still need supply confirmation.
Present catalog IDs do not reserve stock or confirm an assembly order.

See SPLIT-C1-CAD-PRODUCTION-CLOSURE.md for electrical closure and
SPLIT-C1-MECHANICAL-SOURCING.md for current mechanical constraints and sourcing.
The native XY screen isolates J201 shell pads for a Z-clearance check. The
battery planning rectangle overlaps the Display by 1530 mm²; the full battery
must sit outside the occupied interboard gap. Actual battery dimensions,
maximum component heights, FPC geometry and enclosure tolerances remain open.

This is an EVT fabrication-data candidate. manufacturing_release=false.
Physical electrical/thermal EVT and actual mechanical fit require assembled
hardware. C4D-20 integrated outputs, routing141 scenes and the C0/C2 notes below
are historical; they do not override Split-C1.


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
