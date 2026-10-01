# Split-C1 mechanical and sourcing follow-up

Date: 2026-10-01. CAD baseline: d80c6aa.
Status: engineering constraints and exact-part catalog mapping; manufacturing_release=false.

## Current result

Both native boards remain DRC/open/parity/ERC = 0/0/0/0.
Only procurement properties changed in PCB/schematics. Copper, footprint poses,
pad geometry and electrical nets are checked against the baseline.
Reviewed exact-part IDs now cover 11 additional Core refs and 23 Display refs.
Library IDs identify parts; stock, packing, purchased quantity and assembly
availability still require order-time confirmation.

| Board | Present library IDs | SMT refs still MPN-only | Manual/off-board |
|---|---:|---:|---:|
| Core-C1 | 111 | 6 | 1 |
| Display-C1 | 36 | 1 | 0 |

The sourcing CSV includes evidence URLs for this review. Previously present IDs
remain labeled PREEXISTING_ID rather than being newly certified by this review.

## New exact-part mappings

| Board | Refs | Retained MPN | Library ID | Source |
|---|---|---|---|---|
| Core-C1 | D201 | TPD4E05U06DQAR | C138714 | [Catalog](https://www.lcsc.com/product-detail/C138714.html) |
| Core-C1 | D202 | TPD1E10B06DPYR | C48260 | [Catalog](https://www.lcsc.com/product-detail/C48260.html) |
| Core-C1 | J201 | USB4500-03-0-A | C5354966 | [Catalog](https://www.lcsc.com/product-detail/C5354966.html) |
| Core-C1 | J301 | DF58-2P-1.2V(21) | C597951 | [Catalog](https://www.lcsc.com/product-detail/C597951.html) |
| Core-C1 | J501 | 104031-0811 | C585350 | [Catalog](https://www.lcsc.com/product-detail/C585350.html) |
| Core-C1 | J601 | DF40C-60DS-0.4V(58) | C2880473 | [Catalog](https://jlcpcb.com/partdetail/HIROSE-DF40C_60DS_0_4V_58/C2880473) |
| Core-C1 | R306 | FRM121WFR010TM | C7467248 | [Catalog](https://www.lcsc.com/product-detail/C7467248.html) |
| Core-C1 | R903, R904 | FRC0603F1000TS | C2906981 | [Catalog](https://www.lcsc.com/product-detail/C2906981.html) |
| Core-C1 | U501 | ESP32-S3-WROOM-1U-N16R8 | C3013946 | [Catalog](https://www.lcsc.com/product-detail/C3013946.html) |
| Core-C1 | U903 | CW2217BAAD | C5203993 | [Catalog](https://jlcpcb.com/partdetail/Cellwise-CW2217BAAD/C5203993) |
| Display-C1 | C4, C5, C6, C7, C8, C9 | GRM21BR61E475KA12L | C77077 | [Catalog](https://www.lcsc.com/product-detail/C77077.html) |
| Display-C1 | C10 | GRM21BR71E105KA99L | C77080 | [Catalog](https://www.lcsc.com/product-detail/C77080.html) |
| Display-C1 | C11, C12, C13 | GRM188R71E104KA01D | C77050 | [Catalog](https://www.lcsc.com/product-detail/C77050.html) |
| Display-C1 | D1, D2, D3 | MBR0530T1G | C82046 | [Catalog](https://www.lcsc.com/product-detail/C82046.html) |
| Display-C1 | J1 | DF40C-60DP-0.4V(51) | C424647 | [Catalog](https://www.lcsc.com/product-detail/C424647.html) |
| Display-C1 | J2 | FH12-24S-0.5SH(55) | C202112 | [Catalog](https://www.lcsc.com/product-detail/C202112.html) |
| Display-C1 | Q1 | NX3008NBK,215 | C179399 | [Catalog](https://www.lcsc.com/product-detail/C179399.html) |
| Display-C1 | R1, R2, R3, R4, R5 | RC0402FR-0722RL | C114765 | [Catalog](https://www.lcsc.com/product-detail/C114765.html) |
| Display-C1 | R6 | RC0402FR-07100RL | C106232 | [Catalog](https://www.lcsc.com/product-detail/C106232.html) |
| Display-C1 | R13 | RC0603FR-072R2L | C112307 | [Catalog](https://www.lcsc.com/product-detail/C112307.html) |

No manufacturer, electrical rating, package or mating-family substitution was made.
Molex 104031-0811 and catalog 1040310811 are the same formatted ordering number.
The Core builder now clears the Display plug's library ID when constructing the
different DF40 socket, then applies the socket's independently reviewed ID.
Builders replay these mappings from split-c1-sourcing-evidence.json and reject
unexpected manufacturer/MPN/ID conflicts.

Unresolved SMT supply:

- Core-C1 C301: CPH3225A. Confirm exact packing and consignment or library ID.
- Core-C1 C506, C513: 0603B106K100NT. Confirm exact Fenghua X7R 10uF/10V orderable part and library ID; do not substitute dielectric.
- Core-C1 L402: XGL4015-222MEC. Confirm supplier/packing and JLC consignment.
- Core-C1 U902: SGM62125AXG/TR. Manufacturer-listed exact WLCSP variant; confirm supply or consignment.
- Core-C1 U905: SGM37601YTRL20G/TR. Manufacturer-listed exact TQFN20 variant; confirm supply or consignment.
- Display-C1 L1: LSXNE3030KKT470MN. The [manufacturer page](https://ds.yuden.co.jp/TYCOMPAS/or/detail?pn=LSXNE3030KKT470MN&u=M) lists Mass Production (Preferred) and maximum body height 1.0 mm; confirm stock, packing and library ID/consignment. UTY-DN25-02D lists this part as a suggested alternative for older NR/LSXBD models, rather than an EOL part.

TH301 remains manual/off-board. Its attachment and battery NTC harness are
physical assembly work. For the seven unmapped SMT refs, the retained exact
MPN is the procurement identity; use supplier-confirmed consignment if no exact
JLC library entry is confirmed. Purchase quantity, reel/cut-tape packing, lot
traceability and assembly-vendor acceptance remain pending. A search miss does
not prove a part is unavailable. No purchase or supplier message was sent.

## Native mechanical XY screening

Core B.Cu is the z=0 datum. The Display transform remains
x_core=x_display+38, y_core=66-y_display, z_core=-1.5-z_display.

| Plane | z in Core B.Cu coordinates |
|---|---:|
| Core F.Cu | +0.8 mm |
| Core B.Cu | 0 mm |
| Display B.Cu | -1.5 mm |
| Display F.Cu | -2.3 mm |

The gap-facing populated footprint envelopes are only J601 on Core and J1 on
Display. Other Core B.Cu SMT footprints lie outside the Display rectangle
x=38..83, y=30..66. This is a conservative native footprint-bounding-box screen,
not a body-model collision or maximum-height qualification.

J201 has two plated shell-pad envelopes intersecting the Display projection:

| Pad center, native mm | Pad envelope, native mm |
|---|---|
| (44.62, 62.4) | x=44.12..45.12; y=61.5..63.3 |
| (44.62, 66.4) | x=44.12..45.12; y=65.3..67.5 |

GCT publishes 0.8-mm offset and 0.7-mm shell-stake length for USB4500
([official product page](https://gct.co/connector/usb4500)). Those values alone
do not establish below-Core-B protrusion including solder, mounting tolerance and
PCB warp. The official drawing download was unavailable in this session; retain
the J201 body/stake/solder Z-clearance gate.

## Battery layering and Z budget

The inherited battery rectangle x=21..85, y=4..64 is a planning envelope, not a
released battery cavity or a current supplier drawing. Its intersection with the
Display rectangle is x=38..83, y=30..64 = **1530 mm²**, and it intersects the
occupied J601/J1 mating region. The full rectangle cannot be placed in the
interboard gap.

The recorded construction proposal puts the panel outside Core F.Cu components,
and the battery outside the outward Display F.Cu components. The proposal needs
FPC pose, maximum component heights, insulation, supports and physical fit
confirmation before freezing.

Known nominal thickness terms total **5.08 mm**:
0.8 Core + 1.5 gap + 0.8 Display + 1.98 FT01C panel.
This excludes both outward component-height envelopes, battery, swelling,
adhesive/insulation, walls, clearances and tolerances. The panel's 1.98 mm is the
C2 nominal integration input; supplier maximum tolerance and XY pose remain open.

For this conservative layered proposal:

T_outer = 5.08 + H_core_F + H_display_F
+ panel_clearance_and_adhesive + battery_clearance_and_insulation
+ front_wall + rear_wall + manufacturing_tolerance_reserve
+ T_battery_max + swelling_allowance.

All unknowns remain null in split-c1-mechanical-inputs.json. The audit calculates
a battery-plus-swelling thickness budget only after every term is supplied;
it does not invent a battery model or assume an outer-case thickness. Even a
passing numeric budget leaves physical verification false.

## Re-run and package checks

1. Run validate_split_c1.py with regular Python; it rebuilds both boards and runs verify_split_c1.py with KiCad Python.
2. Run audit_split_c1_mechanical.py with the same interpreter.
3. Export each board with export_production.py; run export_jlc.py.
4. Run freeze_split_c1_release.py.

The single entry point `python3 hardware/thin18-compact/release_split_c1.py`
runs all four stages. See SPLIT-C1-CAD-PRODUCTION-CLOSURE.md for runtime
configuration and retrieval of the immutable Git replay baseline.
Exported packages are generated and ignored; they are not duplicated in Git.

Fresh rebuilds use build_core_c1_split.py and build_display_c1_production.py with
a new --output directory. Existing candidates are preserved.

The freeze step checks PCB/interface/input hashes and copies the sourcing evidence,
mechanical inputs and audit into each package's engineering/ directory. These
files are covered by the package SHA256SUMS and combined release record.
A stale mechanical audit blocks package freezing.

Actual battery dimensions/swelling, FT01C FPC geometry, USB midmount clearance,
enclosure support geometry and calibrated electrical/thermal EVT remain open.
manufacturing_release stays false. Historical integrated C4D-20 and routing141
mechanical scenes do not override the split candidates. packaging/ is untouched.
