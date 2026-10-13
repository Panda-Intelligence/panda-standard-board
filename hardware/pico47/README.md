# Current continuation: E0.2 — 2026-10-13

Read [E02-20261013-HANDOFF.md](E02-20261013-HANDOFF.md) first. The dated accepted
checkpoint is `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261013/engineering-candidate`.
Latest fresh native checks: Core46 opens/1 warning, Display21 opens/3 warnings;
errors, parity and ERC0. **67 native unconnected items remain; NOT FOR FABRICATION
OR POWER.** The final R813.2 -> U810.EN21 connection is still open.

Rebuild with `build_pico47.py --routing-checkpoint <checkpoint>` and use
`capture_pico47_checkpoint.py` for non-regressing native evidence. Source/build,
physical pad connectivity and exact library/rule bindings are independently
checked; fewer airwires alone do not qualify the board. The E0.1 and original
E0.2 sections below are historical background, not the current route.

# Panda47 E0 — parallel-display redesign checkpoint

Date: 2026-10-12. Status: **INCOMPLETE ENGINEERING DESIGN — DO NOT ORDER OR POWER**.

This is the user-authorized successor to Product D, not a relabelled SPI board.
The confirmed target is the Read Pico E0470A01 family: 4.7 inch, 1216 × 684,
approximately 297 PPI, raw 16-bit parallel display, plus the same actual replaceable
2050 mAh LCO battery pack. The old 4.26-inch SPI module and 1100 mAh cell are not
accepted substitutes. Matching mAh alone does not identify the Pico battery.

## Non-negotiable requirements and current limitations

Retain two physical PCBs, mainland component identities, 16 MB Flash, 8 MB PSRAM,
touch, frontlight, audio, IMU, microSD, RTC backup and the direct GPIO2 inhibit.
USB-C remains bottom-centre; microSD remains near the lower right corner.
Whole-device maximum thickness remains **7 mm including positive tolerances**.

The 75 × 132 × 6.8 mm coordinates in `design.json` are a temporary electrical
layout study, NOT a frozen enclosure or proof of battery/frontlight fit. Both
engineering PCB candidates currently use four copper layers and 0.8 mm nominal
board thickness. In1 is reserved for the GND reference, not signal routing.

The public Pico specification does not establish the battery manufacturer/MPN,
complete maximum dimensions, protection topology, connector polarity, NTC or
charge termination voltage. These remain null in the source contract. Do not
invent them or treat the legacy two-pad bench landing as the Pico connector.
Charging is not authorized. The exact full panel suffix, touch/frontlight stack,
BORDER behaviour, folded FPC/contact side and per-panel VCOM remain unqualified.

## Implemented electrical changes

The new native Core and Display schematics, PCB pad nets and local libraries
contain the complete 40-pin E0470A01 family map and a new 40P + 20P board link.
This link is **not pin-compatible with Product D**. All 33 available MCU GPIO are
allocated; pins reserved for octal PSRAM remain unused externally. The bare-QFN
mapping is independently checked: physical pin 36 is GPIO48 and pin 37 is GPIO47.
USB19/20, GPIO2 inhibit, the existing I2C bus and independent I2S audio are retained.

Two SGM330A-YTS/TR switches share eight GPIO between the parallel display and
four-bit SD/UART. SD/UART transfers and display scans are mutually exclusive.
Firmware must stop the current peripheral, disable both switches, change selection,
configure the new peripheral, then reconnect; reset selects SD/UART. The mux's
analogue bandwidth is not evidence of qualified 3.3 V digital timing. Buffered
reading and audio interaction still need target firmware and bench tests.

Display power uses a SY7636ARMC engineering circuit. Its exposed pad is a negative
reference and **must not be grounded**. The 25 V reference VGH example is not the
selected panel's 22 V target. The old manufacturer PDF is not current supplier
approval; NC/EP interpretation, sequencing, VCOM and power-stage margins require
explicit qualification before energizing a panel.

GPIO2 now reaches the PMIC EN through R813 (1 kΩ), with a 100 kΩ pull-down. U811 P00
is input-only and monitors EN; it must not drive it. This removes an I2C-expander
write from the physical EN-low path. It does not claim to detect a CPU frozen with
GPIO2 held high, and the incomplete routing is not evidence of working hardware.

L801/L802 use Sunlord MWSA0618S-4R7MT / C408421, with actual larger lands rather
than reusing the old 3 mm geometry. The manufacturer drawing gives 1.8 mm maximum
height and 7.3 × 6.8 mm maximum body. The source retains the manufacturer's
Max./Typ. current headings (Isat 4/5 A; heat-rating 3.5/4 A); these are not relabelled
as guaranteed minima. Hot start-up/fault margins and the rectifier remain open.

Selected GND pads now have explicit solid plane connections and real GND stitching
vias. Clearances, hole limits, minimum spokes, ERC severities and exclusions are
not relaxed. Display via drills are at least 0.30 mm; the chosen stitching via is
0.65/0.30 mm. Stencil/reflow heat balance remains a manufacturing qualification,
not something a successful DRC can certify.

