# Product D — native112mm geometry and full-device render study

## Source and actual completed work

The reproducible source is `seven_mm_product_source.json`, revision D. Run
`build_seven_mm_product.py --output <fresh ignored/external path>` with KiCad Python.
It rebuilds the electrical donor, applies the checked C electrical/part changes,
then replays the D placements,112mm USB recess/outline and copper. Native Core and
Display both pass refilled DRC/open/parity/ERC0/0/0/0. Quality C remains an immutable
116mm electrical study; D restores the requested75x112mm product allocation.

USB-C mouth is at bottom center; microSD remains on the right near the lower corner.
The independent native pad-containment/port checker passes both boards. The old
22mm model and116mm board are not used by the new renderer or product-D builder.

The previous USB checker measured only A6/A7. D also checks the reversed B6/B7
orientation, preventing an A-side pass from concealing an asymmetric receptacle:

| Contact | Complete PCB planar path | Signal vias |
|---|---:|---:|
| D+ A6 |44.097236mm|2|
| D+ B6 |44.097236mm|2|
| D- A7 |44.335534mm|2|
| D- B7 |44.335534mm|2|

Both orientations have0.238298mm planar mismatch, below the0.5mm project review
limit, with matched transitions. Native branch geometry is symmetric; all required
connector contacts are preserved. These are PCB centreline lengths, not certified
90-ohm impedance, complete via/package delay, EMC or USB compliance.

The C525 RF bulk-supply path to U501.2 decreased from17.420658mm to4.894127mm;
to U501.3 it is4.943455mm. The new routed path is0.508mm wide throughout, with two
vias. The source capacitor, pins, regulator nets and RF network values are unchanged.
SD remains F.Cu/no-via; all six paths are within CLK+/-1.27mm. Do not confuse this
with RF/current/thermal qualification; independent measurements remain required.

## Reproduction and negative controls

1. Run `build_seven_mm_product.py --output /fresh/ignored/path` with KiCad Python.
2. Export Core using `tools/native_copper_geometry.py` with KiCad Python.
3. Run `verify_seven_mm_product_paths.py geometry.json --output report.json` using
   Python with Shapely. Both orientations, SD and RF path review must pass.
4. Run the source GPIO,60-contact interconnect, RTC and rule-preservation checks.
5. Generate render inputs with `tools/render/export_seven_mm_scene.py --candidate
   /fresh/path --output /external/scene-input`. Render using Blender and
   `tools/render/build_seven_mm_scene.py --source ... --output ... --mode all`.

Checks performed for D:10 USB-orientation/missing-contact/invalid-input cases,
24 routing-evidence/parser cases and37 source-allocation cases pass. Fresh rebuild
reconfirms native geometry,all-zero native checks and quality-C GPIO/firmware-header
agreement. The original donor and the prior best candidates were not overwritten.

## Render scope — not an assembly or tooling release

The new Blender scene includes rear housing,stepped screen-clearance front frame,
FT01C touch/frontlight/e-paper module,both coplanar boards,40P+20P FFCs,pouch battery,
side keys,USB-C,microSD socket and removable card. Native board geometry is imported
without scaling. The nominal case is75x112x6.8mm; the design target maximum is7mm.
The panel uses its1.98mm nominal module stack,not the thinner bare display.

Most package solids are explicitly identified proxies. Case retention features,
button travel,flex tails,wire strain relief and the exact supplier cable length
remain engineering studies. The nominal frame includes a larger underside pocket
so its rim does not intersect the screen body. The nominal model is not proof of
maximum supplier dimensions,thermal/mechanical compliance,or manufacturing tooling.

Images,MP4,Blender scene,input GLBs and the gallery are delivered outside Git under
`/Users/isaac/workspace/AI/panda-board-deliverables/panda7-revD-20261012/`.
Reproducible builders,reviewed routing plans,tests and this handoff are source;
no generated media,temporary PCB,report,Gerber or ZIP is committed.

## Order blockers still not represented as passed

Exact remaining supplier/catalog acceptance includes SGM2578SD switches,
SGM62125AXG,SGM37601 20-pin variant,mid-mount USB and several RF/crystal/passive
parts. The live missing-reference list must be regenerated from native fields;
previous7/6-reference counts do not include all bare-chip migration components.
RTC primary-cell reverse leakage/temperature/24h retention,cell/tab maximum sizes,
swelling/current limits,controlled stackup,via-in-pad treatment,stencil/CAM/SMT and
case/FPC/tolerance acceptance remain open. A catalog identity is not stock reserved
or assembly acceptance. No paid order or unverified manufacturing approval is made.

Old production-release guards stay closed. D is a source-verified engineering
review with completed native routing,not a claim that every external gate is closed.
