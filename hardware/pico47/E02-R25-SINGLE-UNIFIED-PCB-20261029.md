# Pico47 E0.2 r25 — Single Unified 4-Layer PCB Architecture & JLCPCB Free Coupon Qualification (2026-10-29)

## Executive Summary

Following customer feedback regarding space utilization, manufacturing simplicity, and battery standardization, the Pico47 hardware architecture has been transitioned from a dual-board split (Core + Display with 4 board-to-board connectors and 2 FFC cables) into a **Single Unified 4-Layer PCB architecture (`Single.kicad_pcb`)**.

### Key Architectural Achievements:
1. **100% Zero-Defect Native Verification**:
   - **0** DRC violations
   - **0** unconnected items (0 opens)
   - **0** schematic parity issues
   - **0** ERC violations
   - **173/173** GND pads connected to a dedicated solid `In1.Cu` ground plane (**0 non-GND signal tracks on `In1.Cu`**).
2. **Elimination of Board-to-Board Interconnects**:
   - Eliminated all 4 B2B connectors (`J1`, `J4`, `J601`, `J602`).
   - Eliminated 40-pin parallel display FFC and 20-pin power/control FFC.
   - All high-speed EPD signals (`P47_D[0..15]`, `P47_CKV`, `P47_SPV`, `P47_XLE`, `P47_XSTL`), power rails (`VSYS_RAW`, `3V3_AON`, `3V3_EPD_LOGIC`), control signals (`P47_PGOOD`, `HW_ARM_GPIO`, `EXP_INT`), and I2C buses (`I2C_SDA`, `I2C_SCL`) are routed monolithically across the board with native copper traces and vias.
3. **Option A Standard Rectangular Battery Integration & Zero-Overlap PCB Outline**:
   - Replaced irregular L-shaped pouch study with standard rectangular cell **Model 323576** ($35.0 \times 76.0 \times 3.2\text{ mm}$, 2050 mAh, 3.8V nominal, 7.79 Wh).
   - Dedicated battery bay located at $X = 2.0..37.0\text{ mm}, Y = 4.0..80.0\text{ mm}$.
   - Upper-left PCB step retracted to $X = 38.0..73.0\text{ mm}, Y = 32.0..83.5\text{ mm}$ (with lower full-width span $X = 2.0..73.0\text{ mm}, Y = 83.5..131.0\text{ mm}$), achieving **$0.0\text{ mm}^2$ XY mechanical overlap** ($1.0\text{ mm}$ X clearance and $3.5\text{ mm}$ Y clearance) between the $323576$ battery and the PCB/components (`U901` charger cluster shifted right to $X \ge 38.68\text{ mm}$), strictly maintaining finished device thickness $\le 7.0\text{ mm}$.
   - **Via Process Qualification**: `C804.2` ground return via moved outside the pad to an external dog-bone position at $(17.40, 104.80)$ ($0.45\text{ mm}$ pad / $0.20\text{ mm}$ drill connected to `C804.2` at $(18.20, 105.00)$ via a $0.30\text{ mm}$ `F.Cu` trace, $0\text{ via-in-pad}$ on `C804.2`), and `U501.57`'s 9 thermal vias ($0.50/0.25\text{ mm}$) are specified as standard 4-layer solder-mask tented/plugged thermal vias (`STANDARD_4L_TENTED_THERMAL_VIAS`).
4. **Bottom Type-C Port Architecture**:
   - Bottom center mid-mount USB Type-C receptacle (`J201` / `MUP U22401-17`) positioned at $(37.5, 126.7)$ with connector mouth extending towards $Y = 132.0\text{ mm}$ (device bottom edge).
   - Dedicated housing opening ($X = 32.4..42.6\text{ mm}, Y = 130.9..132.0\text{ mm}, Z = 0.50..3.85\text{ mm}$).
   - Visible in 3D interactive exploded view with dedicated camera inspection preset ("底部接口 (Type-C)").
5. **JLCPCB / JLC EDA Free Prototyping Coupon Full Compliance**:
   - **Dimensions**: $71.0 \times 99.0\text{ mm}$ ($7.1 \times 9.9\text{ cm}$), strictly within $10 \times 10\text{ cm}$ and $\ge 1 \times 1\text{ cm}$.
   - **Delivery**: 1 single closed `Edge.Cuts` loop (10 segments), single-board delivery without panelization (`单片出货，不做拼版`).
   - **Stackup & Color**: Standard 4-layer FR4 process, green solder mask only (`四层板仅支持绿油`).
   - **ENIG Exposed Gold Area**: Top mask opening $541.93\text{ mm}^2$, Bottom mask opening $54.56\text{ mm}^2$. Single-side ratio on bounding box = **8.49%**, strictly $< 20\%$ threshold.
   - **Anti-Split-Order Uniqueness**: Unique build identifiers and deterministic UUID-tagged `.gbrjob` and Gerber archives (`Unique Build ID: P47-SINGLE-20261029-7684F0CC`).
6. **100% Chinese Mainland (PRC) Component Provenance**:
   - Audited and enforced via [`verify_mainland_bom_compliance.py`](verify_mainland_bom_compliance.py) and documented in [`MAINLAND-COMPONENT-BOM-AUDIT-20261029.md`](MAINLAND-COMPONENT-BOM-AUDIT-20261029.md).
   - **100.0% (`215/215`)** of populated BOM components and **100.0% (`5/5`)** of DNP passives on `Single` (as well as `177/177` + `5/5` on `Core` and `42/42` on `Display`) belong to 26 verified Chinese Mainland manufacturer identities (Espressif, GigaDevice, SGMICRO, Silergy, Cellwise, QST, Shenzhen Nsiway Tech, WAVE, XINLUDA, XySemi, Fenghua Advanced, CCTC, HRE, FOJAN, Sunlord, CJ/JSCJ, JSMSEMI, LRC, Shandong Jingdao, YXC, XKB Connection, XUNPU, MUP, Yichang Power Glory).
   - **0** foreign manufacturers and **0** missing `Manufacturer` or `MPN` fields across all boards.

