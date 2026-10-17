# HDI6 v1 next engineering gates

Current native engineering baseline:
`panda47-hdi6-v1-20261017/engineering-candidate`.

**Design target:** two independent six-layer Core/Display PCBs, all previously
confirmed Pico47 hardware features, unchanged original battery/panel requirement,
whole finished product ≤7 mm **including positive tolerances**.

## 1. Resolve HDI escape process, not just layer count

Current initial six-layer stack (0.8 mm nominal, *provisional*):

| Physical layer | Function now |
| --- | --- |
| L1 F.Cu | signal / components |
| L2 In1.Cu | solid GND reference (inherited) |
| L3 In2.Cu | inherited signals |
| L4 In3.Cu | additional signal |
| L5 In4.Cu | second GND reference (new) |
| L6 B.Cu | signals / components |

Do not install fake F→L4 microvias; adjacent-layer microvias cannot skip L2/L3.
For direct fine-pitch MCU/mux/PMIC escape, compare two **mutually exclusive**
factory-validated options:

1. Preserve L2 ground and route new tracks on L4 using appropriate standard
   through vias where physically legal. Maintain stock Core/Display through-via
   minima and preserve GND plane.
2. Deliberately relocate inherited GND/reference signals to an adjacent layer,
   allowing an L1→L2 laser blind-via escape and signal routing on L2. This
   requires **another** source-bound stackup ECO, zone/track-layer remapping,
   native DRC/ground-return validation and supplier approval. The present
   six-layer candidate does not implement this option.

Any 0.25/0.15 mm POFV/HDI via requires a formally reviewed via type, layer
span, annular ring, drill registration, fill/copper cap, minimum spacing
and actual manufacturer process. A normal F↔B through via re-labelled
"microvia" is not acceptable.

## 2. Electrical routing work

- Core: **24** native opens across U710/U711 multiplexed display data,
  MCU source lines, SDMMC, UART, audio, and control. Prior moved-mux and
  Freerouting studies must not be adopted unless they preserve old native pad
  groups, grounds and all power widths.
- Display: **4** native opens: VCOM→J820.10, VPOS→J820.36,
  I2C_SDA→U810.18 and VP→U810.42. The previous four-net In3 study showed
  zero **geometric** opens but 77 **native DRC errors** and is explicitly
  rejected, not incorporated.
- Prefer local, bounded source-bound routing transactions. For each accepted
  batch: independent native DRC (all severities/all-track), zero missing
  ground pads, ERC/schematic parity, original connected-pad groups,
  GPIO2→R813→U810.EN chain, unchanged U810 negative EP,
  C804 filled/capped return, and no signal copper on reference planes.
- Preserve original widths and power-return/spoke quality. Connectivity alone
  does not qualify signal integrity, power, timing or analog-loop behavior.

## 3. Prototype fabrication gate

These are different states and must not be conflated:

**PCB bare-board prototype readiness** requires 0 opens, zero KiCad violations
and parity/ERC issues, full native schematic/board consistency, correct
manufacturable 6-layer stackup, min-hole/annulus/copper/soldermask and vendor
acceptance, Gerber/Excellon plot/drill/outline verification and board DFM.

**Assembled PCBA prototype readiness** additionally requires a verified
complete BOM, accepted/available component identities including exact PMIC,
inductor, diode and FPC connectors, pick-and-place data for both board sides,
assembly-side plan, via-in-pad copper cap, and SMD/USB/FPC manufacturability.

**Whole-device prototype and power-on readiness** separately requires the
actual 2050 mAh pack/NTC/CV/connectors, complete 4.7-inch display stack and FPC,
≤7 mm product mechanical tolerance stack, safe charging, frontlight OVP and
electrical acceptance. Subsequent EVT must confirm EMI/RF, temperature and
lifetime; those *measured* results are not prerequisites to ordering bare PCBs
but cannot be claimed from clean CAD.

The version has `manufacturing_release=false`,
`physical_qualification_complete=false`, `orders_submitted=false`
until the respective formal gate is satisfied.

## 4. Branch workflow

Source branch `hw/pico47-hdi6-v1` and worktree
`/Users/isaac/workspace/AI/panda-standard-board-hdi6` are independently
maintained. Published **four-layer main** and its r12 external CAD remain
untouched. All future output candidates use the separate
`panda47-hdi6-v1-.../` namespace. No automatic merge to `main`.
