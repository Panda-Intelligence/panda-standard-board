# Thin18 Compact — C4 comprehensive domesticization

Date: 2026-09-29 (historical C4 study)

Current authority: [SPLIT-C1-DOMESTICIZATION.md](SPLIT-C1-DOMESTICIZATION.md). The new requirement permits no retained foreign-component exception; 18 refs remain blocked. This C4 study does not override current Split-C1 CAD or its audited BOM.

Goal: replace every realistically replaceable foreign-origin component with a mainland-China manufacturer part, while reducing chip count where a domestic architecture is safer/cheaper than one-for-one substitution.

## Rules

1. Mainland manufacturer only counts as domestic. A foreign brand merely stocked by LCSC does not.
2. Safety-critical charger, battery path, USB, ESD and connectors never become production-approved from price/name similarity.
3. "SELECTED" means documentary electrical + package compatibility is sufficient to enter the engineering CAD candidate. Physical EVT remains separate.
4. Major subsystem replacements are redesigns, not "compatible substitutes".
5. routing142 remains reference-only. Compact C4 is allowed to change schematic, firmware and placement before final routing.

## C4 target architecture

### Keep domestic incumbents

- ESP32-S3-WROOM-1U-N16R8 — Espressif
- GDEQ0426T82-FT01C — Good Display
- FT6336U — FocalTech
- U206 74LVC1G17XC5G/TR — SGMICRO

### C4-PWR

Selected documentary baseline for schematic redesign:

- SGMICRO `SGM41513YTQF24G/TR` / LCSC C5153778
  - 1S synchronous switching charger;
  - NVDC system power path;
  - I2C address 0x1A;
  - exact non-D variant uses VAC/PSEL/nPG and does **not** expose D+/D-;
  - PSEL high provides a conservative 500mA default input-current policy;
  - TS/NTC + JEITA charging behavior;
  - battery-side typical current about 8.5 µA with BATFET enabled;
  - ship leakage about 2.5 µA.
- Cellwise `CW2215BAAC` / JLC C7502681
  - current-sensing fuel gauge;
  - approximately 5 µA active / 0.5 µA shutdown;
  - I2C, NTC and bidirectional current reporting.
- SGMICRO `SGM62125AXG/TR`
  - 4-switch buck-boost;
  - approximately 2.25 µA quiescent current;
  - I2C-programmable output;
  - ADDR=high starts at 3.4 V; compact firmware will lower the AON rail to 3.3 V after startup.

This combination targets removal of:

- BQ25628E;
- BQ27427;
- TPS63802.

Typical core power-management current comparison, before board-level leakage:

- incumbent trio: about 21.5 µA;
- C4 selected trio: about 15.75 µA.

The orderable generic AXP2101/C3036461 is no longer the C4 baseline because its publicly listed charger is linear (100 mA–1 A). It remains a research alternative only; compact thermal loss at high charge current is not acceptable to assume away.

The previously considered SGM62118 remains electrically valid, but SGM62125 is preferred because its typical quiescent current is much lower.

**Historical load-switch assessment superseded:** the disabled-state-only rejection
below the old C4 contract is no longer the current candidate. Split-C1 now uses
SGM2578SDYG/TR with the January 2026 Rev.A.2 datasheet p9 specifying RCB for ON
high/low, a 0.5mm-pitch footprint and local U403 output C516. The datasheet's
front-page wording still conflicts with p9; exact-version manufacturer confirmation,
reverse-current EVT, leakage/timing and supply acceptance remain mandatory.
This engineering change does not establish full-time RCB physical qualification.

### C4-USB

For the product baseline "USB2 device + 5V sink/charge only":

- remove TUSB320 attach/current-policy dependency;
- CC1 = 5.1k Rd to GND;
- CC2 = 5.1k Rd to GND;
- native ESP32-S3 USB D+/D-;
- domestic low-capacitance ESD;
- conservative charger input-current policy.

Target removal after compliance review:

- TUSB320LI
- TPS70933
- SN74AUP2G07 used only for CC-state translation
- TPS3700 VBUS-status chain where PMIC VBUS/IRQ can replace it

No PD/PPS negotiation is part of this baseline.

### C4-GPIO

**Selected engineering substitution:**

- TCA9535PWR → XINLUDA XL9535 / C561273

