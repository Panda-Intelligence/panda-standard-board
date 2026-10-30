# Current Continuation: E0.2 r26 (v0.1.1) — Single Unified 4-Layer PCB Engineering Checkpoint (2026-10-30)

Read [E02-R25-SINGLE-UNIFIED-PCB-20261029.md](E02-R25-SINGLE-UNIFIED-PCB-20261029.md), [MAINLAND-COMPONENT-BOM-AUDIT-20261029.md](MAINLAND-COMPONENT-BOM-AUDIT-20261029.md), and [E02-R25-ROUTING-HANDOFF-20261026.md](E02-R25-ROUTING-HANDOFF-20261026.md).
Canonical dated engineering checkpoint:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261029-r25/engineering-candidate`.

**Single Unified 4-Layer PCB (`Single.kicad_pcb`): 0 opens; DRC errors/warnings/parity/ERC are all ZERO (`manufacturing_release = false` until supplier CAM/supply/stack confirmation).**
- **Zero Mechanical Interference with Full-Size Rectangular Battery Assembly Study**: Upper-left PCB step narrowed from $X = 30.0\text{ mm}$ to **$X = 38.0\text{ mm}$** ($Y = 32.0..83.5\text{ mm}$), providing **$0.0\text{ mm}^2$ XY overlap and $0.0\text{ mm}$ Z overlap** across the full-size **Model 323576** battery assembly study (`BATTERY_PACK` full $35.0 \times 76.0 \times 3.2\text{ mm}$ at $X = 2.0..37.0, Y = 2.0..78.0\text{ mm}$; `BATTERY_SEAL` full $35.8 \times 74.0 \times 0.3\text{ mm}$ at $X = 1.6..37.4, Y = 3.0..77.0\text{ mm}$; `BATTERY_TABS` full $18.0 \times 1.6 \times 0.15\text{ mm}$ at $Y = 77.2..78.8\text{ mm}$; `BATTERY_PCM` full $30.0 \times 3.8 \times 1.3\text{ mm}$ at $X = 4.5..34.5, Y = 78.5..82.3\text{ mm}$; and lateral `BATTERY_WIRE_RED/NTC/BLK` each full $3.7 \times 1.5 \times 1.0\text{ mm}$ at $X = 33.8..37.5, Y = 78.5..83.2\text{ mm}$). `study_only_not_supplier_qualified = true` and `battery_fit_proven = false` remain in effect until the exact replaceable Pico battery supplier drawing is confirmed.
- **Option 1 Upper-Right Structural Support, Poron Cushion, `1511` Speaker & 2.4 GHz FPC Antenna Bay (`upper_right_support_bay`)**: Keeping `Single.kicad_pcb` strictly at $71.0 \times 99.0\text{ mm}$ ($\le 10 \times 10\text{ cm}$ JLCPCB 4L ENIG coupon), the upper-right $35.0 \times 30.0\text{ mm}$ cavity ($X = 38.0..73.0, Y = 2.0..32.0\text{ mm}$) houses a rear-shell cross-rib honeycomb support grid + $Y = 31.2\text{ mm}$ anti-cantilever ledge (`UPPER_RIGHT_RIB_GRID`, $X = 38.5..72.5, Y = 2.5..31.2, Z = 0.55..3.65\text{ mm}$), a $0.30\text{ mm}$ Poron/EVA screen support pad (`UPPER_RIGHT_PORON_PAD`, $X = 39.0..72.0, Y = 3.0..31.0, Z = 3.65..3.95\text{ mm}$, coplanar with the $Z = 3.95\text{ mm}$ battery top surface), a standard $15.0 \times 11.0 \times 2.90\text{ mm}$ sealed micro-speaker box (`SPEAKER_BOX_1511`, $X = 55.5..70.5, Y = 17.5..28.5, Z = 0.75..3.65\text{ mm}$, wired to `J502` `SPK_P/N`), and a $24.0 \times 7.0 \times 0.20\text{ mm}$ 2.4 GHz Wi-Fi/BLE FPC antenna (`FPC_ANTENNA_2G4`, $X = 41.0..65.0, Y = 4.5..11.5, Z = 3.65..3.85\text{ mm}$, wired to `J507` `RF_ANT`) with **$0.0\text{ mm}^2$ XY overlap** against both `Single.kicad_pcb` ($Y \ge 32.0\text{ mm}$) and the `323576` battery assembly ($X \le 37.5\text{ mm}$).
- **Via-in-Pad & Thermal Via Process Accounting**: `C804.2` ground return via moved outside the pad to an external dog-bone location at **`(17.40, 104.80)`** ($0.45/0.20\text{ mm}$ via connected by a $0.30\text{ mm}$ `F.Cu` trace to `C804.2` at `(18.20, 105.00)`), eliminating `C804.2` via-in-pad; `U501.57`'s 9 thermal vias ($0.50/0.25\text{ mm}$) lie inside the exposed-pad solder-mask opening and stencil apertures (`REQUIRED-VIA-IN-PAD.csv`), so `single_board.json` retains `process = "FILLED_AND_COPPER_CAPPED_OR_SUPPLIER_APPROVED_EQUIVALENT"` and `supplier_process_accepted = false` until factory CAM acceptance.
- **100% Chinese Mainland (PRC) Component Provenance & Consignment Manifest**: Verified via `verify_mainland_bom_compliance.py` (`215/215` populated BOM components + `5/5` DNP passives on `Single`, `177/177` + `5/5` on `Core`, `42/42` on `Display`; `0` foreign manufacturers; `0` missing `Manufacturer` or `MPN` fields). Bottom Type-C USB receptacle (`J201` / **`MUP U22401-17`**) positioned at bottom center. `PENDING-SUPPLY.csv` (21 consignment/registration SMT parts) and `REQUIRED-POST-SMT.csv` (`BT301` post-SMT assembly) are exported alongside `BOM_JLCPCB_Single.csv` and `CPL_JLCPCB_Single.csv`.
- **Single-Board Checkpoint, SHA-256-Bound R25 $\rightarrow$ R26 Replay & Pre-Release Gates**: Verified end-to-end via `build_pico47_single.py`, `single_board.json`, and `r25_router/apply_single_r26_x38_eco.py` (which enforces baseline/target SHA-256 and UUID completeness, replays all 51 footprint moves, 27 boundary nets, the $X = 38.0\text{ mm}$ step outline, and the `C804.2` dog-bone via from R25 to R26, and verifies native DRC). Dedicated solid `In1.Cu` GND plane with strictly 0 non-GND signal tracks; all 173 GND pads connected. `manufacturing_release` remains `false` until the 21 pending SMT parts, `BT301` post-SMT assembly, `U501.57` via-in-pad CAM confirmation, and exact Pico battery/screen supplier drawings are confirmed.

---

# Historical continuation: E0.2 r7 — SPV and coordinated panel-control fanout

Read [E02-R7-SPV-CLOSURE-20261014.md](E02-R7-SPV-CLOSURE-20261014.md).
Dated checkpoint:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261014-r7/engineering-candidate`.
The requested `panda47-e0-20261012/engineering-candidate` is its verified copy;
previous r6 is preserved in the sibling pre-r7 archive.

**Core 32 opens; Display 9 opens; DRC errors/warnings/parity/ERC are zero.**
SPV R730.2 -> J601.40 is connected. CKV, XLE and XSTL are independently verified
connected and shorter than before. All 237 ground pads remain reference-connected.
All 9,429 non-control track/via items are unchanged. **41 native unconnected items
remain. NOT FOR FABRICATION OR POWER.** Digital timing, analog/current/return and
physical product qualification have not been granted.

Fresh source replay and independent capture reproduce all four exact control
states, counts and original pad groups. Use `build_pico47.py --routing-checkpoint`
and `capture_pico47_checkpoint.py --require-complete-ground`. The standalone
inspector generates netlists in its candidate directory: use fresh copies for
such inspection and do not mutate published manifests.

Native CAD/reports/manifests remain external or ignored. The old sections below
are historical background, not the current route or manufacturing approval.

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
