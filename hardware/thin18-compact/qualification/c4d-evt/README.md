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