TSSOP-24 pin assignment is identical to the incumbent TCA9535 PW package. Register/default/interrupt semantics remain subject to firmware regression, but the substitution is eligible for same-net CAD application.

### C4-IMU

- LSM6DSO32XTR → QST QMI8658A / C3021082
- mainland 6-axis IMU, LGA-14, 1.71–3.6V, I2C/I3C/SPI
- requires footprint/pin remap and firmware driver port
- ±16g ceiling means any actual dependency on ±32g must be removed or the substitution rejected

### C4-RTC

Current domestic redesign candidate:

- RV-3028-C7 → GATEMODE BM8563EMA + domestic 32.768kHz crystal

Tradeoff accepted for study:
- much lower BOM/supply complexity;
- not an accuracy/current equivalent;
- firmware + crystal + backup-current qualification required.

No domestic integrated-crystal RTC has yet been proven equivalent to RV-3028.

### C4-AUDIO

Preferred low-cost architecture:

- MAX98357A → Nsiway NS4168 / C910588
- direct I2S mono Class-D, 3–5.5V
- package changes TQFN16 → ESOP8

For a future microphone/voice SKU:
- Everest ES8311 / C962342 codec
- Nsiway NS4150B / C189961 analog Class-D PA

The voice architecture is not required for the base reader.

### C4-FRONTLIGHT

C4D-10B replaces the foreign LM36922H reference with a mainland engineering candidate:

- SGMICRO `SGM37601YTRL20G/TR`;
- TQFN-3.5×3.5-20L, official land pattern transcribed into the project library;
- I2C address `0x36` with A0 low;
- LED1/LED2 drive the FT01C warm/cool strings;
- U601 P15/P16 provide hardware enable and PWM;
- J804 uses the exact FH34SRJ-6S-0.5SH(50) / C224194 land pattern.

The reset defaults are unsafe for this panel if light is enabled immediately: SGM37601 resets to 20 mA and 36 V OVP, while the panel limit is 15 mA/string. C4D-10B therefore keeps `FL_HWEN` and `FL_PWM` low until firmware writes:

- `REG0x01 = 0x56` — 14.5 mA nominal;
- `REG0x02 = 0xA1` — internal compensation, 18 V OVP, 2.7 V UVLO;
- `REG0x03 = 0x2B` — PFM enabled, 1 MHz switching.

Selected support parts:

- Sunlord `SWPA252012S100MT` / C37428, 10 µH;
- CJ `B5819W SL` / C8598, 40 V / 1 A Schottky;
- Fenghua input/VIN/VDC/output capacitors and boot pull-downs.

The first-order low-input/high-output estimate gives about 0.301 A peak inductor current, with approximately 2.92× saturation and 2.06× rated-current margin.

Fresh C4D-10B native checks: ERC 0, DRC 0, schematic parity 0; 436 unconnected items remain because final compact routing has not started.

Production RFQ/stock confirmation, current accuracy, open-string behavior, DC-bias capacitance, thermal, EMI, acoustic noise, shutdown leakage and FPC mechanical qualification remain open. This is not manufacturing release.

### C4-LOGIC / EPD

Candidates:
- AIP74LVC2G17 / Wuxi I-core or lingxingic LVC2G17 for EPD Schmitt buffers after Ioff/threshold review
- mainland 2G07 candidate after open-drain + partial-power proof
- UMW AO3400A only if EPD switch-node VDS/overshoot permits 30V; otherwise choose higher-VDS mainland MOSFET
- Yangjie/CJ Schottky family
- Sunlord 47uH power inductor
- Fenghua 50V MLCC

### C4-MECHANICAL COMPONENTS

Do **not** force a domestic connector purely to reach a percentage target.

Still blocked on exact geometry evidence:
- J802 24-pin EPD FPC
- J803/J804 6-pin touch/front-light FPC
- USB-C mid-mount receptacle
- microSD socket
- DF58 battery connector
- JST SH connectors
- side switches

These remain foreign until an exact mainland drawing/mating/height/footprint-qualified replacement is found.

## Expected result

C4 aims to make the **active silicon and general passives overwhelmingly mainland-origin**. The remaining foreign content should be concentrated in mechanically constrained connectors/switches only where forcing a substitute would create higher reliability or tooling cost.

Physical qualification remains mandatory before manufacturing release.