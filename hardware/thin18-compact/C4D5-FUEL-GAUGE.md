# Thin18 Compact C4D-5 — domestic fuel gauge

Date: 2026-09-29

Implemented candidate: `c4d5-96x68-cw2217`

- Cellwise `CW2217BAAD`, JLC C5203993, DFN-12.
- Symbol/footprint were transcribed from the public JLC/EasyEDA model and checked against the Cellwise pin contract.
- U301 BQ27427 and R307 BIN pulldown are DNP/off-board in this compact candidate.
- R306 is upgraded to FOJAN `FRM121WFR010TM` / C7467248: 10mΩ, 1W, ±1%, ±50ppm/°C, 1206.
- CSP is on the system side (`BAT_PACKP`), CSN on the cell-connector side (`BAT_CONN_P`), so charge current is positive and discharge current negative.
- CW2217 VDD and VCELL use separate 100Ω filters; VCELL has a dedicated 1µF filter capacitor.
- TS reuses the existing external 10k / B3435 NTC path.

Fresh KiCad:
- ERC 0
- DRC 0
- schematic parity 0
- open 409 (expected: compact board is intentionally not fully routed)

The lower-Iq CW2215B remains a future optimization, not the current EVT baseline, because its public WLCSP ball map was not reproducibly available in this cycle.

Physical SOC/current accuracy, battery profile/FastCali data, NTC behavior and sleep current remain NOT_RUN.
