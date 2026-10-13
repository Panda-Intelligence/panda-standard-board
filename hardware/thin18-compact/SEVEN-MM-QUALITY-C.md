# Quality routing C - 2026-10-10

## Verified and reproducible

`build_seven_mm_quality.py --output <fresh ignored/external directory>` first
rebuilds the committed electrical donor, then replays the reviewed quality source.
Core and Display both pass fresh refilled native DRC/open/parity/ERC 0/0/0/0.
The actual source is `seven_mm_quality_source.json`, revision C. It includes the
prior revision-B GPIO/SI changes and the updated matching firmware pin header;
`verify_seven_mm_quality_gpio.py` independently checks the pin contract.
No generated native trial, report, Gerber, routing grid or media belongs in Git.

The board-edge rule is tightened from0.15 to0.20mm, with no other PCB/netclass/ERC
rule relaxation. `seven_mm_process_rules.py` rejects additional changes/exclusions.
BAT_CELL_N main return is rerouted with0.80mm copper, preserving the short0.30mm
common-pin bridge and the separate protection-sense branch.141 existing3V3_AON
segments (95.465mm total) were widened within existing native clearances.
All changes pass native DRC after zone refill, including a fresh source rebuild.

USB complete board planar mismatch is0.011047mm with2 signal vias on each line.
SD paths are all F.Cu/no-via, within CLK +/-1.27mm. These are connected-path
measurements, not certified90-ohm impedance, via/package delay or physical tests.
The RF bulk-capacitor path still needs a tighter loop review; a failed relocation
trial was NOT adopted. Do not equate connected copper with a qualified RF design.

Ten previously unmapped physical references now have exact catalog identities:
U501 C2913194; C520/C522/C523/C524/C526 C56392; C521/C527 C1526;
C528/C529 C1549. Manufacturer,MPN and package were checked on JLC official pages.
The native PCB, schematic and local libraries agree. No stock or receipt is claimed.
Other unmapped parts remain open; do not substitute approximate codes or omit them.

## Not an approved product or assembly order

The inherited quality floorplan is a75x116mm study: USB mouth is near Y=115.7mm.
The approved source allocation remains75x112mm, with USB opening at Y=112mm.
That4mm extension is NOT silently adopted as a product requirement; the old native
port checker correctly rejects it. Recover the bottom strip or obtain an explicit
mechanical decision before replacing the product target. The all-zero quality
candidate must not be confused with a verified112mm enclosure fit.

JLCPCB publishes +/-0.10mm thickness tolerance below1.0mm. Thus nominal0.80mm
PCB must budget0.90mm, not0.88mm. The corrected electronics section sums to6.90mm;
the battery section sums to6.85mm. These budget calculations do not establish
supplier maximum panel/cell/tabs dimensions, swelling allowance or complete fit.
JLC default inner copper is0.5oz; a resistance calculation assuming35um on every
layer is a study assumption, not guaranteed fabrication copper or thermal proof.

Remaining design/order gates include the product outline/port datum, controlled
USB/RF stackup, power-current/thermal review, remaining exact component/harness
supply, RTC reverse-charge leakage/retention, and via-in-pad/CAM/SMT acceptance.
No paid order, supplier reservation or manufacturing release is performed here.
Old product release/RFQ/render guards remain closed.

## Sources and local continuation

JLC capabilities: https://jlcpcb.com/capabilities/pcb-capabilities
ESP PCB guidance: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html
Exact catalog links are recorded in `seven_mm_quality_catalog.json`.
Current local native/check evidence is under
`.work/seven-mm-release-review-20261010-1405/candidate/` and `rebuilt-final/`.
Only reviewed source/contract/library/test files are committed; these outputs stay ignored.
