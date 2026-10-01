# Thin18 Compact Split-C1 two-board EVT plan

This directory is the fail-closed evidence package for qualification items Q04-Q14.

Current stage: **PCB DESIGN, NO PHYSICAL SAMPLES** (user confirmation2026-10-01). All11 tests are planned and NOT_RUN. Core-C1 and Display-C1 are distinct PCB designs. The USB serial device on the Mac is the old Murphy/development board and is excluded. Instrument entries remain empty until the future bench is registered.

A KiCad-clean board, a datasheet, a calculation or a development board never counts as a physical measurement. A test can become `MEASURED_PASS` or `MEASURED_FAIL` only when all of the following are bound together:

- exact PCB SHA-256 and assembly BOM SHA-256;
- sample serial number and component lots;
- firmware SHA-256 and configuration;
- approved test-limit revision;
- instrument identity, range and calibration state;
- raw evidence files with SHA-256;
- observed values and review sign-off.

Files:

- `qualification-plan.json` — Q04-Q14 procedures, required evidence and gates;
- `sample-manifest.json` — empty template until a real assembly exists;
- `instrument-manifest.json` — empty template until instruments are connected/recorded;
- `measurements.csv` — structured result rows;
- `fixture-bom.csv` — required bench fixtures/instruments;
- `verify_qualification.py` — rejects paper-only PASS and manufacturing release;
- `evidence/` — raw captures, logs, photos and exports; never replace them with prose summaries.

Run:

```sh
python3 hardware/thin18-compact/qualification/c4d-evt/verify_qualification.py
python3 hardware/thin18-compact/qualification/c4d-evt/verify_qualification.py --release
```

The first command validates the current truthful state. The second must return exit code 2 until every required physical gate is complete and independently signed.

## Current Split-C1 assembly identity

The current release-candidate record binds both Core-C1 and Display-C1. Generate
the local packages with `python3 hardware/thin18-compact/release_split_c1.py`
before checking fabrication artifact hashes. For a measured Split-C1 sample,
include `pcb_identities` matching both entries in release-candidate.json and
`assembly_boms` matching each board's production manifest BOM path and SHA-256.
A current Core with an old Display, or a different assembly BOM, is rejected.
All existing sample, instrument, approved-limit, independent-review and Q04-Q14
requirements still apply. No physical measurement has been recorded.

The committed candidate pins only both native PCB identities and the relative
generated-candidate path. The generated production/split-c1-qualification.json
pins the run-specific package digest, so exporting from a different checkout
does not modify tracked qualification inputs. Both layers are checked at release.


## Bring-up sequence after the samples arrive

1. Register one pair: separate Core/Display serials, both native PCB SHA256s,
   both assembly BOM SHA256s, parts/board lots, panel and full battery identity,
   firmware build and photos. Approve applicable test limits before testing.
2. Inspect each board unpowered: orientation/reflow/bridges, ground/power shorts,
   exact DF40 socket versus plug, each signal and the reserved NC matrix. Probe
   from the interface contract; do not connect a generic development board.
3. Test Core independently with the Display disconnected, current-limited
   supply and approved battery simulator/charger/NTC limits. Record Q04-Q10
   electrical evidence before attaching the real cell or panel flexes.
4. Test Display with an approved powered fixture only on J1 pins35/36(3.3V)
   and contracted ground pins. Inspect L1/Q1/D1-D3 and J2 contact side first;
   use rated high-impedance probes for EPD rails. Run Q13 startup/rail/SPI/BUSY,
   white/black/pattern refresh, sleep and shutdown. Follow the exact panel
   initialization/waveform profile; no unqualified voltage limits are invented.
5. Remove all supply sources before mating or unmating. Check J201 body/stakes/
   solder clearance before seating. Support the Display independently and
   measure the nominal1.5mm gap at the approved tolerance. Run Q14 matched
   startup/reset/sleep/backfeed tests; Q11 checks touch/frontlight flexes.
6. Fit the complete selected protected pack, NTC harness, panel flexes and case
   supports using maximum dimensions and swelling allowance, then run enclosed
   Q12 thermal/RF/concurrent-load/soak and Q14 port/retention checks. A physical
   failing test remains MEASURED_FAIL with evidence; do not replace it with a
   CAD result. Complete all11 tests before independent product release.

A row's `state` must collectively cover every `required_sample_states` entry.
For Split-C1, `board_serial_numbers` must contain Core-C1 and Display-C1;
`sample_id` is the pair identity. `pcb_sha256` and legacy `assembly_bom_*`
fields remain the Core values; `pcb_identities` and `assembly_boms` bind both.
No physical procedure above has been executed in the design-stage session.


To run the negative controls, generate the two current production packages
first, then run `python3 hardware/thin18-compact/qualification/c4d-evt/run_negative_controls.py`.
Controls reject missing Display test coverage, paper-only PASS, untraceable
samples, expired calibration, premature release, wrong Display PCB/BOM, wrong legacy Core BOM,
missing Display serial and omitted paired-board operating states. Synthetic binding fixtures are never registered as
physical samples and the destructive input changes are restored in `finally`.

## X4 Pro runtime comparison in Q12

The user's reference is XTEINK X4 Pro: official1100mAh and5.95mm device body.
Its official FAQ gives no reproducible hours/days figure. Do not use standard
X4 claims, equal capacity or equal brightness percentages as runtime evidence.
See `qualification-plan.json` -> `runtime_benchmark_protocol` for the proposed
25+/-2C,30s/page,full-refresh-per10pages comparison and required raw records.

Q12 includes frontlight-off, cool/warm/mixed-light and sync/sleep reading states
for the paired boards. Register a real identified X4 Pro, match measured white
page luminance and workload, record firmware/battery health, and integrate
current and voltage at the battery terminals down to normal protected shutdown.
Approve luminance, wireless schedule and numeric runtime/current limits first.
No benchmark measurement or runtime PASS exists at the PCB design stage.
The mechanical audit's880mAh allowance and sensitivity hours are illustrative
calculations only; the current DF40/candidate-cell stack does not support the
5.95mm comparison goal. Both PCB designs and all existing physical gates remain.
