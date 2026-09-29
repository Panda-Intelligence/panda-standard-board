# Thin18 Compact — C0/C1 Architecture Decision

Date: 2026-09-29

## Baseline facts

The routing142 board is 70 × 128.1 mm. Its 202 footprints are strongly bimodal in Y:

- 112 footprints below y=30 mm;
- only 5 footprints between y=30 and 100 mm, including two mounting holes;
- 85 footprints above y=100 mm.

The sum of footprint bounding-box areas is about 2039 mm², versus about 8967 mm² of the old rectangular board. The long middle area is therefore primarily mechanical/product space rather than required electronics area.

The existing display interface is already a raw-panel architecture: SSD1677 display power/drive plus J802 FH12-24S-0.5SH(55), 24 pins at 0.5-mm pitch. It is not a Waveshare carrier-board dependency.

The external display candidate family under review is Good Display 4.26-inch / 800×480 / SSD1677. Exact production suffix, FPC pinout, front-light and touch stack remain a freeze gate.

## C0 proof: 70 × 64 mm fold

C0 is generated deterministically from routing142 by:

1. deleting all legacy tracks, vias and zones;
2. keeping the lower placement cluster;
3. moving the y>=100 mm cluster by -64 mm;
4. preserving the USB4500 mid-mount board-edge cutout;
5. relocating four mounting holes to free locations;
6. changing the main outline to 70 × 64 mm.

Results:

- 202 PCB footprints preserved;
- 203 schematic component refs preserved;
- 601 pin/net tuples identical;
- ERC = 0;
- schematic parity = 0;
- DRC rule violations = 0;
- 449 unconnected items are expected because the candidate is intentionally unrouted;
- new bounding-box overlap pairs introduced by the fold = 0.

This proves that **electronics placement area is not the blocker for a <100 × 100 mm PCB**.

C0 is not for fabrication and must not inherit routing142 routing qualification.

## Why C0 is not automatically the product layout

A 70 × 64 full-component board makes the battery stack difficult. If the battery is simply placed behind populated PCB regions, component Z-height and battery swelling can make the product thicker even though it becomes shorter.

Therefore C0 is a proof of area feasibility, not the preferred mechanical architecture.

## C1 target

Use the coupon boundary to gain horizontal room rather than minimizing PCB area at all costs:

- target PCB: **96 × 68 mm**
- hard maximum: <100 × 100 mm
- board: 4-layer / 0.8 mm / ENIG; green solder mask for the target JLC coupon
- panel nominal reference: about 105.33 × 62.37 mm
- product length target: governed by panel + enclosure tolerance, approximately 108–112 mm rather than 104 mm
- preserve the full electrical feature set

C1 should create a central low-Z / component-free battery region on the rear side where possible, while moving high components, connectors and power magnetics toward perimeter zones. This deliberately trades some PCB area for lower stack height and easier routing.

### C1 placement zones

- USB-C: external bottom edge
- microSD: external side edge with card-access sweep
- side switches: external side edge
- display FPC J802: panel-facing edge/region, final orientation tied to exact panel drawing
- ESP32-S3-WROOM-1U: peripheral zone with antenna-coax exit access
- charger / buck-boost / battery gauge: battery/USB side
- EPD HV power: close to J802 with controlled switching-current loop
- audio + speaker connector: perimeter
- RTC + supercap: low-noise region
- central rear: battery low-Z keepout candidate, not an approved cavity yet

## Gates before C1 routing

1. freeze exact Good Display panel suffix and original mechanical drawing;
2. pin-for-pin compare its FPC with the current EPD0426A02 contract;
3. freeze front-light and touch choice;
4. freeze battery dimensions, swelling allowance and NTC/harness;
5. build enclosure Z-stack with real component maximum heights;
6. freeze connector opening directions and service access;
7. produce C1 placement with zero new courtyard/physical overlap;
8. then route from scratch and re-run native DRC/parity/ERC, SI-sensitive review, fabrication DFM and physical EVT.

routing142 remains preserved as the old-form-factor electrical/routing reference.
