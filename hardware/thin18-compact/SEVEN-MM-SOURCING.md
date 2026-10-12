# Product D sourcing checkpoint — 2026-10-12

## Actual result, not a declaration that all supply is accepted

The original twenty missing PCB-reference codes are now classified without
omitting any required component. **12 references have verified exact JLC catalog
identities written into native PCB/schematic/local libraries; 7 SMT references
still require actual JLC registration/consignment acceptance; 1 required cell
assembly is explicitly post-SMT, not a reflow component.** Registration paperwork
is prepared, not submitted. There are no quotes, reserved stock or warehouse
receipts and no manufacturing/paid-order release.

The default `build_seven_mm_product.py --output ...` now applies the reviewed
sourcing overlay after reproducing D. `build_seven_mm_sourced_product.py` is an
explicit equivalent. `--routing-only` retains the immutable pre-sourcing D for
regression and must not be used as the current procurement BOM. Do not patch the
old C/initial electrical donor globally: its source-bound hashes are retained.

## Exact mappings and the two explicit MPN corrections

| References | Current manufacturer part | JLC code | Change |
|---|---|---|---|
| L506 | Sunlord SDCL1005C24NJTDF | C74301 | Exact original 24nH/0402 identity |
| L507 | Sunlord SDCL1608C2N0STDF | C370234 | Exact original 2nH/0603 identity |
| L508 | Sunlord SDCL1005C2N0STDF | C43365 | Exact original 2nH/0402 identity |
| C530,C531 | FH 0402CG0R8C500NT | C40459 | Exact original0.8pF/50V/C0G/0402 identity |
| R540–R545 | FH RC-02000FT | C140225 | Explicit replacement of unverifiedRC-02K0000FT ordering string;0-ohm0402 |
| Y501 | YXC XL2EL89COI-111YLC-40M | C18214314 | Explicit same-family40MHz/12pF crystal replacement |

The new resistor code is not claimed to identify the old ordering string. The
crystal replacement retains40MHz,12pF load,+/-10ppm initial tolerance,+/-20ppm
stability and-40..85C. Its manufacturerYSX321SL drawing matches the actual1.4x1.2mm
lands at(+/-1.1,+/-0.85),signal pins1/3 and GND2/4. Body max is3.3x2.6x0.8mm.
C528/C529 remain18pF. C9010/15pF and22-ohm C140177 are rejected, not substituted.
This is a specification/land comparison, not measured oscillator startup or RF
qualification. Existing signal paths, pad geometry and electrical values are not
modified to fit catalog availability.

Exact native properties in PCB, schematic instance, embedded/shared symbol and
local footprint carry MPN,LCSC,source URL,supply route,stage and non-acceptance
status. Source plans list raw evidence hashes/URLs, not embedded supplier HTML.
The actual source contract is `seven_mm_product_sourcing.json` and the guarded
metadata applier is `seven_mm_sourcing.py`.

## Seven SMT references still needing real registration

| References | Exact required part | Registration route |
|---|---|---|
| U402–U405 | SGM2578SDYG/TR | SGMICRO/authorizedSekorm -> registered JLC consignment |
| U902 | SGM62125AXG/TR | Same authorized manufacturer/distributor route |
| U905 | SGM37601YTRL20G/TR | Same route;20-pinTQFN,not24-pin |
| J201 | MUP U22401-17 | Original MUP -> registered JLC consignment |

The respective per-Core quantities are4,1,1,1. Total order quantity and placement
attrition are not chosen without the user's board quantities/JLC acceptance.
SGM2578S does not replaceSD/QOD; SGM62125B/C/D do not replaceA; the24-pin frontlight
variant and otherUSB material/plating/mount suffixes are not drop-in alternatives.
Public manufacturer pages establish exact identities, not available JLC codes.

**Search limitation:** the public JLCcomponentSearch SSR page returned zero even
for known positive controlsC74301/C56392. That broken/empty client-side result is
not proof that the seven parts do not exist in the catalog. Their C-codes remain
unverified and blank; no arbitrary code is assigned to achieve a zero-missing count.