---

## Technical Specifications & Net Verification Summary

| Metric | Single Unified PCB Specification | Verification Status |
| :--- | :--- | :--- |
| **Dimensions** | $71.0 \times 99.0 \times 0.8\text{ mm}$ | Passed ($< 100 \times 100\text{ mm}$) |
| **Layer Stackup** | 4-Layer FR4 (`F.Cu`, `In1.Cu`, `In2.Cu`, `B.Cu`) | Passed |
| **Internal Ground** | Solid `In1.Cu` GND plane, **0 signal tracks** | Passed (100% solid GND) |
| **GND Continuity** | 173 pads connected to GND net | Passed (0 open items) |
| **DRC Errors** | 0 errors | Passed (KiCad CLI 10.0.5) |
| **DRC Warnings** | 0 warnings | Passed (0 dangling tracks/vias) |
| **Schematic Parity**| 0 issues | Passed (100% matched) |
| **ERC Violations** | 0 violations | Passed |
| **Solder Mask** | Green (`F.Mask`, `B.Mask`) | Passed |
| **Surface Finish** | ENIG (Electroless Nickel Immersion Gold) | Passed |
| **Exposed Gold Ratio** | 8.49% single-side bbox, 10.78% polygon | Passed ($< 20\%$) |
| **Component Count** | 248 placed SMT parts | Passed |

---

## Interconnect Routing Details

The previously open board-to-board control and power signals have been closed natively across the single board:
- **`P47_CKV` & `P47_SPV`**:
  - `P47_SPV` routes on `F.Cu` along $Y = 105.95\text{ mm}$, smoothly jogging north to $Y = 105.35\text{ mm}$ to clear `Via 3V3_EPD_LOGIC at (42.0, 106.05)`.
  - `P47_CKV` runs on `F.Cu` at $Y = 104.95\text{ mm}$ to $X = 38.8\text{ mm}$, transitions to `In2.Cu` via dedicated via to hop under `P47_SPV`, returns to `F.Cu` at $(38.8, 106.95)$, jogs to $(42.475, 106.475)$ and terminates into `VIA P47_CKV at (44.375, 106.475)` on `F.Cu`. Because CKV enters on `F.Cu` and Core exits on `B.Cu`, the via connects on both layers, eliminating dangling via warnings.
- **`I2C_SCL` & `EXP_INT`**:
  - `I2C_SCL` runs on `B.Cu` along $Y = 115.4002\text{ mm}$ past $X = 35.116\text{ mm}$ to $X = 35.60\text{ mm}$ (providing $0.875\text{ mm}$ clearance to `Via 3V3_AON at (35.116, 114.225)`), jogs diagonally to $(36.50, 114.50) \to (36.80, 114.50)$, vias up to `F.Cu` at $(36.80, 114.50)$ (providing $> 0.375\text{ mm}$ clearance to `EXP_INT` on `In2.Cu`), and connects on `F.Cu` to $(43.40, 115.80)$.
- **`HW_ARM_GPIO`**:
  - Dips on `B.Cu` along $Y = 115.95\text{ mm}$ between $X = 32.833$ and $X = 35.500$, providing $> 0.32\text{ mm}$ clearance to `Via EXP_INT at (34.5133, 116.5704)` and $> 0.24\text{ mm}$ to `Via I2C_SCL at (34.0203, 115.4002)`.
- **Power Rails**:
  - `VSYS_RAW`: $0.4\text{ mm}$ trace on `F.Cu` directly connecting PMIC output to system loads.
  - `3V3_AON`: $0.4\text{ mm}$ trace on `F.Cu` connecting AON regulator to MCU and always-on peripherals.
  - `3V3_EPD_LOGIC`: $0.35\text{ mm}$ trace on `B.Cu` connecting Display logic supply to MCU logic translators.

---

## Manufacturing & Delivery Deliverables

Deliverables are packaged in `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261029-r25`:
1. `engineering-candidate/`:
   - `Single.kicad_pcb`
   - `Single.kicad_sch`
   - `Single.kicad_pro`
   - `Single.kicad_prl`
   - `Single.kicad_dru`
   - `Single-drc.json` (0 violations)
   - `Single-erc.json` (0 violations)
2. `jlcpcb-orderpack/Single/`:
   - `JLCPCB_Single_Gerber_4L_Green_ENIG.zip` (Gerbers + Excellon Drill)
   - `BOM_JLCPCB_Single.csv` (Complete component BOM for SMT)
   - `CPL_JLCPCB_Single.csv` (Component Pick & Place coordinate list)
3. `render/` & Artifacts:
   - `Panda47-R25-Exploded-3D.html` (Interactive WebGL 3D exploded diagram with Type-C camera preset)
   - `Panda47-R25-Exploded-4K.png` (4K 3840×2160 exploded rendering)
   - `Panda47-R25-Assembled-4K.png` (4K 3840×2160 assembled rendering)
   - `Panda47-R25-Internal-4K.png` (4K 3840×2160 internal layout rendering)
   - `Panda47-R25-Full-Assembly-1080p.mp4` (1080p 24fps 240-frame full assembly/exploded video animation)
