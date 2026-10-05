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
