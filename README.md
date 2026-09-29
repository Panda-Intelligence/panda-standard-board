# Panda Standard Board

Open hardware design sources and engineering documentation for the **Panda Standard Board**, maintained by Panda Intelligence.

## Current hardware baseline

The current published engineering baseline is:

- **Board:** Thin18 domestic EVT
- **PCB checkpoint:** `routing142`
- **PCB SHA-256:** `ccc19c5402f633638ed72e7c94a92375684037a1f9c04f63072dc58f86c16071`
- **KiCad validation:** 0 DRC violations, 0 unconnected items, 0 schematic-parity errors; ERC 0
- **Status:** engineering / EVT — **not a manufacturing release**

The baseline includes the current right-side microSD access geometry. Manufacturing, assembly, SI/PI, RF, thermal, tolerance-stack and physical EVT qualification remain separate release gates.

## Repository layout

```text
hardware/
  thin18/
    routing142/        Current KiCad engineering baseline and machine-readable verification evidence
docs/
  design/              Electrical architecture, interfaces, power tree, constraints and design rules
  verification/        ERC/layout/fabrication-readiness engineering reviews
  mechanical/          Board/mechanical interface review notes
LICENSES/
```

## Opening the design

The design was validated with **KiCad 10.0.5**. Open the complete project under:

```text
hardware/thin18/routing142/eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/
```

Project-local symbol and footprint libraries are included where the design depends on them.

## Verification boundary

A clean KiCad DRC/ERC result means the design database is internally consistent. It does **not** establish production qualification, regulatory compliance, component derating, RF performance, thermal margin, assembly yield or mechanical fit of real production parts.

Use tagged manufacturing releases, when available, for fabrication rather than assuming the newest engineering checkpoint is production-ready.

## Licensing

Hardware design sources: **CERN-OHL-S-2.0**.

Documentation: **CC BY-SA 4.0**, unless otherwise noted.

Third-party component models, symbols, footprints, manufacturer names and trademarks retain their respective rights and licensing terms.
