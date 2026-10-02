# Panda Standard Board

Open hardware design sources and engineering documentation for the **Panda Standard Board**, maintained by Panda Intelligence.

## Active compact product work

The compact product now targets **112 x 75 x 7.0 mm** with two PCBs.
See [Thin7 redesign](hardware/thin18-compact/thin7/THIN7-REDESIGN.md).
Its mechanical outlines require electronic relayout and part qualification;
current Split-C1 routed CAD does not meet 7 mm and is not a factory release.

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

## Product visualization

Explore the [interactive Thin18 routing142 assembly model](hardware/thin18/routing142/visualization/Panda-thin18-routing142-exploded.html) or watch the [exploded-view video on YouTube](https://youtu.be/T_Nb8tvqas8).

The model is an engineering visualization for design communication. Mechanical fit and manufacturing readiness require separate validation.

## Verification boundary

A clean KiCad DRC/ERC result means the design database is internally consistent. It does **not** establish production qualification, regulatory compliance, component derating, RF performance, thermal margin, assembly yield or mechanical fit of real production parts.

Use tagged manufacturing releases, when available, for fabrication rather than assuming the newest engineering checkpoint is production-ready.

## Licensing

Hardware design sources: **CERN-OHL-S-2.0**.

Documentation: **CC BY-SA 4.0**, unless otherwise noted.

Third-party component models, symbols, footprints, manufacturer names and trademarks retain their respective rights and licensing terms.
