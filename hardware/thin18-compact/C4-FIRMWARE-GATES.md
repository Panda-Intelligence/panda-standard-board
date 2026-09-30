# Thin18 Compact — C4 firmware migration gates

Date: 2026-09-29

This audit checks whether the proposed mainland hardware substitutions are blocked by existing Panda OS dependencies.

## QMI8658A

Repository findings:

- Panda OS already contains QMI8658 probe candidates qmi8658LowCandidate() / qmi8658HighCandidate() used by the s37uc board family.
- No Murphy-specific code was found that depends on LSM6DSO32X ±32 g, MLC, FSM, or sensor-hub features.
- Existing motion support is probe/axis oriented rather than tightly coupled to an LSM6DSO32X register implementation.

Conclusion: QMI8658A is firmware-feasible. A real QMI8658 device driver still needs initialization, sample read, FIFO/interrupt handling if used, orientation mapping and calibration tests. The ±16 g ceiling remains a product requirement gate, not a discovered firmware blocker.

## AXP2101

Panda OS currently exposes generic board-level fuel-gauge and charger types, but only BQ27220/BQ25896 are implemented in the existing type enum/driver path. No AXP2101 driver is present.

Required work:

- add AXP2101 PMIC type and driver;
- charger state/fault/USB presence mapping;
- battery voltage/current/SOC/e-gauge mapping;
- NTC and thermal fault handling;
- ship/power-off sequence;
- IRQ handling;
- safe startup defaults before firmware initialization.

Conclusion: firmware work is required but structurally contained. The existing Power/board abstraction does not force the old BQ25628/BQ27427 implementation.

## Passive USB-C sink

No product feature dependency was found that requires USB-PD or Type-C current-role negotiation.

For the C4 baseline, firmware may remove TUSB320 attach-state handling if the final product is fixed as USB2 device, 5 V sink only, no PD/PPS, and conservative charger input-current policy. USB insertion can instead be sourced from PMIC VBUS/IRQ state.

## Audio

Panda OS already models audio capabilities by board and supports I2S-based board implementations. The existing type enum does not name NS4168, but a direct-I2S amplifier does not require a codec control bus.

Required work:

- define the compact board playback path;
- set the NS4168-compatible I2S format/channel behavior;
- control the switched audio supply;
- add mute/pop sequencing tests.

Conclusion: NS4168 is firmware-feasible for a playback-only SKU. ES8311 + NS4150B remains a separate voice/capture SKU.

## RTC

Current generic RTC enum contains PCF8563. BM8563 is PCF8563-class but must not be assumed register-identical without testing.

Required work:

- confirm register compatibility;
- alarm/interrupt behavior;
- oscillator/load-cap assumptions;
- century/leap-year handling;
- backup-current and startup tests.

## XL9535

XL9535 retains the TCA9535-class 16-bit expander architecture.

Required regression:

- address;
- power-on input defaults;
- configuration/output/polarity/input register behavior;
- active-low open-drain INT semantics;
- brownout / partial-power behavior.

The C4A CAD candidate is topology-identical, so this is a firmware/device-behavior regression rather than a board-software architecture change.

## SGM37601 front light

C4D-10B requires a fail-closed startup sequence because SGM37601 reset defaults are 20 mA and 36 V OVP, above the FT01C 15 mA/string contract. Firmware must keep FL_HWEN/FL_PWM low, program 14.5 mA (`0x56`), 18 V OVP/internal compensation (`0xA1`) and 1 MHz/PFM (`0x2B`), then assert PWM. Shutdown must deassert PWM before HWEN. Address 0x36 has no documented conflict in the current compact I2C map.
