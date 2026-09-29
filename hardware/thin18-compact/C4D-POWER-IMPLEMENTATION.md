# Thin18 Compact — C4D power implementation

Date: 2026-09-29

PR: #4

C4D turns the C4 documentary architecture into pin-level CAD inputs. The implementation is deliberately split so each electrical delta is independently reviewable.

## Exact variant correction

The selected charger is **SGM41513YTQF24G/TR**, the non-D variant.

It has:

- VAC
- PSEL
- nPG

and **does not have D+/D- pins**.

Therefore C4D does not claim BC1.2 auto-detection. PSEL-high is the fail-safe 500 mA baseline. Any higher input-current programming requires a separately qualified source-capability policy.

## C4D-1 — charger / NVDC

Target:

`BQ25628ERYKR -> SGM41513YTQF24G/TR`

The old product-level nets are intentionally retained where semantics match:

- VBUS_USB
- PACK_BAT
- VSYS_RAW
- I2C_SCL / I2C_SDA
- BQ_PG
- BQ_STAT
- BQ_INT
- BQ_CE
- BQ_TS
- BQ_QON

The internal switch/boost nets are replaced by SGM41513-specific names.

Existing 47 nF bootstrap, 1 µF VBUS, 10 µF PMID, 4.7 µF REGN, 10 µF BAT, and SYS bulk values are structurally reusable, subject to final exact-voltage/DC-bias checks.

## C4D-2 — AON buck-boost

Target:

`TPS63802DLA -> SGM62125AXG/TR`

SGM62125's recommended 2.2 MHz application is unusually compatible with the current power block:

- 0.47 µH inductor
- 10 µF input
- 2 × 22 µF output

The existing L401/C401/C402/C403 roles are therefore retained as layout resources, but the inductor's Isat/DCR must be requalified.

ADDR is planned high for the 3.4 V start-up state / I²C address 0x76. Firmware then programs 3.3 V. Every always-on load must be checked for 3.4 V start-up tolerance before this candidate can advance.

## C4D-3 — fuel gauge

Target:

`BQ27427YZFR -> CW2215BAAC`

CW2215B is selected for its 5 µA active current and current sensing. The public datasheet obtained in this pass proves the logical interface and WLCSP-9 package, but does not expose a trustworthy ball-to-function map.

**Fail-closed rule:** no CW2215B KiCad symbol/footprint will be generated from guesses. C4D-3 remains blocked until the authoritative ball map or EasyEDA source model is captured.

## C4D-4 — USB-C simplification

Remove:

- U202 TUSB320
- U203 TPS70933
- U204 SN74AUP2G07
- U205 TPS3700

Use:

- CC1 5.1 kΩ Rd
- CC2 5.1 kΩ Rd
- ESP32-S3 native D+/D-
- domestic low-cap ESD after exact selection
- SGM41513 nPG/nINT/register state for VBUS/charger status

The 500 mA default input-current limit is part of the hardware safety contract.

## Implementation order

1. generate exact SGM41513 symbol/footprint and replace U201;
2. fresh ERC + parity + semantic netlist-delta review;
3. generate exact SGM62125 symbol/footprint and replace U401;
4. validate 3.4 V start-up compatibility and I²C address map;
5. obtain CW2215B authoritative ball map, then replace U301;
6. remove U202-U205 and add passive CC resistors;
7. reallocate XL9535 pins freed by old CC status;
8. only then proceed to placement and final routing.

No manufacturing release is implied by this contract.
