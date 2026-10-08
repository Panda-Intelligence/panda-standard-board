# 2026-10-08 electrical-connectivity checkpoint — NOT an order release

Core and Display now both rebuild with native DRC/open/parity/ERC **0/0/0/0**.
The earlier two/four airwire counts below are historical. The current reviewed
source is `seven_mm_core_routing.json` plus the existing Display route plan;
run `build_seven_mm_candidate.py --output /new/ignored-or-external/directory`.
The checked copy is `.work/seven-mm-release-close-20261008/rebuilt-thermal-final/`.

Display SPI clock EPD_D0 moved from unused-after-ECO GPIO38/package43 to the
previously unused GPIO21/package27. All60 FFC positions and every other MCU net
are preserved. USB clamp D201 is now at(30.5,102.75),90deg, near bottom USB.
`seven_mm_host_gpio.json`, `verify_seven_mm_host_gpio.py` and
`firmware/seven_mm/board_pins.h` define/check the new mapping; existing target
firmware must be integrated and tested before use. GPIO2 inhibit, GPIO19/20 USB,
strapping pins,16MB Flash and the reserved8MB PSRAM interface were not reassigned.

Native ground vias within exposed pads: **U501=9, U901=5**. These are real
through-vias connected to In1 GND,not edited counts. Local UART/I2C/control
reroutes preserve the full netlist. No design rule or exclusion was relaxed.
The rebuild has3874 Core segments/443 vias. Both exact source plans are bound to
native schematic/project/custom-rule/library evidence and refreshed zone filling.

Checks:34 allocation tests,21 route-evidence tests,8 port tests,12 prototype-review
negative controls; GPIO/interconnect/RTC checks reject9/3/5 invalid cases. Native
copper containment and nominal connector direction checks pass on the rebuilt copy.
The allocation JSON's qualification flags are NOT a substitute for those actual
native reports and must not be used alone to infer an order release.

**Still not ready to order:** the connected baseline needs power-path, switching
loop, crystal/Flash, USB differential and SD timing/impedance review, exact supply,
and mechanical maximum-envelope closure. `audit_seven_mm_prototype.py` reports
these openly and returns2. Wider isolated segments alone cannot clear the audit.
The original22mm/Split-C1 orderpack and obsolete visual model remain blocked.

An isolated electrical-quality floorplan is at
`.work/seven-mm-release-close-20261008/quality-work/`. It contains shorter critical
circuits, paired USB, single-surface SD and wider power routes, but is NOT complete
and is NOT the source baseline. Its75x116mm mechanical exploration adds bottom
space while keeping the7mm maximum; it is not a qualified enclosure or a routed
replacement. Never confuse its partial native file with the fully connected copy.
Generated candidate CAD, temporary JSON/reports, media and router grids stay ignored;
only reviewed source plans, contracts, tests and this handoff are committed.

## Earlier checkpoint (superseded by the section above)

# 2026-10-07 continuation checkpoint

The current source includes the low-profile electrical builder, 40P+20P FFC
mapping, explicit primary-cell RTC review requirements, native outline/port
checks, and verified Display routing replay. The earlier first-placement figures
below are historical; do not revert to those candidates.

Fresh native checks on the saved best Core candidate: DRC 0, open 4, parity 0,
ERC 0; Display: 0/0/0/0. The four Core opens are two GND islands, EPD_D0 and USB_DM.
The isolated continuation copy is `.work/seven-mm-final-four-20261007/candidate/`;
it was copied from `weighted4-trial/best-native.kicad_pcb`, not the interrupted
trial's working file. That baseline Core SHA-256 is
`b52d8a71630f79c50597d56efb15ce7ea43dacd7ee1886fceca9dea274785429`.
Pending Core copper is not labeled native-clean or included in manufacturing
export. Original donor PCB/schematic files remain unchanged.

The Core outline now includes the USB recess and a 64.8mm connector shelf.
Independent native copper-to-board containment rejects the previous J601 MP land
outside the board; nominal port faces remain bottom-center USB and lower-right SD.
Passing native geometry is not supplier-envelope, 7mm-stack, SI/PI/RF or safety
qualification. RTC diode orientation is NOT proof of negligible reverse charging.
No manufacturing release or order is authorized.

