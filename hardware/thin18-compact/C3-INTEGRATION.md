# Thin18 Compact — C3 integration contract

Date: 2026-09-29

Status: engineering / EVT. This is not a manufacturing release.

## C3 objective

C3 integrates the front-light and capacitive-touch interfaces required by the frozen GDEQ0426T82-FT01C display family while keeping the compact PCB at **96 × 68 mm**.

C3 is intentionally split:

- **C3A** freezes logical interfaces, control-resource ownership, sourcing references and placement reservations.
- **C3B** adds exact J803/J804 footprints and the final front-light schematic only after the official display drawing has been transcribed for FPC contact side, tail location and bend direction.

This avoids committing the board to an unverified connector orientation.

## Touch contract

The display touch controller is FT6336U on a separate six-pin FPC.

Logical J803 contract:

1. GND
2. 3V3_TOUCH
3. TOUCH_RST
4. TOUCH_INT
5. I2C_SCL
6. I2C_SDA

The exact physical pin order above remains provisional until the Good Display FT01C mechanical drawing is checked. The electrical functions are frozen; connector MPN, contact side and board orientation are not.

Existing reusable resources:

- U403 / TPS22916 controlled by U601.P01 already creates the independently switchable 3V3_TOUCH domain.
- I2C_SCL and I2C_SDA are already the board management bus.
- FT6336U nominal address 0x38 does not conflict with the current production baseline.
- the existing power-tree baseline already disables 3V3_TOUCH during deep sleep and does not require touch as a wake source.

### Touch control policy for C3A

ESP32-S3-WROOM-1U-N16R8 GPIO35/36/37 must not be used: the N16R8 variant uses Octal PSRAM connections internally.

U601 has only one genuinely spare port, P15. C3A reserves that port for front-light hardware enable rather than touch.

Therefore the C3A touch policy is:

- reset by controlled 3V3_TOUCH power sequencing plus a reset-conditioning network;
- TOUCH_INT is brought to J803/test access, but the EVT firmware may poll FT6336U over I2C while touch power is enabled;
- TOUCH_INT is not a deep-sleep wake source in the baseline;
- if awake polling proves unacceptable in power or latency testing, C3B may add a small I2C GPIO expander or another qualified interrupt path.

This is an explicit EVT compromise, not a claim that interrupt qualification is complete.

## Front-light contract

FT01C exposes two independently driven series LED strings, warm and cool, each specified for no more than 15 V and 15 mA.

Logical J804 contract:

1. LED_W-
2. LED_W+
3. NC
4. NC
5. LED_C-
6. LED_C+

Exact connector MPN/contact side remains blocked on the official drawing.

### Driver architecture

C3 uses a **dual-string I2C WLED driver** architecture so brightness and color temperature do not consume multiple MCU GPIOs.

Primary electrical reference:

- TI LM36922HYFFR
- LCSC C213572
- DSBGA-12
- 2.5–5.5 V input
- two LED strings
- up to 38 V / 25 mA per string
- I2C-programmable independent current sinks
- ASEL=GND target address: 0x36
- HWEN low is the true low-power shutdown state

Current public mainland catalog observation on 2026-09-29: MOQ 1, stock about 10 pieces, 1+ ¥11.1 / 10+ ¥10.84 / 30+ ¥10.66.

Because that stock is too shallow for production assurance, LM36922HYFFR is an **electrical reference / EVT candidate**, not a frozen production MPN. LM3630A remains a functional reference/fallback; a higher-stock mainland or domestic dual-string I2C driver must still be sourced before production release.

### Power/control allocation

- input rail: VSYS_FL_IN derived from the battery/system rail, within the selected driver's 2.5–5.5 V input range;
- U601.P15, previously EXP_P15_SPARE, becomes FL_HWEN;
- I2C_SCL/SDA control brightness and per-string warm/cool current;
- no ESP32 Octal-PSRAM-reserved GPIO is consumed.

The driver cluster must include the selected inductor, output capacitor, input decoupling and any required current/OVP configuration parts from the final driver datasheet.

## Placement reservations

C3A reserves collision-free top-side areas on the 96 × 68 mm C2 placement:

- J803 touch connector envelope: x=1..11 mm, y=36.5..41.5 mm
- J804 front-light connector envelope: x=1..11 mm, y=43..48 mm
- front-light driver/power envelope: x=1..19 mm, y=50..60 mm

All three envelopes were checked against the existing top-side footprint bounding boxes with 0.5 mm clearance and had zero hits.

These are reservations, not final connector coordinates.

## C3B entry gates

1. transcribe the official FT01C touch/front-light FPC tail locations, pitch, contact side and bend direction;
2. select exact J803/J804 connectors and validate mating geometry;
3. select the production front-light driver MPN or explicitly accept the LM36922H supply risk for EVT;
4. calculate inductor/current/output-cap requirements and 15 mA/string limit;
5. implement touch reset conditioning and verify FT6336U power/reset timing;
6. add J803/J804/front-light driver to schematic and PCB;
7. run native ERC, DRC, schematic parity and exact netlist-delta review;
8. update the 3-D/Z-stack model using the 1.98 mm FT01C display stack;
9. only then start final compact routing.
