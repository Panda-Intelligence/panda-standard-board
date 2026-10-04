# Panda Standard Board

Open hardware design sources and engineering documentation for the **Panda Standard Board**, maintained by Panda Intelligence.

## Active Split-C1 prototype and mainland IC continuation

The active continuation is the populated **Core-C1 96 x 68 mm / 4-layer** plus
**Display-C1 45 x 36 mm / 2-layer** design already split and routed on main.
Start with [Split-C1 handoff](hardware/thin18-compact/SPLIT-C1-HANDOFF.md) and the
[PG/PSEL functional migration](hardware/thin18-compact/SPLIT-C1-POWER-INTEGRITY.md).
Do not replace it with Thin7/portrait-R2 experimental CAD merely because an
experiment has a newer timestamp. Thin7 remains a separate, incomplete 7-mm
mechanical target and is not claimed by the Split-C1 bench prototype.

Generate checked prototype data explicitly:

```sh
python3 hardware/thin18-compact/release_split_c1.py --target split-c1
```

Bare-board CAM/DFM, accepted PCBA supply and physical EVT are separate gates.
The new supervisor is a mainland part, but its exact assembly code/receipt is
not yet confirmed. No production qualification or actual purchase is implied.

## Historical published Thin18 baseline

The earlier published integrated-board engineering baseline was:

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

## Opening the active two-board design

The design was validated with **KiCad 10.0.5**. Open the complete project under:

```text
hardware/thin18-compact/core-c1-96x68-split/eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/
hardware/thin18-compact/display-c1-45x36-production-bom/
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

## Split-C1 executable control follow-up

[Portable bench-control core](firmware/split_c1/README.md) implements tested
XL9535/SGM41513/SGM37601 sequencing and a read-only QMI8658A identity probe.
Host tests and native pin/address binding checks run in the explicit Split-C1
export pipeline. This is not product-firmware integration or physical EVT.
The [hardware-finish ECO](hardware/thin18-compact/SPLIT-C1-HARDWARE-FINISH.md) adds default-off charge authorization and a native GPIO2 shutdown path.
Read the updated control binding before using any older firmware. Physical EVT and accepted assembly supply remain separate gates.
