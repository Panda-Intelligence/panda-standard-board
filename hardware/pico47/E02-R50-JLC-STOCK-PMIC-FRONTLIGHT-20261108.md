# E0.2 R50 — JLC stock BOM, TPS651851 PMIC and AW99703 front light (2026-11-08)

User request 2026-11-08: every SMT/BOM line must be orderable from current JLC assembly stock, parts as thin as practical, then re-order the prototype. Decisions taken by the user on 2026-11-08:

- U810 (SY7636ARMC, 0 stock at JLC and LCSC): redesign with an in-stock EPD PMIC, choosing the best value after looking at comparable e-readers.
- U905 (SGM37601, 0 stock): switch to an in-stock driver.
- U902 (SGM62125AXG/TR, not stocked): first kept for consignment, then (same day, after a survey of every JLC-stocked buck-boost) replaced by Richtek RT6160AWSC on the same land.
- R801 / R803: 0.1 % thin-film 0402 parts are not stocked; 1 % is accepted.

Stock figures below were read from the JLC parts API on 2026-11-08 and will change.

## 1. EPD PMIC: SY7636ARMC → TI TPS651851RSLR (C702311)

| Product (same 4.7" class or panel family) | PMIC |
|---|---|
| Reference device (E0470A01) | SY7636A |
| Reference device C (4.7", 297 ppi) | TPS65185 (EPDiy) |
| EPDiy v7 | TPS651851RSLR |
| LilyGo T5 E-Paper S3 Pro | TPS65185 |
| Inkplate 6 / 6PLUS | TPS65186 |

Only two EPD PMICs were in JLC stock: TPS651851RSLR (188 pcs, $2.45 @10) and Fitipower FP9931WD (101 pcs, $2.03 @10). TPS651851 was chosen: mature open drivers (EPDiy, Inkplate), full VPOS headroom, and — decisive for the schedule — it fits the existing U810 land. Both are 6 × 6 mm 48-pin QFN at 0.4 mm pitch with the same pin numbering; TI's leads (0.18–0.30 × 0.4 mm) sit inside the 0.8 × 0.2 mm lands and the 4.1 mm thermal pad inside the 4.4 mm land. No mainland EPD PMIC was in stock, so U810 is the one user-approved non-mainland part (`USER_APPROVED_NON_MAINLAND` in `verify_mainland_bom_compliance.py`, exact reference + MPN).

Pin changes on the same land:

| Pin | SY7636A use | TPS651851 | R50 connection |
|---|---|---|---|
| 5 | NC | WAKEUP | new net `P47_WAKEUP` from U811 P04 (pin 8) |
| 6 | NC | DGND | GND via next to the pin |
| 16 | NC | VCOM_PWR | VN (stub into the thermal pad) |
| 22 | NC | PBKG | VN (stub into the thermal pad) |
| 27 | NC | VEE_IN | VN (stub into the thermal pad) |
| 37 | NC | VDDH_IN | VB (`P47_VP`), straight up to D801.1 |
| 43 | NC | VPOS_IN | VB, bridged to pin 42 |
| 49 (EP) | isolated | thermal pad, tied to PBKG | VN — never GND |
| 4 | VN | VNEG_IN | VN through the thermal pad; the old 6 mm B.Cu run under the package is removed |

Value changes follow the TI typical application: VDDH_D / VEE_D caps C807 / C810 1 µF → 100 nF; flying caps C808 / C811 47 nF → 10 nF; VREF cap C815 100 nF → 4.7 µF (0402, still within the 0.55 mm backside budget); L801 4.7 µH → 2.2 µH (DCDC1). TPS651851 regulates VEE_FB at −0.994 V against GND, so R804 moves from VREF to GND and becomes 39.2 k: VEE = −0.994 × (1 + 750/39.2) = −20.0 V. VDDH keeps 442 k / 21 k (0.998 × 22.05 = 22.0 V). The TS input wants NTC ∥ 43 k to AGND: R806 36 k → 43 k, R805 (the SY7636 VREF pull-up) is not fitted. VPOS / VNEG / VCOM come from I2C registers (address 0x68). Firmware must drive WAKEUP, PWRUP (`P47_HV_EN`) and VCOM_CTRL (`P47_VCOM_EN`) in TI's order and program VCOM for the panel.

## 2. Front light: SGM37601 → AWINIC AW99703CSR (C5162547)

No I2C dual-bank LED driver in a leaded package was in stock. AW99703CSR (mainland, 40 pcs) is ball-for-ball compatible with TI LM3697YFQR (C2861742, 344 pcs), so either can be fitted on the same land. WLCSP-12, 1.64 × 1.24 × 0.638 mm max, 0.4 mm pitch, placed at the old U905 centre (7.5, 124.7), rotated 90°. HVLED1 = cool (`FL_C_N`), HVLED2 = warm (`FL_W_N`), HVLED3 unused; I2C 0x36 (same as before). L905, D905, C923, R920 and C921 are reused; C922 (old VDC) is not fitted.

The inner ball B2 (SCL) has no surface escape at 0.4 mm pitch, so it carries a 0.25 / 0.15 mm via-in-pad. A footprint-scoped DRC rule allows exactly that via (`insideCourtyard('U905')`, net I2C_SCL); the board-wide 0.4 mm via rule is unchanged. It must be resin filled and copper capped like the other via-in-pad holes. C2 (AGND) joins C3 (PGND) between the balls; C3 has its own GND via.

## 3. Like-for-like stock substitutions

See `r25_router/single_r50_jlc_stock_delta.json` (same land, nets and placement):

| Refs | Was (stock) | Now | Note |
|---|---|---|---|
| 16 × 10 k (R510 …) | FH RC-02K1002FT C140215 (0) | FOJAN FRC0402F1002TS C2906861 | same rating |
| C303, C521, C527 | FH 0402B105K100NT C1526 (discontinued) | FOJAN FCC0402B105K100AT C54938484 | 1 µF 10 V X7R |
| C206, C801, C803, C816 | FH 0805B106K100NT C90544 (0) | CCTC TCC0805X7R106K100FT C380346 | 10 µF 10 V X7R |
| D202 | SGM05HU1ALXUGY2G C55274065 (0) | LRC LESD8D5.0T5G C172414 | SOD-882, VRWM 5.0 V |
| U906 | SGM809B-TXN3LG 3.08 V (0) | SGM809B-SXN3LG 2.93 V C699617 | status monitor only |
| U907 | XB7608A C669688 (0) | XB7608AJ C2681921 | identical thresholds |
| U402–U405 | SGM2578SDYG/TR (not at JLC) | SGM2578YG/TR C403706 | same balls; 1 A instead of 2 A |
| J201 | MUP U22401-17 (not at JLC) | MUP U22401-23 C49325733 | same family drawing |
| L401 | MWSA0402S-R47MT (2.0 mm) | MWSA0412S-R47MT C5451683 (1.2 mm) | same land |
| L402 | MWSA0402S-1R0MT (2.0 mm) | MWSA0412S-1R0MT C2991787 (1.2 mm) | same land; Isat 3.8 A |
| L802 | MWSA0618S-4R7MT (1.8 mm) | MWSA0615S-4R7MT C19267541 (1.5 mm) | same land |
| R801–R804 | FH THC02H 0.1 % (not at JLC) | FH RC-02K 1 % | VGH / VEE ≈ ±2 % worst case |
| TH801 | FH CMKD103F3380HANT (not at JLC) | Sunlord SDNT1005X103F3380FTF C279776 | 10 k 1 %, B3380 1 % |

| U902 | SGMICRO SGM62125AXG/TR (not stocked) | Richtek RT6160AWSC C7065276 | same 15-ball land, 0.6 mm; see below |

| D201 | LRC8804FDT1G C2856698 (11 pcs) | LRC8804DT1G C2912064 | same DFN2510-10 and pin map (1/2/4/5 I/O, 3/8 GND, 6/7/9/10 NC); Cio 0.6 pF max |

### U902 survey

All 488 JLC parts tagged buck-boost were screened (163 in stock), plus a brand-by-brand search of mainland makers. No mainland part is usable: every SGMICRO buck-boost is out of stock, XDS TX4401 draws 1 mA quiescent (unsuitable for the always-on rail), JoulWatt JW3651 is a 3–21 V wide-input part, and BCT3140 is a camera-flash charge pump mis-filed as buck-boost. RT6160AWSC (Richtek, 10 655 pcs, $0.47 @10) has the same ball map as the U902 land (A1 EN, A2/A3 VIN, B1 VSEL, B2/B3 LX1, C1 AGND, C2/C3 PGND, D1 SCL, D2/D3 LX2, E1 SDA, E2/E3 VOUT), 0.4 mm pitch, 0.6 mm max height, 2 µA quiescent, 3 A, I2C 0x75 and 0.47 µH. TI TPS63810YFFR (241 pcs, $1.77) is the second drop-in. With VSEL tied high the rail starts at 3.45 V; firmware writes register 0x05 = 0x33 (V = 2.025 V + code × 25 mV) for 3.3 V after reading DEVID (0x03), because TPS63810 uses a different code. ILIM_P is 4.5–5.5 A, close to the 5.2 A rating of the thin L401 (MWSA0412S-R47MT): normal peaks stay below 2.5 A, but a hard short may saturate it; MWSA0402S-R47MT (2.0 mm) is the higher-margin fallback. U902 is the second exact user-approved non-mainland exception.

## 4. Copper

All new copper was generated with the repository router (`r25_router/router2.py`, `power_connect.py`) and stored as geometric rules in `r25_router/single_r50_pmic_frontlight_delta.json` (copper of a net inside a window, or at exact coordinates), because replayed copper UUIDs change on every rebuild.

- PMIC: 178 items removed (old VREF tree, the VN run under the package, the corner of `P47_VP_LX` and `P47_VGH_DRV`), 56 tracks and 9 vias added. `P47_VP_LX` now leaves pin 40 through a via at (16.575, 92.375), which frees pin 37 for VDDH_IN; `P47_VGH_DRV` keeps 2 vias.
- Front light: the old TQFN fan-out and the `FL_*`, I2C and `FL_HWEN` copper inside (4.4, 121.6)–(10.4, 127.4) were replaced; 66 tracks and 9 vias added, including the B2 via-in-pad.

## 5. Verification (2026-11-08)

- Full clean rebuild R26 → R48 → R49 → R50 (`build_pico47_single_r50.py`): DRC errors / warnings / unconnected / schematic parity / ERC = 0 / 0 / 0 / 0 / 0. All R48/R49 native inspections pass with the R50 contract (ground returns 185 pads, critical links remapped to the AW99703 balls, charge-pump storage with 100 nF / 10 nF values, PMIC analog shield, pose envelopes, backside heights). Contracts that only applied to SY7636A (VREF 0.1 µF filter, 7.5 k / 36 k TS network) are dropped for R50.
- A second R50 run from the same R49 replay gives byte-identical BOM / CPL / drill files and geometrically identical Gerbers (only aperture order differs).
- `v0.1.3/` checked on its own: all native checks 0. BOM audit: 225 populated (224 SMT + BT301), 7 DNP, U810 the only approved non-mainland part.
- Via-in-pad inventory: 45 (U905's two old QFN via-in-pads are gone, U905.B2 added).
- Every BOM line was re-read from the JLC API: all in stock for ≥5 boards; pending supply is empty. Lowest stock: AW99703CSR 40, MWSA0618S-2R2MT 137, U22401-23 144, TPS651851RSLR 188.

## 6. Height (front side, after R50)

| Part | Max height | Source |
|---|---|---|
| U506 GD25Q128ESIG, SOP-8 208 mil | 2.16 mm | GigaDevice datasheet |
| U302 SD3078, SOP-8 208 mil | ≈2.1 mm | package class (drawing not read) |
| L801 MWSA0618S-2R2MT | 1.8 mm | Sunlord catalog |
| U904 NS4168, ESOP-8 | ≈1.75 mm | package class |
| J201 U22401-23 (mid-mount) | 1.60 mm above board | MUP drawing |
| SW201 / SW202 TS-1186E | 1.6 mm | XKB drawing (1.5 ± 0.1) |
| L802 MWSA0615S-4R7MT | 1.5 mm | Sunlord catalog |
| L401 / L402 MWSA0412S, L905 SWPA252012 | 1.2 mm | Sunlord catalog |
| J803 / J804 / J820 X05A10 | 1.0 mm | XKB drawing |
| U810 TPS651851 / U905 AW99703 | 1.0 / 0.64 mm | TI / AWINIC |

Backside parts are unchanged (≤0.55 mm; C815 is now 4.7 µF 0402 within the same budget). The next height reductions need footprint changes and are not in R50: U506 → GD25Q128EWIGR WSON-8 (0.8 mm, C2982923, 1931 in stock), and a 2.2 µH boost inductor with a smaller land for L801.

`manufacturing_release`, `supplier_process_accepted` and the EVT qualification flags stay false. The new PMIC and front-light driver need firmware (TPS65185-family register map at 0x68, AW99703 at 0x36) and bench bring-up before the panel or front light are powered.

Cost-down swaps (U503 QMI8658B and five capacitor lines) and the unit cost estimate are in [R50 cost estimate](E02-R50-COST-ESTIMATE-20261108.md).
