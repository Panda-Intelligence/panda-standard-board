# Thin18 Compact — C4D-6 domestic audio

Date: 2026-09-29

C4D-6 replaces the assembled MAX98357A audio path with mainland Nsiway NS4168 / LCSC C910588.

Implemented:
- U904 NS4168 on ESOP-8 exposed-pad footprint;
- existing VSYS_AUDIO switched domain retained;
- existing I2S_BCLK / I2S_LRCLK / I2S_DIN retained;
- existing SPK_P / SPK_N and J502 speaker connector retained;
- old U502 and R503-R506 remain schematic DNP references only and are removed from PCB population.

Native checks:
- ERC 0
- DRC 0
- schematic parity 0
- open 399 (compact board still intentionally unrouted)

Firmware gate:
- NS4168 channel selection is controlled by CTRL=VSYS_AUDIO in this EVT candidate;
- firmware must ensure valid right-channel content, or duplicate mono content to both I2S channels.

Physical qualification remains open: output power, idle current, pop/click, polarity, thermal and EMI.