## Source and verification tools

`build_pico47.py` builds a new candidate from a native-clean, sourcing-bound D
checkpoint. It never overwrites the donor and reports real DRC/open/parity/ERC
counts. Old disconnected copper is not relabelled onto the new signals.

`pico47_contract.py` and `test_pico47_contract.py` enforce pin allocations, required
features, exact known identities and explicitly unknown supplier properties.
`verify_pico47_native.py` independently exports fresh schematic netlists and checks
33 GPIO, 40 panel contacts, 60 interboard contacts, eight mux channels, 518 retained
Core pad functions, PMIC EP and direct-enable connectivity, actual inductor lands,
and unchanged native design rules. These are electrical-intent checks, not proof
that every trace is connected or that a sample works.

`import_pico47_route.py` imports SES **copper only**, retains native component/pad/
outline intent and reruns native checks. Router completion never grants release.
A trial with smaller router clearances was rejected after native DRC; it is not
adopted and did not change the actual project rules.

`split_pico47_junctions.py` splits existing segments at real same-net junctions.
`prune_pico47_stubs.py` removes only native-reported dead ends and validates all
originally connected pad groups after each trial. A split of a live pad group or
increase in native errors restores that trial. Connectivity snapshots use isolated
KiCad Python processes to avoid repeated-SWIG-wrapper lifetime faults. Fewer
airwires after deleting an orphan are not described as newly routed connections.
`test_pico47_connectivity.py` tests this acceptance logic independently.

## Rebuild and inspect

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
python3 hardware/pico47/test_pico47_contract.py
python3 hardware/pico47/test_pico47_connectivity.py
"$KPY" hardware/pico47/build_pico47.py \
  --donor /absolute/path/to/verified/sourced-D-candidate \
  --output /absolute/fresh/ignored-or-external/E0-candidate
"$KPY" hardware/pico47/verify_pico47_native.py \
  --candidate /absolute/path/to/E0-candidate \
  --donor /absolute/path/to/verified/sourced-D-candidate \
  --output /absolute/fresh/ignored-or-external/native-check.json
```

Use the current continuation candidate recorded below, not whichever `.work`
directory has the newest mtime. The old `build_seven_mm_product.py` remains a
reversible Product-D regression, not the requested new display design.
Generated native files, SES/DSN, trial snapshots, PDFs, logs, renders and packages
remain outside Git. The existing unrelated `packaging/` is untouched.

## Primary references

- Read Pico specification: https://dot.mindreset.tech/docs/read_0
- Official panel-family declaration: https://github.com/MindReset/read_pico_firmware/blob/6a247cc94420b85c650b32a6b2c063a360070eee/components/epdiy/src/displays.c
- E0470A01-AF-S manufacturer specification mirror (not proof of the Pico full suffix): https://raw.githubusercontent.com/exomind-team/openepd-47/main/materials/vendor/display/E0470A01-AF-S-specification.pdf
- Espressif package pins: https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf
- GPIO API: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/gpio.html
- SGM330A primary datasheet: https://www.sg-micro.com/rect/assets/7d4de883-c52b-4322-b0a1-24add89dc52c/SGM330A.pdf
- Silergy exact product: https://www.silergy.com/zh/productsview/sy7636armc
- Sunlord original series drawing, pp3/10: https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/2905/MWSA-S_Series_DS.pdf
- KiCad connectivity clusters: https://docs.kicad.org/doxygen/connectivity__data_8cpp_source.html

## Historical E0.1 candidate and native results — superseded by E02-HANDOFF

Canonical external review candidate:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e0-20261012/engineering-candidate/`.
Its `CURRENT-STATUS.json`, native reports and `INDEPENDENT-CHECK.json` bind the
actual files; it is not a manufacturing package. Working ancestry is
`.work/pico47-close-20261012/integration-e06/`. Preserve these when cleaning .work.

Final fresh refill/all-severity/all-track-error/schematic-parity DRC and ERC:

| Board | DRC errors | DRC warnings | Unconnected items | Parity | ERC |
|---|---:|---:|---:|---:|---:|
| Core | 0 | 1 | 161 | 0 | 0 |
| Display | 0 | 4 | 49 | 0 | 0 |

The warnings are remaining copper end/via connection work, not waived checks.
The display routing stage reduced its native unconnected count from104 to49.
Core dead-end cleanup retained all354 original native pad-connectivity groups;
its lower airwire count includes removed orphan islands, not new routed signals.
A native guard restored trials that would split live connections.
58 E0 contract/connectivity tests and71 legacy sourcing/routing tests passed.

Next work: complete the new GPIO/mux/FFC routes and remaining Display nets,
then validate full path timing, power loops, thermal/ripple margins and bus handover.
In parallel obtain exact Pico pack and complete panel assembly drawings before
freezing final geometry. No battery procurement or manufacturer acceptance was
created by these source changes. Manufacturing release remains false.
