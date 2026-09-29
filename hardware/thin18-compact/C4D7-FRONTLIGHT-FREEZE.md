# Thin18 Compact — C4D-7 front-light domestic freeze

Date: 2026-09-29

Status: engineering selection frozen; CAD integration remains gated.

## Selected mainland driver

SGMICRO `SGM37601YTRL20G/TR` is selected as the C4 domestic front-light driver.

Reasons:
- active production device;
- 2.8–24 V input;
- boost output up to 40 V;
- six current sinks, 6–25 mA/channel;
- I2C-controlled LED current / switching frequency / dimming;
- programmable OVP, default 36 V;
- TQFN-3.5×3.5-20L;
- internal compensation is enabled by default.

FT01C mapping target:
- LED1 -> warm string cathode (`FL_W_N`);
- LED2 -> cool string cathode (`FL_C_N`);
- LED3..LED6 disabled/unpopulated;
- W+ and C+ -> boost `FL_VOUT`;
- A0 = GND -> 7-bit address 0x36;
- EN -> `FL_HWEN` from U601 P15;
- PWM held in an enabled/static state; brightness/color baseline controlled by I2C.

## Required support network

Before CAD release, add as one controlled ECO:
- 10 µH mainland inductor;
- external Schottky diode with VR above programmed OVP;
- >=4.7 µF input bulk;
- >=1 µF VDC decoupling;
- >=4.7 µF high-voltage output capacitor with effective capacitance verified at operating voltage;
- optional input RC per low-VIN application guidance;
- internal compensation baseline; COMP remains unpopulated unless bench stability requires external RC.

## J804 gate

Panel connector remains Hirose `FH34SRJ-6S-0.5SH(50)` candidate:
- 6 positions;
- 0.5 mm pitch;
- 1.0 mm height;
- 0.30 mm FPC;
- top-and-bottom contacts.

No mainland connector has proven exact mating/land-pattern equivalence. J804 therefore remains a foreign mechanical retention item.

CAD integration is blocked until the official Hirose land pattern is imported rather than manually approximated.

## Qualification

Still required:
- current clamp <=15 mA/string;
- OVP programmed for the FT01C string voltage rather than leaving 36 V default;
- shutdown leakage;
- color/brightness control;
- inductor current/thermal;
- switch-node ringing/EMI;
- audible noise;
- front-light uniformity.

Manufacturing release: false.
