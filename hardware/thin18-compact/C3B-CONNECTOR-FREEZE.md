# Thin18 Compact — C3B connector freeze

Date: 2026-09-29

Status: exact connector **candidate** freeze; not manufacturing release.

## Official FT01C tail functions

The latest Good Display GDEQ0426T82-FT01C drawing/specification is the authority for panel-side function order.

### Touch FPC

Panel-side six-pin order:

1. GND
2. VDD3.3V
3. RST
4. INT
5. SDA
6. SCL

Board net mapping:

1. GND
2. 3V3_TOUCH
3. TOUCH_RST
4. TOUCH_INT
5. I2C_SDA
6. I2C_SCL

### Front-light FPC

Panel-side six-pin order:

1. LED W-
2. LED W+
3. NC
4. NC
5. LED C-
6. LED C+

This remains the authoritative electrical ordering even where third-party boards number their connector pads differently due to flex orientation.

## J803 / J804 exact connector candidate

Candidate for both six-pin tails:

- Hirose `FH34SRJ-6S-0.5SH(50)`
- 6 positions
- 0.5 mm pitch
- back-flip ZIF
- top **and** bottom contacts
- supports 0.30 mm flex in the independent mechanical reference

A dual-contact connector reduces the risk of choosing the wrong contact-side variant while the exact flex-fold orientation is still being frozen.

This is not yet a production-approved connector. Before C3B schematic/PCB integration it still needs a direct manufacturer-land-pattern check and an overlay against the Good Display drawing.

## Driver electrical reference

C3 retains `LM36922HYFFR / LCSC C213572` as the dual-string I2C front-light electrical reference.

Required reference application parts from TI:

- L1: 10 µH class;
- CIN: >=2.2 µF effective;
- COUT: >=1 µF effective at the boost voltage;
- external Schottky between SW and VOUT;
- ASEL=GND -> I2C 0x36;
- PWM may be held at a defined static level when brightness is controlled exclusively over I2C;
- HWEN is controlled by `U601.P15 = FL_HWEN` so true hardware shutdown remains available.

Exact inductor/Schottky/capacitor MPNs remain a C3B sourcing task.

## Touch control policy

`U601.P15` is consumed by front-light HWEN.

For the baseline compact EVT:
- FT6336U reset is produced by controlled `3V3_TOUCH` sequencing plus a dedicated reset-conditioning network;
- touch events may be polled on I2C while awake;
- `TOUCH_INT` is carried to the connector and test access but is not a deep-sleep wake source.

If polling fails the power/latency target, add a small I2C GPIO expander in C3B rather than reusing ESP32-S3 N16R8 GPIO35/36/37, which are reserved by Octal PSRAM.
