# C301 round plated-hole manufacturing ECO

## Reason and exact change

The previous C301 1.8x1.4mm plated oval slots had a length/width ratio below the
fabricator's published2:1 guidance. Merely obtaining KiCad0DRC did not resolve
that manufacturing issue. Enlarged-slot trials interfered with existing inner
routing and were not adopted.

The accepted geometry instead uses **two1.9mm nominal finished round PTHs with
2.3mm round copper lands**, preserving C301's position(59.4,43.5),20mm pin pitch,
positive pad1RTC_VBACKUP and negative pad2GND. The nominal annular ring is0.20mm.
The exact KAMCAP SE-5R5-D105VYH3C/C2894294 remains unchanged. These are reviewed
engineering lands, not a claim that the manufacturer recommends this PCB pattern.

All track/via objects and every other footprint remain unchanged. The body
courtyard,cap polarity mark,board outlines,layer stack and design rules stay.
Only C301 embedded/library lands,drills,description and refilled copper zones
change. `build_core_c1_split.py` applies `_split_c1_cap_drill_eco.py` after the
prior electrical ECOs,so immutable-baseline replay remains reproducible.

## Insertion-envelope screen

KAMCAP2020.6 specification p4 gives pitch20+/-0.5mm,lead width1.0+/-0.1mm and
thickness0.20+/-0.05mm. The JLCPCB capability page gives through-hole lower
size tolerance-0.08mm and hole-position tolerance+/-0.075mm. Using these as
explicit fabrication assumptions,and centering the capacitor between the two
actual hole centers:

- Lead circumscribed radius: hypot(1.1/2,0.25/2).
- Conservative per-lead center offset: hypot(0.5/2+0.075,0.075).
- Minimum assumed finished-hole radius: (1.9-0.08)/2=0.91mm.
- Calculated radial margin is positive; `verify_split_c1_cap_drill.py` records
  the exact result and rejects an undersized nominal hole or reduced annular ring.

This screen is not an insertion test or solder-joint qualification. Actual lot
geometry,finished-hole/plating tolerance,lead coplanarity,solder fill and body
support must be checked at first assembly. The part is still manually installed
after SMT; trim and insulate rear leads as specified by the existing handoff.
No external force or permanent lead bending is assumed by the calculation.

## Export and verification

The native checker verifies circular shape,1.9mm drill,2.3mm land,20mm pitch,
pose,MPN,polarity and rejects obsolete slot geometry. The exported Excellon audit
requires1.9mm ROUND PTH hits at(49.4,43.5) and(69.4,43.5),not G85 slots.
Remaining Core USB slots are retained. Current and reconstructed native boards
must still pass DRC/open/parity/ERC0/0/0/0 before package generation.

## Primary references

KAMCAP exact model specification2020.6,p4 dimensioned drawing and tolerances:
https://atta.szlcsc.com/upload/public/pdf/source/20210914/37A5D1176C23A52D8BA2A343DB47BCB6.pdf

Fabricator capability,checked2026-10-04:plated-slot2:1 guidance,hole-size and
position tolerances,and multilayer1oz annular-ring recommendation0.20mm:
https://jlcpcb.com/capabilities/pcb-capabilities

No CAM acceptance,actual supply,physical EVT or manufacturing release is implied.
