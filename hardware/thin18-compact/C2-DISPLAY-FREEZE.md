# Thin18 Compact — C2 display / touch / front-light freeze

Date: 2026-09-29
Status: engineering input freeze for compact EVT; **not manufacturing release**

## Selected integration target

Compact EVT will use the Good Display **GDEQ0426T82-FT01C** family target rather than sizing the PCB to the old product envelope.

Frozen mechanical/electrical inputs:

- 4.26-inch monochrome E-paper;
- 800 × 480;
- SSD1677;
- module outline **105.33 × 62.37 × 1.98 mm** for the front-light + touch assembly;
- active area **92.8 × 55.68 mm**;
- main display interface: 24-pin FPC, 0.5-mm pitch, SPI;
- touch IC: **FT6336U**, 2.8–3.6 V;
- touch interface: separate 6-pin FPC;
- front light: separate 6-pin / 0.5-mm FPC, warm + cool LED strings, each ≤15 V / ≤15 mA.

The bare GDEY0426T82 panel is thinner (0.926 mm), but compact product mechanical planning must use the **1.98 mm FT01C stack**, not the bare-panel thickness.

## Existing J802 compatibility

The current routing142/C1 J802 already implements the SSD1677 24-pin raw-panel interface.

A deterministic netlist comparison is maintained by `verify_c2_display_contract.py`.

Result:

- **22 / 24 pins are compatible as-is**;
- pin 8 is currently GND; this is correct because Good Display defines it as BS1 and BS1 low selects 4-wire SPI;
- **pin 6 and pin 7 must change from GND to NC**;
- all other signal and power assignments match the target functionally.

Therefore the new screen is a small display-interface ECO, not a display subsystem redesign.

## Touch integration

The existing architecture already reserves:

- `3V3_TOUCH` behind U403 TPS22916;
- `I2C_SCL` / `I2C_SDA`;
- `TOUCH_INT` aggregation;
- `TOUCH_RST`;
- test point / isolation policy for the touch power domain.

C2 therefore allocates a new compact-board connector **J803** with the logical contract:

1. GND
2. 3V3_TOUCH
3. TOUCH_RST
4. TOUCH_INT
5. I2C_SDA
6. I2C_SCL

The physical FPC contact side/orientation is **not frozen** until the official FT01C mechanical drawing is transcribed into the enclosure coordinate system.

## Front-light integration

FT01C exposes a separate six-pin front-light FPC:

1. LED W-
2. LED W+
3. NC
4. NC
5. LED C-
6. LED C+

The current core architecture exposes `VSYS_FL_IN` but intentionally left switching/driver behavior to an adapter.

For the compact product, the adapter-board assumption is removed: C3 must select an on-mainboard front-light driver that supports the two series strings without violating ≤15 mA/string or ≤15 V/string. Exact driver MPN remains open and must be qualified for shutdown leakage, dimming behavior, efficiency, acoustic noise, EMI and thermal rise.

A connector placeholder **J804** is reserved now; no production MPN is assigned before the official drawing/contact-side check.

## Compact mechanical consequence

C1 PCB remains **96 × 68 mm**, below the 100 × 100 mm coupon boundary.

The display is wider/longer than the PCB by design. Product envelope should be driven by the 105.33-mm panel plus enclosure tolerances, approximately **108–112 mm** long.

The rear battery envelope remains a C1 target, not a released cavity. The FT01C thickness of 1.98 mm replaces the earlier bare-panel 0.926-mm assumption for all Z-stack calculations.

## C3 entry gates

Before starting full reroute:

1. apply J802 pin 6/7 NC ECO to the compact schematic and PCB;
2. add J803 touch connector with the six logical nets above;
3. reserve J804 front-light FPC and select a front-light driver architecture;
4. import official FT01C connector locations/contact side into the mechanical coordinate contract;
5. freeze battery thickness + swelling allowance;
6. re-run ERC, schematic parity and unrouted-placement DRC;
7. only then start C3 routing.

routing142 remains the old-form-factor routing reference and is never overwritten by compact work.
