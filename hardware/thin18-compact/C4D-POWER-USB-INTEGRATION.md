# Thin18 Compact — C4D power / USB integration

Date: 2026-09-29

Status: engineering integration input; not manufacturing release.

## Corrected charger choice

C4D uses the **non-D SGM41513YTQF24G/TR**.

Important variant distinction:

- SGM41513 pin 2 = PSEL and pin 3 = nPG;
- SGM41513A/D pin 2/3 = D+/D- and can perform BC1.2-style source detection.

The compact baseline deliberately chooses the non-D part so the charger does **not** attach to the USB D+/D- pair used by ESP32-S3 native USB.

For the first EVT baseline:
- PSEL is held high;
- autonomous input-current limit starts at 500 mA;
- firmware may program IINDPM after boot if a later source-capability policy is added;
- no claim is made that passive Type-C Rd detects 1.5 A or 3 A advertised source current.

This is slower than an aggressive 1.5/3 A charge policy but is deterministic and safe for the simplified USB-C architecture.

## USB C4D delta

Current components targeted for removal:

- U202 TUSB320LIRWBR
- U203 TPS70933DBVR
- U204 SN74AUP2G07DCKR
- U205 TPS3700DDCR
- R205 VBUS_DET divider feed
- R208 legacy CC-domain bias
- R209 legacy VBUS sensing helper

Repurpose:

- R206 -> 5.1 kΩ Rd from USB_CC1 to GND
- R207 -> 5.1 kΩ Rd from USB_CC2 to GND

Consequences:

- U601 P16 / P17 are released because CC_OUT1_AON / CC_OUT2_AON disappear;
- VBUS-good / attach-state moves to SGM41513 nPG / nINT and register state;
- ESP32-S3 retains exclusive use of USB_DP / USB_DM.

## SGM41513 non-D pin contract

TQFN-4×4-24L:

1. VAC — connect to VBUS for input-voltage sense
2. PSEL — high = 500 mA autonomous input-current limit; low = 2.4 A
3. nPG — open-drain input-power-good
4. STAT — open-drain charge state
5. SCL
6. SDA
7. nINT — open-drain, active-low status/fault pulse
8. NC
9. nCE — active-low charge enable
10. NC
11. TS — battery NTC
12. nQON — ship exit / system reset control
13,14. BAT
15,16. SYS
17,18. GND
19,20. SW
21. BTST
22. REGN
23. PMID
24. VBUS
EP. GND thermal pad

The non-D part supports I2C at address 0x1A and retains NVDC power-path / ship-mode behavior.

## Placement feasibility

The 96 × 68 mm placement already has enough area after the incumbent power components are removed.

C4D reserves:

- SGM41513 package/courtyard envelope near old U201/L402
- CW2215B envelope near old U301
- SGM62125 envelope near old U401/L401

The reservation builder excludes only the incumbent components that the C4 architecture removes and checks all remaining top-side footprint bounding boxes with 0.5 mm clearance.

## Integration gates

Before electrical replacement of the C4C schematic:

1. create exact project-local symbols and footprints for SGM41513, CW2215B and SGM62125;
2. transcribe CW2215B and SGM62125 ball maps from manufacturer-controlled documentation;
3. freeze SGM41513 charge-current / regulation / NTC / safety-timer settings;
4. freeze CW2215B sense-resistor/profile data;
5. prove every 3V3_AON load tolerates SGM62125 3.4 V startup;
6. replace the USB sheet and root-sheet status nets in one atomic ECO;
7. run ERC, parity and semantic netlist-delta review before any routing.
