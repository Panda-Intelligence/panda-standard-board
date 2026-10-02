# Split-C1 mechanical and sourcing follow-up

Date: 2026-10-02. Architecture: two PCBs, Core-C1 and Display-C1.
Project stage: PCB design only; the user confirmed no physical boards exist.
Status: engineering constraints and exact-part catalog mapping; manufacturing_release=false.

## Current result

Both native boards remain DRC/open/parity/ERC = 0/0/0/0.
The CAD includes 87 controlled mainland substitutions (Core58/Display29), local
U403 bypass C516, reviewed HCTL NTC/speaker lands, Sunlord power/EPD lands,
and XKB A2 six-pin dual-contact connectors. L402 is intentionally changed from
2.2uH to1uH for SGM41513; power routing and C402/R306 support changes are
predecessor-guarded. J803/J804 rotate180deg and shift -Y2.5mm to preserve all
signal world coordinates; entry reverses to -Y. H804 moves to(3,33), and SDA
bypasses the J804 support. Rule minima are not relaxed; the USB ECO removes three obsolete J201 exceptions.
XKB TS-1186E-B-B A1 side switches replace both ALPS parts with two original0.6x1.6mm lands and new signal/ground routes. C504 moves0.25mm to clear the courtyard; its nets/value remain unchanged. Maximum bare-part height1.6mm is taken from the side view; catalog H3.55 is actuator depth in the top view. Enclosure opening, force, travel and lifecycle remain unqualified.
Current CAD equals a deterministic fresh rebuild including these changes.
The current all-domestic audit covers156 populated system-BOM refs:148 mainland
manufacturer refs and8 foreign refs still requiring replacement. See
[SPLIT-C1-DOMESTICIZATION.md](SPLIT-C1-DOMESTICIZATION.md) for qualification
calculations and differences. The60pin HCTL pair retains the reviewed1.5mm
nominal mating transform; physical fit and mixed-family mating are not approved.

| Board | Present SMT library IDs | SMT refs still MPN-only | Manual/off-board |
|---|---:|---:|---:|
| Core-C1 | 111 / 118 | 7 | 1: Shiheng TH301, C394023 |
| Display-C1 | 36 / 37 | 1 | 0 |

The reviewed sourcing register now covers 94 refs, including manual TH301.
Exact current identities/evidence are in split-c1-sourcing-evidence.json and
split-c1-domestic-policy.json. Previously present IDs remain PREEXISTING_ID.
The old Hirose/Murata/Yageo/UNI-ROYAL/onsemi IDs are not current replacement IDs.
Core R615 is precisely FH RS-03K5231FT / C140082.

Builders pin the original connector wiring seed, apply checked predecessor ECOs,
then reviewed sourcing. They reject MPN/ID conflicts; policy audit rejects an
unreviewed identity or manufacturer-only relabel. The MUP topmount USB ECO removes
the old cutout/0.02mm edge blocker; both boards pass standard DFM. No stock is reserved.

## Supply readiness for the original seven SMT refs

The original seven-ref supply list is updated to current exact identities;
Coilcraft/Taiyo followups are retired. C301 is still foreign and blocked under
the all-mainland requirement. Four SGM2578SDYG/TR switches and every new connector
also require exact supply/packing and assembler acceptance. One Core plus one
Display needs the quantities below. For N pairs, usable placements are N times
the quantities; add assembler-approved attrition and tape leader/trailer. N is unset.

| Board / refs | Qty per pair | Current exact MPN / ID | Still needed |
|---|---:|---|---|
| Core C301 | 1 | Seiko CPH3225A / C6048128, still foreign | RTC/backup subsystem domestic redesign; current foreign part cannot be ordered |
| Core C506, C513 | 2 | HRE CGA0603X7R106K100JT / C22399626 | Actual stock, allocation and effective DC-bias capacitance |
| Core L402 | 1 | Sunlord MWSA0402S-1R0MTB01 / no confirmed ID | Exact B01 order/packing, code assignment and assembly acceptance; ordinary1R0MT forbidden |
| Core U902 | 1 | SGM62125AXG/TR / no confirmed ID | Exact A WLCSP15 code, quote/packing and assembly acceptance |
| Core U905 | 1 | SGM37601YTRL20G/TR / no confirmed ID | Exact TQFN20 code, packing/MSL handling;24pin not interchangeable |
| Display L1 | 1 | Sunlord SWPA3012S470MT / no confirmed ID | Exact code/packing and assembly acceptance |
| Core U402-U405 | 4 | SGM2578SDYG/TR / no confirmed ID | Exact SD WLCSP version, enabled-state RCB clarification and assembly acceptance |

