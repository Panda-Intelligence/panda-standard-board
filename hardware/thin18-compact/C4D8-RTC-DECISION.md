# Thin18 Compact — C4D-8 RTC domesticization decision

Date: 2026-09-29

Status: mainland RTC candidate identified, substitution blocked by backup-retention architecture.

## Candidate

GATEMODE `BM8563EMA` / LCSC C269878:
- I2C RTC/calendar;
- MSOP-8;
- 1.2–5.5 V supply;
- external 32.768 kHz crystal;
- alarm/interrupt and programmable clock output.

It is a credible low-cost mainland PCF8563-class RTC candidate.

## Why it is not applied

The current RV-3028 design has a dedicated backup pin:
- U302 VDD -> 3V3_AON;
- U302 VBACKUP -> RTC_VBACKUP;
- C301 11 mF / 3.3 V backup capacitor -> RTC_VBACKUP.

BM8563EMA has only one VDD rail and no dedicated VBACKUP input.

A direct substitution would therefore lose the current backup-domain contract unless a new charge/isolation/ORing topology is designed.

The compact product currently requires RTC retention through low-power / ship-state transitions. That behavior is more important than maximizing mainland-part percentage.

## Decision

- retain RV-3028-C7 for the current C4 EVT baseline;
- mark BM8563EMA as a redesign candidate, not a drop-in;
- do not reuse C301 directly on BM8563 VDD without a validated charging/isolation network;
- revisit only if a mainland integrated-crystal / backup-input RTC is found, or if a separate backup-domain circuit is intentionally designed.

Any external-crystal candidate must also satisfy the RTC ESR/load-capacitance requirement; a nominally matching 32.768 kHz crystal is not sufficient.

Manufacturing release: false.