OfficialSGMICROauthorized-distributor page listsSekorm. Relevant contacts in the
prepared request: sales_china@sg-micro.com / Sekorm400-830-1766; MUP
sales@mupconnector.com / +86-755-29673656. Receiving address and account-specific
registration labels must come from the actual JLCconsignment transaction, not a
copied internet address. Nothing was sent or purchased by this checkpoint.

## BT301 is required, but it is not an SMT code gap

BT301 remains in the all-stages PCB BOM and native design with noDNP/exclusion
change. Its exact manufacturer isYichang Power Glory/Omnergy,CR1216 primary cell.
The required part is a factory-insulated lead/tab assembly, not a bare coin-cell
SKU. It is explicitly excluded from the generated SMT stage and listed as mandatory
post-SMT assembly. No reflow or direct soldering to a bare cell is permitted.
Factory assembly drawing, maximum tab/lead/insulation envelope, polarity and
strain relief must be accepted. Bare-cell12.5x1.6mm is not the complete assembly
maximum. RTC reverse leakage/temperature/24hretention remains a separate gate.

## Verification and reproduction

-47 contract/parser/metadata-negative cases pass, including wrongC-code, foreign
 manufacturer, wrong crystalload/pins, changed package, false stock/registration,
 omitted cell, unsafe reflow and non-metadata geometry/net edits.
-A fresh default rebuild givesCore andDisplayDRC/open/parity/ERC0/0/0/0 after
 refill. Copper items, geometry, complete pad-to-net map and native rule/project
 files are unchanged by the sourcing overlay. No existing routing is redone.
-187 populated PCB references are exported from current native files, with all
 twenty original problem references retained. Code-mapped physical refs outside
 the twenty are preserved, not re-promised as stocked/received by this review.

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
python3 hardware/thin18-compact/test_seven_mm_sourcing.py
"$KPY" hardware/thin18-compact/build_seven_mm_product.py --output /fresh/external/candidate
"$KPY" hardware/thin18-compact/export_seven_mm_sourcing.py --candidate /fresh/external/candidate --output /fresh/external/sourcing-review
```

Generated current request/BOM package:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda7-sourcing-20261012/`.
ReadSTART-HERE.md,TWENTY-REFERENCE-DISPOSITION.csv,JLC-REGISTRATION-REQUEST.csv,
REQUIRED-POST-SMT.csv and the separately named manufacturer RFQ drafts. Core SMT
review CSV retains all7 unresolved refs with blankC-codes; it is deliberately NOT
named a production-ready BOM. ExternalTH301temperature-harness requirement is
also retained. Full enclosure/panel/main-cell BOM is outside this twenty-ref task.

Raw research, generated native candidates,CSV/RFQ/export reports stay out ofGit.
Only the manifest,metadata builder/verifier,tests,exporter and handoff are source.
Old ProductD render geometry does not change, and no new media is generated here.

## Primary sources

https://jlcpcb.com/partdetail/SDCL1005C24NJTDF/C74301
https://jlcpcb.com/partdetail/Sunlord-SDCL1608C2N0STDF/C370234
https://jlcpcb.com/partdetail/Sunlord-SDCL1005C2N0STDF/C43365
https://www.lcsc.com/product-detail/C40459.html
https://jlcpcb.com/partdetail/151551-RC02000FT/C140225
https://www.lcsc.com/product-detail/C18214314.html
https://www.oneyac.net/product/30804506.html
https://uploadcdn.oneyac.com/attachments/files/brand_pdf/yxc/1A/A8/YXC-YSX321SL.pdf
https://www.sg-micro.com/product/SGM2578SD
https://www.sg-micro.com/product/SGM62125
https://www.sg-micro.com/product/SGM37601
https://www.sg-micro.com/authorized-distributors
https://www.mupconnector.com/product/usbc/3412.html
https://www.omnergybattery.com/product/cr1216-coin-button-cell-battery-for-remote-controls
https://jlcpcb.com/help/article/how-to-consign-parts-to-jlcpcb-from-mainland-china
https://jlcpcb.com/help/article/how-to-use-jlcpcb-global-sourcing-parts-service