Validation before this checkpoint: 34 source-layout cases, 21 routing-evidence
cases and 8 native-port cases pass. Source plans/builders/contracts/tests belong
in Git; generated candidates, reports, DSN/SES, media and packaging stay out.

## Earlier initial-allocation handoff (superseded where noted above)

# Current product: whole-device thickness <=7mm

The22mm prototype is rejected. Develop662f5f4 remains the electrical/BOM donor,
not the new product geometry. Its old zero-DRC results do not apply to this relayout.
`seven_mm_layout.json` is the current source allocation:portrait75x112mm,
nominal6.8mm case thickness plus0.2mm positive tolerance, maximum7.0mm finished.

## Port and board allocation

USB-C external opening center:(37.5,112)mm,bottom center,outward+Y.
microSD external opening center:(75,96)mm,right side16mm from lower corner,outward+X.
Origin is the front-view top-left corner,X right,Y down. These datums are NOT
footprint origins; final offsets must follow the exact manufacturer's drawing.
Plug overmold, insertion/ejection travel, wall and corner clearance remain to verify.

Exactly two coplanar PCBs:4-layer Core along right spine/bottom strip,2-layer
Display in36x33mm lower-left allocation. Battery51x62mm occupies a separate XY
region. No PCB overlaps another PCB or the battery in the source allocation.
Keep0.8mm nominal PCB,0.88mm maximum budget and2.4mm mounted-component allowance.
The source sums are electronics6.98mm,battery6.85mm;these are budgets,not proof.

## Required changes before routing completion

C301's6.5mm-high backup capacitor must be replaced while preserving>=24h RTC.
The existing RTC charging policy must be reviewed with any new backup chemistry;
never substitute a primary cell into an enabled charging circuit.
U501's3.2mm module requires a low-profile implementation preserving16MB Flash,
8MB PSRAM,GPIO2 inhibit and RF performance;bare ESP32-S3R8 is an evaluation path.
J301/J302/J502 need low-profile domestic connectors or a qualified solder harness.
J601/J1 need a low-profile flexible link with all60 contacts and return paths verified.
J201 needs exact mid-mount package/cutout validation,not just moving the old body.
J501 needs card access and complete SD-bus rerouting,not merely a new opening.

The FT01C touch/frontlight screen remains62.37x105.33mm in portrait without scaling.
Its2.2mm thickness budget and FPC pose require supplier confirmation. Battery
complete-pack2.8mm plus0.5mm swelling is an allocation,NOT a selected SKU;retain
1100mAh target/900mAh minimum and protection pending exact supplier evidence.

## Actual initial native candidate

`prepare_seven_mm_placement.py` copies the current donor into a fresh external
candidate, preserves every footprint and pad-to-net assignment, removes obsolete
routes and applies new outlines/first-pass placement. Unimplemented tall/interface
parts remain visibly outside the outline for review,not deleted or converted DNP.

KiCad10.0.6 generated native-placement-02 on Mac mini:Core118 initially placed/37
review objects;Display36 placed/1 review. Review includes excluded mechanical/test
objects,not37 missing chips. Initial DRC/open/parity/ERC:Core3/395/0/0;
Display49/104/0/0. USB edge,legacy library and silkscreen issues remain explicitly
reported. This is NOT routed or manufacturing-ready. Donor PCB hashes are unchanged.

## Reproduce

Run `python3 hardware/thin18-compact/seven_mm_layout.py --test` or `--plan`.
Run `python3 tools/render/verify_product_envelope.py --test`.
Run KiCad's Python with `hardware/thin18-compact/prepare_seven_mm_placement.py
--output /absolute/new/external/candidate` for a new initial-placement candidate.

Old product rendering,release and RFQ entry points now fail closed. The stop can
only be replaced by reviewed native routing,part,port and tolerance verification;
a budget sum,JSON flag,old DRC or scaled22mm scene cannot clear it. No order placed.

Temporary native work is under Mac mini's
`/Users/isaacliu/Library/Caches/panda-seven-mm-20261005/` while MacBook is offline.
Canonical checkout remains `/Users/isaac/workspace/AI/panda-standard-board`,develop.
Commit only reusable sources/contracts/tests,not candidate CAD,reports or media.

Current source checks:32 layout-allocation cases and5 render-rejection cases pass.
The legacy release/RFQ commands return2 before any export or RFQ directory is created;
this is an intentional hold,not a new successful manufacturing validation.