Core L401 now has exact Sunlord MWSA0402S-R47MT/C6331050 tape identity. HCTL
HC-1.0-3PWT/C2845362 and2PWT/C2845361 require matching new housings/contacts;
old JST harnesses are not transferred. XKB X05A10H06G/C528032 requires dimensions
from A2 p2 dated2026-01-15; a catalog ID alone does not establish the supplied
revision. No stock count, quote, reservation, purchase or supplier message is
asserted. These identities/evidence are in split-c1-sourcing-evidence.json.
No live inventory or assembler acceptance is implied by a cached listing.
TH301 is manual/offboard Shiheng MF52D-103F3435-100/C394023,100mm AWG30 and
4mm-max tip; matching termination, thermal attachment and charge thresholds are open.

Primary paths: [Sunlord MWSA2025](https://atta.szlcsc.com/upload/public/pdf/source/20250613/CEE4AE5EC9F7EB97495A767C9ECB8960.pdf),
[Sunlord SWPA2024](https://atta.szlcsc.com/upload/public/pdf/source/20241120/5FB31A17AAA509171003FB8365AF70A5.pdf),
[SGM62125](https://www.sg-micro.com/product/SGM62125),
[SGM37601](https://www.sg-micro.com/product/SGM37601),
[SGMICRO authorized distributors](https://www.sg-micro.com/authorized-distributors).

For JLC consignment, an exact accepted C-code is required before shipping. If
missing, submit the exact manufacturer/MPN/package for engineering acceptance
and code assignment first. Then confirm usable tape/attrition quantity and
receipt in My Parts; select the owned stock separately for each board's assembly.
A distributor listing is not assembler acceptance. See the [official guide](https://jlcpcb.com/help/article/important-note-before-you-consign-the-part-to-jlcpcb)
and [using owned stock](https://jlcpcb.com/help/article/how-to-use-my-own-parts-for-pcb-assembly-order).
No consignment submission or stock purchase is part of this design-stage update.

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

J201 is now the mainland MUP U20405-01 topmount part, without posts. The right shell lands still intersect the Display projection:

| Pad center, native mm | Pad envelope, native mm |
|---|---|
| (43.32,61.8) | x=42.72..43.92; y=60.8..62.8 |
| (43.32,66.3) | x=42.72..43.92; y=65.25..67.35 |

[MUP Rev4 original drawing](https://atta.szlcsc.com/upload/public/pdf/source/20240223/861C7C148AA03685D8854DCE43F31033.pdf)
and the [exact official product](https://mupconn.com/product/usbc/3368.html) differ on nominal height (3.20mm drawing /3.26mm on-board page). Use3.46mm as a conservative design budget, not a certified mounted maximum. Nominal0.6mm shell legs do not establish solder protrusion/PCB-warp clearance. The new PCB has a straight edge, no midmount cutout and no J201 DRC exemptions; both boards pass independent standard DFM. Case aperture, plug, panel and maximum mounted-Z clearances remain open.

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

For a conservative rear envelope covering both PCBs:

T_outer = 0.8 + 1.98 + H_core_F
+ max(1.5 + 0.8 + H_display_F, H_core_B_outside_Display)
+ panel_clearance_and_adhesive + battery_clearance_and_insulation
+ front_wall + rear_wall + manufacturing_tolerance_reserve
+ T_battery_max + swelling_allowance.

Core back-side components outside the Display projection must also fit inside
the case. All unverified heights and final pack thickness stay null. The user-requested
X4 Pro comparison goal is recorded as5.95mm; the audit never turns a candidate cell dimension into a selected pack.

## Battery candidates and enclosure dimensions at the design stage

| Candidate | Published body / pack dimensions | Capacity | XY screening in the historical 64x60 region | Pending |
|---|---|---:|---|---|
| EEMB LP503450 | Bare-cell max52x34.5x5.3mm including tab-length envelope | 950mAh typical,900 minimum | Total slack12x25.5mm; body passes an illustrative1mm-per-side screen | Full protected pack, connector/NTC harness and swelling; runtime and peak-load budget |
| FP Battery LP505060 | Protected-pack length62+/-1mm; width50 and thickness5mm have no stated maximum tolerance;100mm leads | 1800mAh | Using63x50 leaves only1x10mm total; fails illustrative1mm-per-side X screen | Width/thickness maximums, lead folding, connector and swelling; runtime and load budget |

Sources: [EEMB product and linked drawing](https://www.eemb.com/product-145),
[FP manufacturer's drawing](https://www.fpbattery.com/wp-content/uploads/2024/04/fpbattery-505060-3.7V-1800mAh-Lithium-Polymer-Battery-Specification.pdf).
The two makers' model numbers are distinct procurement identities. EEMB is a
bare cell, not a ready protected battery pack. Neither candidate is selected.
The published charge/discharge limits are recorded for later charger/load
matching; EEMB additionally limits charging at0..20C to0.3C. Nominal capacity
alone does not establish runtime. No cell is added to the PCB BOM.

With the panel centered at Core(48,34) as an explicitly unverified study pose,
the two PCB outlines, nominal panel and current populated footprint envelopes
have a union105.33x68.775mm. The extra0.775mm includes J201's native envelope;
J501's envelope extends to x98.55mm. Illustrative1mm edge clearance plus1.5mm
wall on each side gives110.33x73.775mm, rounded111x74mm **XY only**.
This is a calculated study envelope, not a finished enclosure size. Panel/FPC
pose, USB plug and microSD travel, antenna, speaker, harness, bosses and
retention geometry may enlarge it. The X4 Pro5.95mm reference is now recorded; no enclosure thickness is signed off.

The audit exports current port/switch envelope coordinates and Core mounting
holes: H801(15,2),H802(81,2),H803(93,34),H804(3,33), all1.6mm NPTH for the
existing M1.2-clearance footprints. The Display has no dedicated mounting-hole
footprint. Provide insulating supports/retention; the HCTL pair must not be the
sole structural support. These dimensions do not approve a boss or cutout.

New closed-height screens are recorded separately: HCTL J302/J5023.2mm
conservative budget, MWSA L401/L4022.0mm max, SWPA L1 1.2mm max, XKB
J803/J8041.1mm max (open actuator nominal1.55mm). They do not replace body models
or FPC fold/connector insertion envelopes. J803/J804 entries now face-Y and H804
moves1mm toward-Y; enclosure bosses and FT01C folded tails must follow the new
native poses before a case drawing can be frozen. No physical clearance is approved.

## XTEINK X4 Pro reference and design consequences

The user requested this reference on2026-10-01. The [official product](https://www.xteink.com/products/xteink-x4-pro-pocket-ereader)
and [official FAQ](https://www.xteink.com/blogs/product/x4-pro-faq-specs-support)
publish **111x69x5.95mm**, **1100mAh**, touch/buttons and adjustable warm/cool
frontlight. The5.95mm is the complete device body thickness, not wall thickness
or the optional protective cover. The FAQ expressly gives no hours/days promise
or reproducible battery-life test conditions. Standard X4 or X3 runtime claims
must not be copied into the Pro requirement.

The mechanical input records5.95mm as a comparison goal and1100mAh as a capacity
baseline. Neither is a selected pack, a frozen case drawing or measured runtime.
The current two-board HCTL construction consumes5.08mm before the battery,
component heights, walls or allowances, leaving only **0.87mm for all remaining
terms**. This is an optimistic nominal remainder, not usable battery thickness.

| Existing candidate | Fixed stack plus published battery thickness | Basis | Result against5.95mm |
|---|---:|---|---|
| EEMB LP503450 | 10.38mm | 5.3mm bare-cell maximum; PCM/harness excluded | Exceeds goal before components/walls;950mAh typical also below1100mAh baseline |
| FP LP505060 | 10.08mm | 5mm pack nominal; thickness maximum unknown | Exceeds goal before components/walls;1800mAh is not proof of equivalent runtime |

These subtotals are dimension screens, not minimum measured case thicknesses.

Two exact-part height sources also sharpen the screen: Core U501 is the
**WROOM-1U** module,3.2mm per[Espressif v1.8 Table1-2](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf),
not the3.1mm WROOM-1. Display J2 is2.0mm per[Hirose's exact part](https://www.hirose.com/product/p/CL0586-0521-0-55).
Both native footprint envelopes intersect the centered panel/Core/Display
projection. Adding each height separately to5.08mm yields conservative local
section screens of **8.28mm at U501** and **7.08mm at J2**, before the battery,
case or mounting allowances. They are not summed together as though their XY
locations were identical. Footprint envelopes are not exact solid bodies, and
nominal catalog heights are not mounted maximums; no physical fit is approved.
Changing only battery thickness therefore does not resolve the current screen.

The existing illustrative XY study110.33x73.775mm also exceeds the reference's
69mm width by4.775mm; a native footprint bounding box is not a verified body.

Two reviewable architecture paths retain **two PCBs**:

- Preserve the present HCTL overlap construction: use the dimension formula to
  set an achievable case thickness after selecting the complete pack and
  obtaining maximum component/USB/FPC dimensions. The studied5mm-class cells
  cannot support a5.95mm case in this construction.
- Pursue a5.95mm body: perform a mechanical/interconnect ECO before rerouting.
  Investigate non-overlapping PCB/battery regions, smaller board footprints and
  a lower-profile interconnect with independent Display retention. Freeze a
  complete section using supplier maximums, swelling, walls and FPC bend space
  first. Merely changing the cell capacity or HCTL gap is insufficient; no
  unverified thin battery or FPC connector is selected by this update.

For runtime sensitivity only, assume1100mAh and an illustrative80% usable charge
allowance (880mAh). Average **battery-terminal** draw10/20/40/80mA gives88/44/22/11h
respectively. These are calculations, not X4 Pro specifications or Panda
measurements. Converter losses are already included in measured battery draw;
3.3V rail current cannot be inserted into this formula as battery current.
The80% allowance itself needs validation for the selected pack and cutoff.

Q12 now includes frontlight-off, cool, warm, mixed and sync/sleep workloads,
whole-battery charge/energy logging, optical measurements and a matched X4 Pro
comparison. Proposed common settings are25+/-2C,30s/page and one full refresh
per10pages; they are planned test conditions, not the reference's official
conditions. Match actual luminance, document and wireless schedule, record both
firmwares and battery health, and discharge only to normal protected shutdown.
Numeric runtime limits remain unapproved until a reliable reference comparison
and product budget are available. No sample or measurement is registered.

## Future two-board EVT

qualification/c4d-evt now plans Q04-Q14. Q13 isolates Display rails, L1/Q1/D1-D3
stress, SPI/BUSY timing and actual panel refresh. Q14 covers both serials, all60
contacts,1.5mm gap, J201 clearance, independent Display support, full pack/FPC
fit and startup/reset/sleep/shutdown of the mated pair. All eleven physical
items are NOT_RUN because neither board has been assembled. CAD or the old
Murphy/development board cannot produce a physical PASS for these designs.
The qualification verifier requires both PCB/BOM identities, both board serials,
required operating states and instrument/evidence records before measurement
results can count. See the qualification README for staged bring-up.

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

The X4 Pro capacity/thickness reference is now recorded. Inputs still needed:
a selected complete battery pack, an achievable two-board mechanical section
and approved numeric runtime limits, maximum FT01C flex drawing and component heights,
USB midmount maximum Z and enclosure supports. Physical verification is a
future step after sample assembly.
manufacturing_release stays false. Historical integrated C4D-20 and routing141
mechanical scenes do not override the split candidates. packaging/ is untouched.