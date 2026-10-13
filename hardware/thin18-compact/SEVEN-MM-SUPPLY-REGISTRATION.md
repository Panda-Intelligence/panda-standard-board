# Remaining supply: source-bound technical registration, 2026-10-12

## Actual result and boundary

The existing twenty-reference disposition remains **12 exact catalog mappings,
7 required SMT references pending actual registration/supply,1 required post-SMT
RTC cell assembly**. This checkpoint assigns no new C-code, sends no inquiries,
places no order and does not claim manufacturer or warehouse acceptance.

The earlier empty-SSR search limitation was resolved with an anonymous browser
and successful public-search responses. Known positive controlC74301 returned its
exact Sunlord part. Searches forSGM2578SD,SGM62125,SGM37601 did not show a match in
that public catalog snapshot. U22401 returned four candidates,none establishing
the exact-17 identity. LCSC denied even its positive control; this cannot be
interpreted as no stock. Search results are not an availability guarantee and are
not evidence that JLC cannot register a part. No user's browser session was used.

## Do not turn a similarly named C-code into a false substitution

| Candidate | Catalog code | Technical disposition |
|---|---|---|
| U22401-23 | C49325733 | Manufacturer specifies1.60mm mid-mount,CH-0.02;current design needs0.80mm,CH0.78. Reject as a drop-in despite similar XY dimensions. |
| MUP-U22401-38 | C56127182 |0.80mm but LCP/gold-flash;not the NYLON/Au3u-17. No reviewed full variant replacement or supply approval. |
| MUP-U22401-05 | C9900262011 |Different LCP suffix;public entry isJLCPCB Assembly,Standard Only/high difficulty. Not evidence this code identifies-17. |
| MUP-U22401 | C5128294 |Generic unsuffixed identity cannot prove the required mounting/material variant. |

Keep all seven exact original SMT parts. No source geometry,net mapping,copper,
rules,population or existing catalog mapping changes in this checkpoint.

## Completed technical request data

`seven_mm_supply_registration.json` binds to the current sourced-BOM contract.
It supplies four precise registration rows,4/1/1/1 quantities perCore,manufacturer
sources,MSL1/1/2 for the threeSGMICRO package groups, and an explicit unknown MSL
for the USB connector pending manufacturer packaging confirmation.

`seven_mm_supply_preflight.py` checks native identities and exports actual top-view
placement and pad/net coordinates. It does not call the KiCad angle a JLC machine
rotation. U905's twenty leads plus exposed pad21 are kept separate from its four
unnumbered paste windows. C-codes,actual quantities,invoice/price/origin/weight,
account registration,address,labels and receipts are never invented.

BT301 has an internal drawing REQUEST identifier,not a supplier SKU. Its current
positive2x2mm landing is(58.5,56.4)mm/RTC_CELL_P;negative is(68.5,56.4)mm/GND. Both
lie beneath the nominal cell body,so the manufacturer must propose factory-attached
insulated leads/tabs and a safe assembly sequence.2.4mm is a project installed-height
budget,not a signed complete-cell maximum. No bare-cell soldering,reflow,uninsulated
tab compression or unproven reverse-charge/24h retention approval is permitted.

## Quantity and acceptance handling

The current user has not confirmed Core/Display build quantities. The exporter can
run without them to ask technical feasibility/sample MOQ,but leaves purchase totals
blank. With explicit board counts it computes required populated quantities;
actual consignment totals remain blank until JLC attrition is provided.

The state helper rejectsReceived/Checked as usable inventory. In Warehouse,
sufficient available quantity,and deliberate identity/document review are necessary
inputs. The helper does NOT authenticate documents and does not itself qualify the
board or provide purchase authorization. No synthetic unit-test receipt is ever
exported as real supplier evidence.

## Run

```sh
python3 hardware/thin18-compact/test_seven_mm_supply_preflight.py
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
"$KPY" hardware/thin18-compact/seven_mm_supply_preflight.py \
  --candidate /absolute/path/to/current/sourced/candidate \
  --output /absolute/fresh/external/registration-review
```

Optional`--core-quantity N --display-quantity N`requires user-confirmed positive
integers. There is no default production count. The current generated request
packet is outside Git at
`/Users/isaac/workspace/AI/panda-board-deliverables/panda7-registration-technical-20261012/`.
It includes four UNSENT preflight requests to JLCPCB,SGMICRO,MUP andOmnergy,without
purchase commitments. It deliberately omits complete schematic/PCB copper from
vendor material preregistration.38 new tests pass;both native boards recheck
DRC/open/parity/ERC0/0/0/0 unchanged. Registration/quote/receipt collection is the
next external action,requiring actual account/user authorization and responses.

## Primary sources

https://jlcpcb.com/partdetail/MUP-U2240123/C49325733
https://www.mupconnector.com/product/usbc/3414.html
https://www.mupconnector.com/product/usbc/3424.html
https://www.mupconnector.com/product/usbc/2980.html
https://jlcpcb.com/partdetail/JLCPCBAssembly-MUP_U2240105/C9900262011
https://jlcpcb.com/partdetail/MUP-MUPU22401/C5128294
https://www.sg-micro.com/product/SGM2578SD
https://www.sg-micro.com/product/SGM62125
https://www.sg-micro.com/product/SGM37601
https://www.omnergybattery.com/product/cr1216-coin-button-cell-battery-for-remote-controls
https://jlcpcb.com/help/article/how-to-consign-parts-to-jlcpcb-from-mainland-china
