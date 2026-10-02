# Thin7 — two-board 7.0 mm mechanical redesign

User requirement, 2026-10-02: the device must be about 7 mm thick. The earlier
112 × 75 × 21 mm side-pack study is rejected as the product architecture.
This change establishes a concrete mechanical partition and two empty KiCad
outline templates. **It does not claim that the electronic redesign is routed.**

## Fixed design intent

- Case target: **112 × 75 × 7.0 mm**, uniform body thickness; no hidden battery bump.
- Exactly two PCBs: **Core 99 × 30 mm bounding box, L-shaped, 4 layers, 0.8 mm**;
  **Display 45 × 36 mm, 2 layers, 0.8 mm**. The Core area budget is 2055 mm².
- Core, Display and main battery occupy separate XY regions in the same layer.
  A flexible 60-contact link replaces the stacked J601/J1 connection.
- GDEQ0426T82-FT01C retains its 105.33 × 62.37 mm body and 2.2 mm thickness budget.
  Its touch face sits 0.2 mm below the outer front plane. The front frame covers
  the inactive border; an extra full-area cover is not included in this stack.
- Preserve 1100 mAh nominal capacity target / 900 mAh minimum target, 16 MB flash,
  8 MB PSRAM, touch, front light, audio, IMU, microSD, mainland component policy,
  and isolated **RTC retention ≥24 h**. No main reading runtime is invented.

## Critical battery section

| Term | Design budget, mm |
|---|---:|
| Rear wall | 0.55 |
| Electrical insulation | 0.15 |
| Complete protected pack maximum | 3.10 |
| Swelling allowance | 0.50 |
| Panel clearance and residual reserve | 0.15 |
| Panel bond | 0.15 |
| Screen, front light and touch thickness budget | 2.20 |
| Screen recess | 0.20 |
| **Total** | **7.00** |

These are requirements for selection, not signed supplier maxima. The pack
must fit **62 × 51 × 3.1 mm including PCM, wrap, tabs and local lead exit**.
No fastener, rib or cable may consume the cell's swelling space. Housing,
panel and pack tolerances, PCB warp, adhesive compression and supplier-approved
swelling still require a full maximum-material stack. The 0.15 mm clearance
is not proof that the complete tolerance stack fits.

The manufacturer lists DNK LP305060 as a 1000 mAh, 3 × 50 × 62 mm protected
pack, 1 A continuous / 2 A peak. It is an **unselected screening candidate**:
its nominal dimensions support investigating this battery region, but its
capacity and current ratings do not meet the existing targets and its maximum
assembled dimensions are absent. Do not silently substitute it or assume a
1100 mAh version of the same size exists.

## Native CAD blockers and necessary electronic work

| Native item | Required change |
|---|---|
| C301 SE-5R5-D105VYH3C | 6.5 mm body + 0.2 mm mounting allowance cannot fit. Qualify a thin RTC backup assembly ≤2.4 mm mounted and its charge/isolation circuit. |
| U501 WROOM-1U-N16R8 | Replace the 3.2 mm module with bare ESP32-S3R8, domestic 16 MB flash, 40 MHz crystal, RF matching and antenna. Recheck package maximum, all GPIOs, RF/SI and firmware. PICO N8 is only 8 MB flash and is not an equivalent replacement. |
| J301 / J302 / J502 | Replace 5.5 / 3.2 / 3.2 mm wire housings with qualified low-profile mainland parts or supplier-terminated solder harnesses with retention. |
| J601 / J1 | Replace 1.5 mm stacked interconnect with qualified flexible connection; preserve every native contact, current capacity, grounds and signal integrity. |
| J201 / J501 | USB must use the bottom bezel outside the panel projection or a qualified mid-mount package. Verify USB plug and card access, travel and case openings. |
| Core / Display | New placement and routing are required. The empty outlines are not populated boards; native DRC=0 does not validate their fit. |

The RTC remains SD3078 for this mechanical study. Do not connect a primary coin
cell to its existing enabled charger. A primary-cell route requires hardware
charge blocking and firmware charge disable; a rechargeable route requires an
approved voltage/current window. Neither alternative is selected here.

## Source and verification

`thin7-mechanical-contract.json` is the single geometry/budget source. Run:

```sh
python3 hardware/thin18-compact/thin7/audit_thin7.py
python3 hardware/thin18-compact/thin7/audit_thin7.py --require-native-ready
```

The first checks dimensional closure, PCB count/coupon size and disjoint XY
partitions, and reports native blockers. The second must fail for current CAD.
`release_split_c1.py` runs this gate before producing new factory packages.
The old 21 mm study is retained only as historical evidence, marked superseded.
No supply acceptance, physical EVT or manufacturing release is claimed.

Build empty native templates with KiCad's Python environment using
`build_thin7_outline_templates.py`; rebuild visualization with Blender using
`build_thin7_scene.py -- stills` or `-- animation`. All object scales are 1;
the assembled case coordinates span exactly 7 mm. Rendered boards are labeled
partition templates, with no invented routed copper or populated BOM.

Primary references checked 2026-10-02:

- X4 Pro official FAQ: https://www.xteink.com/blogs/product/x4-pro-faq-specs-support
  (111 × 69 × 5.95 mm and 1100 mAh reference; user target is about 7 mm).
- Espressif ESP32-S3 datasheet: https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf
  (bare QFN56 architecture; package/RF implementation remains to qualify).
- DNK LP305060: https://www.dnkpower.com/products/305060-3-7v-1000mah-lithium-polymer-battery/
  (nominal pack dimensions and capacity/current screening only).
- Existing exact native component drawing links remain in
  `../split-c1-mechanical-inputs.json`; current supply gaps remain open.
