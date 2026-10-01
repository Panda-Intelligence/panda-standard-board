# Generated Split-C1 fabrication packages

Run `python3 hardware/thin18-compact/release_split_c1.py` from a full-history clone with KiCad 10.0.5 installed.
Outputs are generated locally under core-c1-96x68/, display-c1-45x36/ and split-c1-release.json.
Native CAD, replay inputs, purchasing evidence and validation summaries are versioned; Gerbers, ZIPs, netlists and copied per-package reports are generated and ignored.
Each generated manufacturing package includes BOM/CPL, source hashes, engineering evidence and SHA256SUMS. manufacturing_release remains false until physical qualification is complete.
