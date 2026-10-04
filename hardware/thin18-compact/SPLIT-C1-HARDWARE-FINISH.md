# Split-C1 hardware finish — prototype source

This is the user's selected routed Split-C1, NOT Thin7/portrait-R2. Core remains
96 x 68 mm / four copper layers; Display remains 45 x 36 mm / two layers; both
are 0.8 mm. The ESP32-S3-WROOM-1U-N16R8 and HCTL 60-pin mating pair are unchanged.

## Electrical corrections

The former direct XL9535-to-charger BQ_CE connection is replaced by a default-off
hardware authorization circuit. R607 still pulls the expander request low; its
net is now CHG_REQUEST. R932 adds a 10k pulldown alongside the original100k.

```
SGM41513_REGN -- R930100k -- CHG_nCE -- Q907.D
                                       Q907.S -- Q908.D
CHG_REQUEST --------------------------- Q907.G   Q908.S -- GND
FL_HWEN ---------------------------------------- Q908.G
```

Q907/Q908 are the exact existing JSM NX3008NBK,215-JSM/C53113911: pin1=G,
pin2=D,pin3=S. They switch only the low-current nCE logic node, NOT the battery
or system power path. The pullup uses the charger's REGN supply, available
before downstream AON startup. No5V node is connected to an ESP/XL GPIO.

| Expander P05 request | Direct permit | nCE sink authorized | Frontlight EN |
|---|---|---|---|
| Low or high impedance | Low or high impedance | No | Low |
| Low | High | No | High |
| High | Low | No | Low |
| High | High | Yes | High |

An authorized sink is not by itself charging: charge configuration, battery,
NTC, source and other charger conditions still apply. Likewise EN high does not
permit LED operation until PWM and verified frontlight registers are correct.

GPIO2/module pad38 now drives HW_ARM_GPIO through R9311.2k to FL_HWEN. This
bypasses I2C and the expander. R93310k parallels the existing R601100k pulldown.
XL9535 P15/pad18 is explicitly unused/input; P16 still controls PWM. No octal
PSRAM or strapping pin is repurposed. Pulling native GPIO2 low disables driver
EN and the second charger-authorizing MOS even when I2C is unresponsive.

TP19, B.Cu at(58,17)mm, is copper-only FORCE-LOW test access, excluded from
BOM/CPL. Ground it to inhibit frontlight and charging; do not inject voltage.
R931 limits opposing GPIO current to approximately3.03mA at3.6V with its1%
low-resistance corner. The pad can be used by the bring-up fixture before any
unqualified application firmware is run.

## Parts and placement

Six additional populated parts:Q907,Q908,R930,R931,R932,R933. All use exact
already-reviewed mainland manufacturer/MPN/catalog identities. No new unmapped
SKU is introduced. Expected system population is162 refs (Core125,Display37),
including CoreC301/TH301 manual-or-offboard. Core123SMT;Display37SMT. The17
board-level IC/module refs remain unchanged; the two new devices are discrete
MOSFETs. Seven older SMT positions still require exact supply/assembly acceptance:
U402-U405,U902,U905,U906. A catalog code is not a reservation or supplier receipt.

Only existing U501/U601/U901 pin connections and R601/R607 descriptions change;
existing component positions are untouched. All Display native files and Core
outline, layers and design rules remain unchanged. New copper is restricted to
the reviewed enable/REGN/ground paths; the former dead charger escape is removed.
The exact route delta and new poses are frozen in split-c1-hardware-finish-layout.json.

## Validation and fabrication

Run from repository root:

```
python3 hardware/thin18-compact/release_split_c1.py --target split-c1
```

The command verifies current AND reconstructed native CAD, the independent
pin/variant/land checks,60-pin interconnect, BOM/CPL identities, mechanical XY
screen and both bare-board DFM checks. Use its current generated source-bound
reports, not a hidden routing trial or an old ZIP. The output is
production/Panda-Split-C1-JLC-Prototype.zip, with individual Core/Display Gerber
and separate plated/non-plated drill files, assembly views and BOM/CPL.

## Explicit physical and firmware boundaries

This closes the two identified static hardware defects: autonomous default-low
nCE wiring and an exclusively-I2C frontlight shutdown path. It is not a claim of
physical electrical qualification. Test REGN/nCE during batteryless and battery
startup, GPIO low/high/Hi-Z, partial-power, reset and bus-loss before qualified
battery charging. Datasheet leakage/threshold calculations are screening values
at stated conditions, not universal temperature/ramp guarantees. In particular,
JSM gate leakage is specified up to10uA, which is why the stronger10k pulldowns
were added rather than relying solely on100k. Verify enable HIGH/LOW margins
and physical current at the actual AON/temperature corners.

The direct GPIO is NOT an autonomous watchdog. CPU/GPIO retained-high failure
still needs TP19 grounded or power removed. The prototype includes that manual
shutdown route; it does not silently claim self-detection of arbitrary CPU faults.

Old firmware is incompatible with this board: P05 is now active-high request,
not active-low nCE; P15 must stay input; native GPIO2 defaults LOW. The minimal
host-controller binding was updated to require direct GPIO callbacks and to
keep CHG_REQUEST LOW. No target firmware was flashed or physically qualified.

Physical USB/current/charging/NTC, magnetics/thermal, RTC retention, panel/RF,
battery/enclosure and real supplier/assembly acceptance remain prototype tests.
manufacturing_release=false and assembly_order_ready=false are intentionally
retained. Bare-board CAM review does not require pretending these tests ran.
