# Thin18 Compact — C4 check closure

Date: 2026-09-29

## Scope closed

The following checks have been completed for the current compact domesticization study:

- all 203 native schematic references have an explicit domesticization disposition;
- all 97 unique passive groups / 137 passive references have been screened;
- exact mainland procurement metadata has been applied to 20 capacitor references;
- U601 has been changed in CAD from TCA9535PWR to XINLUDA XL9535 / C561273;
- mechanical/interconnect mainland drop-in screening is complete for USB-C, microSD, battery/JST/FPC connectors, side switches and external NTC;
- firmware dependency audit is complete for QMI8658, power/charger/gauge, USB-C simplification, audio, RTC and XL9535;
- C4 power architecture documentary review is complete;
- native KiCad DRC / schematic parity / ERC checks were rerun on the active C4C candidate;
- fail-closed negative controls were executed, not merely listed.

## Active CAD candidate

`c4c-96x68-domestic-passives`

Fresh native results:

- DRC violations: 0
- schematic parity: 0
- ERC violations: 0
- unconnected items: 447 — expected because compact routing has intentionally not started
- native references: 203
- pin/net tuples: 601

Topology is identical to C4A; the C4C delta is procurement metadata for selected same-footprint passives.

## Applied mainland selections

Already applied in CAD:

- U601: XINLUDA XL9535 / C561273
- 11 × 100 nF 0402: Fenghua 0402B104K250NT / C56392
- 9 × 1 µF 0603: Fenghua 0603B105K250NT / C59302
- existing domestic parts such as ESP32-S3-WROOM-1U-N16R8 and SGMICRO U206 remain retained

## Selected for C4 schematic redesign

Power baseline:

- charger / NVDC: SGMICRO SGM41513YTQF24G/TR / C5153778
- fuel gauge: Cellwise CW2215BAAC / JLC C7502681
- 3V3 AON buck-boost: SGMICRO SGM62125AXG/TR
- USB-C: passive 5.1 kΩ Rd sink, native ESP32-S3 USB, charger/PMIC VBUS status

Typical current of those three active power ICs is approximately 15.75 µA before board leakage, versus approximately 21.5 µA for the incumbent BQ25628 + BQ27427 + TPS63802 trio.

Other redesign candidates:

- QST QMI8658A / C3021082
- Nsiway NS4168 / C910588
- GATEMODE BM8563EMA / C269878
- mainland low-cap ESD candidate after exact clamp/capacitance/pin proof

## Explicitly rejected / blocked

- AXP2101 as the baseline charger: currently orderable generic part uses a linear charger; thermal loss at high compact-device charge current is not accepted.
- SGM2578S/SD as direct TPS22916 replacement: published reverse-current protection does not prove enabled-state full-time RCB.
- AIP74LVC2G17 direct value-only ECO: attempted CAD change caused parity/ERC failures; a correct domestic symbol must be created before reconsideration.
- forced mainland mechanical connector substitutions: no exact drop-in evidence was found.
- precision/pulse/current/DC-bias passives without exact evidence: remain blocked, not downgraded.

## Negative controls

Executed and passed:

1. selected schematic MPN mutation rejected;
2. missing reference status rejected;
3. physical PASS without raw measurements rejected;
4. unsafe load-switch selection rejected;
5. manufacturing release gate rejected.

## What is not complete

This document closes the **documentary and current-CAD checking phase**, not product release.

Still required:

- implement the C4 power/USB/IMU/audio redesign in schematic and PCB;
- C4D-10A/J803 touch and C4D-10B/J804 + SGM37601 front-light CAD are now integrated; physical FPC/current/thermal/EMI qualification remains required;
- reroute the 96 × 68 mm board to open = 0;
- generate final production BOM/CPL/Gerbers;
- build real EVT units;
- run charging/NTC/ship/deep-sleep/USB-C/RF/EMI/thermal/audio/display/touch/mechanical qualification.

Physical tests completed: **0**.

Manufacturing release: **false**.

## Post-closure implementation progress

After the original documentary closure, C4D-10A integrated the exact touch FPC and C4D-10B integrated the mainland SGM37601 dual-string front-light circuit. C4D-10B passes ERC/DRC/parity at 0/0/0 and includes a fail-closed firmware startup contract. The board is still intentionally unrouted and physical tests remain zero.
