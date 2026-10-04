# Split-C1 — PG / PSEL functional migration

## Scope and acceptance boundary

ECO `SPLIT-C1-POWER-INTEGRITY-01` continues the **main-branch Split-C1** at
`6906a246b1658386278c13912e77bfe833c1d8ea`. Core remains 96 x 68 mm / 4 layers;
Display remains 45 x 36 mm / 2 layers. Both remain 0.8 mm. The connector pair,
60-pin mapping, board outlines, layer stack and design-rule configuration are
unchanged. Thin7 and portrait-R2 are not the source of this PCB.

The original populated BOM had 155 mainland-manufacturer refs, but that identity
result did not establish a complete electrical migration. This ECO adds one
mainland IC and fixes two circuit-level omissions. The resulting expected BOM
is **156 refs: Core119 / Display37**; there are **17 populated board-level IC
refs: Core14 / Display3**. Native checks and deterministic replay must pass again.
Manufacturing release, actual PCBA acceptance and physical EVT remain false.

## U906 restores a real supply-status source

The prior `PG_3V3_MAIN` connected only XL9535 U601.17 and TP16. The selected
SGM62125 regulator has no PG output. U906 is now **SGM809B-TXN3LG/TR**, monitoring
`3V3_AON`: pin1=GND, pin2=active-low push-pull nRESET/PG_3V3_MAIN, pin3=3V3_AON.
Its original-maker SOT-23 TX00031.001 lands are 0.76 x 0.76 mm, 1.90 mm paired
pitch and 2.29 mm opposing-row pitch. The new body is at (17,18.75), F.Cu.
No existing connector, host module, power IC or RF/USB component moved.

This is **informational power status**, not an MCU hard-reset circuit. The
3.08 V nominal threshold has a 2.966..3.181 V full-temperature range; it cannot
prove a reset before every MCU 3.0 V minimum. Recovery delay is 120..400 ms at
full temperature. Behavior below the supervisor's specified supply range, supply
ramps, noise rejection and board-level timing need physical verification.
Firmware must leave XL9535 P14 configured as an input; driving it creates
contention with the push-pull supervisor. Do not use charger nPG as 3.3 V PG.

Original-maker basis: SGM803B/SGM809B/SGM810B, October2024 Rev.A.2, pp2-4,8,10:
https://www.sg-micro.com/rect/assets/50d03578-1421-4ff6-a32f-020bee34d824/SGM803B_SGM809B_SGM810B.pdf

## PSEL no longer depends on downstream AON startup

U901 is the **non-A/non-D SGM41513YTQF24G/TR**. The original PSEL connection to
3V3_AON did not establish the high input level before batteryless source
detection. The manufacturer power-up sequence starts internal REGN before
source-type detection and then enables the converter.

The exact existing domestic resistors are reused:

```text
SGM41513_REGN -- R204 1.2k / 1% --+-- U901.2 PSEL
                                |
                              R201
                             5.6k / 1%
                                |
                               GND
```

R204 remains FH RS-03K1201FT / C118396; R201 remains FH RS-03K5601FT / C99891.
These are now explicit divider components, not an analog ILIM network. The
machine-readable pin and part contract is `split-c1-power-integrity.json`.
The old BQ_ILIM and BQ_ILIM_RC net names are absent.

Using the conservative 4.45..5.4 V REGN envelope, resistor 1% extremes and a
+/-1 uA leakage sensitivity, PSEL calculates to **3.650693..4.463635 V**, versus
VIH0.9 V and the 6 V absolute limit. Divider load is at most approximately
0.802 mA in this screen. The manufacturer's leakage table is measured at 1.8 V:
using +/-1 uA at the divider's higher voltage is an **assumption**, not an
additional guaranteed specification. Startup ramps, loading and all corners
must be measured; absolute maximum is not a substitute for qualification.

High PSEL selects a **nominal 500 mA reset input-current setting**. This is not
an independent hardware current ceiling: host register writes can override it.
Read back IINDPM after startup, watchdog/reset and source changes. Keep OTG
disabled and do not increase current without a qualified source/pack/copper
policy. USB enumeration, pre-enumeration and suspend compliance remain separate
open gates; a 500 mA setting alone does not prove USB compliance.

Original-maker basis: SGM41513/SGM41513A/SGM41513D, April2025 Rev.C.1, pp3,5,11,20-21:
https://www.sg-micro.com/rect/assets/58a4fe4d-da1d-49a3-b312-5664211d9016/SGM41513_SGM41513A_SGM41513D.pdf

## C204 and routing are controlled changes

C204 retains its exact FH0603B334K500NT/C188679, 330 nF/50 V X7R identity. It is
repurposed as the supervisor bypass, pin1=3V3_AON/pin2=GND, at (16.5,16),180deg.
It is no longer an obsolete charger RC component and is not a PSEL delay.

Only the two old AON-to-PSEL branch tracks and former BQ_ILIM_RC copper are
removed. Existing BQ_ILIM copper is renamed PSEL where reused. Seventeen new
segments and four vias complete the connections; new traces use F.Cu/B.Cu.
The rest of the pre-existing copper, including USB/RF/SD and the Display PCB,
is unchanged. Main-branch existing internal-layer signals are not reinterpreted
as a Thin7 ground-plane contract. `split-c1-power-integrity-adoption.json`
records source hashes and the exact adoption; layout replay is additive and
rejects an unexpected predecessor. No clearance or DRC exclusion is relaxed.

## Verification and next gates

Run from the repository root:

```sh
python3 hardware/thin18-compact/release_split_c1.py --target split-c1
python3 hardware/thin18-compact/verify_split_c1_supply.py --negative-controls
```

The native current and rebuilt boards must both pass DRC/open/parity/ERC
0/0/0/0. Separate semantic checks reject a downstream-AON PSEL connection,
reversed supervisor pins, wrong threshold/output/charger variants, missing
bypass, old ILIM nets or unauthorized PG loads. Twenty-two unit tests exercise
circuit and target-isolation cases; synthetic fixtures are never saved as
supplier receipts or measured EVT results.

**Seven SMT refs / four exact groups now need catalog mapping or accepted
consignment:** U902, U905, U402-U405 and new U906. U906's exact code, received
inventory, lot, packing and assembler acceptance are unknown; no lookalike code
is assigned. Procurement still requires the full system BOM, not only these
seven refs. The supplier receipt verifier also follows D202 and post-SMT C301.

Before a functional prototype is declared complete: verify PG recovery/falling
edges and P14 input-only behavior; test no-battery/empty-battery/normal-battery
cold starts with AON, REGN, PSEL and input-current capture; exercise USB/reset/
watchdog limits; integrate the actual charger/regulator/gauge/RTC/frontlight
firmware contracts. Existing physical, thermal, battery and enclosure gates
remain open. No board-level identity audit certifies the Flash/PSRAM die inside
the ESP module or controllers inside externally supplied screen/touch modules.
