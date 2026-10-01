# Thin18 Compact C4D EVT qualification

This directory is the fail-closed evidence package for qualification items 4–12.

Current state: **NOT RUN**. No traceable Thin18 Compact assembly or calibrated bench/RF instruments were detected on the authorized Mac on 2026-09-30. The connected USB devices were a phone, hubs and Ethernet; they are not qualification evidence.

A KiCad-clean board, a datasheet, a calculation or a development board never counts as a physical measurement. A test can become `MEASURED_PASS` or `MEASURED_FAIL` only when all of the following are bound together:

- exact PCB SHA-256 and assembly BOM SHA-256;
- sample serial number and component lots;
- firmware SHA-256 and configuration;
- approved test-limit revision;
- instrument identity, range and calibration state;
- raw evidence files with SHA-256;
- observed values and review sign-off.

Files:

- `qualification-plan.json` — item 4–12 procedures, required evidence and gates;
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
All existing sample, instrument, approved-limit, independent-review and Q04-Q12
requirements still apply. No physical measurement has been recorded.

The committed candidate pins only both native PCB identities and the relative
generated-candidate path. The generated production/split-c1-qualification.json
pins the run-specific package digest, so exporting from a different checkout
does not modify tracked qualification inputs. Both layers are checked at release.
