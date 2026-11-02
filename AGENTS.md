# CURRENT ROUTING CONTINUATION — 2026-11-02 R37 SINGLE / VREF TREE

Read `hardware/pico47/E02-R37-VREF-TREE-20261102.md` first. Default R37 replays
directly from immutable R26 with single_r37_layout_delta.json SHA-256
972b1157ebeb0d7c2a706b240f82f18db1adc07806f900560201e28a5f32c421.
Named candidate: `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r37/engineering-candidate`.
PCB SHA-256 df53238d1b91644d1c76f66369b0b603483c167a0864e79b14f4c5ba714fc2ea.

Only P47_VREF copper changes: 77.746→36.769 mm, 608→27 tracks, 6→4 vias.
All 265 parts/908 pads/IDs/fields/values/poses, all non-VREF copper, SCH/libraries,
rules/16 zones/outline/stack remain exact. C815 stays unique100n at B12.8/94/0;
preserve its complete four-item root and root-via surface contacts. R805 is now
6.187mm F-only (visited root via is a same-layer contact); R804.2 is29.642mm
planar/32.197mm spatial. Do not call geometric shortening noise qualification.

Original R804 terminal/under-inductor reference copper remains in the0.5mm
LX-pad/track/via + native L801/L802 courtyard search projection. New copper adds
no physical exposed area outside old copper coverage (2um export tolerance).
R804 move screen had zero courtyard-compatible quiet positions; none adopted.
Keep original coupled copper risk explicit. Final source guard limits the whole
reference tree to40mm/4vias and exact reviewed coupled primitives; actual noise,
stability/current PMIC revision remain unqualified. Historical R36 is retained.

Two full replays/default/historyR36/native audits pass:43/43, all native/ERC0,
185GND/52critical,11018tracks/1004vias/16zones,443 distinct local tests. Keep
4layers/noIn1signal/negativeEP/C804dogbone/GPIO2direct/3clockGND/7power4CIN4COUT/
full46process/actualSDUSBclockrefs/43poses. SMT226/CPL226, BT301postSMT excluded,
21pending. Actual electrical/noise/power geometry, actual pack/fullpanel maximum
envelopes, backside heights/clearance/positive-tolerance<=7mm, supply/full46CAM/EVT
remain open. No manufacture, charging or panel power. User requires verified
stage commit & regular push to this feature branch; reviewed PR before main.
Generated CAD/reports/renders stay ignored/external. Inspectors writing netlists
run only on fresh review copies. Preserve packaging, four worktrees, unrelated
changes and every historical sealed checkpoint; never select by newest mtime.

# HISTORICAL ROUTING CONTINUATION — 2026-11-02 R36 SINGLE / PMIC REFERENCE FILTER

Read `hardware/pico47/E02-R36-PMIC-REFERENCE-FILTER-20261102.md` first.
DefaultR36 directR26 source single_r36_layout_delta.json SHA
d7c0ac5a03cae4326a6f1ba5c71952c1a1cc08323c71a4a20a5627e2eeb2454e.
Named candidate: `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r36/engineering-candidate`.
PCB SHA256 b7c149d1d8bf7ddb1d910e96ab67490a90bce4a5aac332bfa5abb5c53a7e6477.

Only existingC815100n movedF8.75/92/90 toB12.8/94/0; all265parts908pads/UUIDs/
fields/values/pinnets retained, other264poses andallotherCu/rules/libraries exact.
VREFcap planar14.601→.846mm, effectivevias2→1, spatial15.879→1.611mm; native
pad-distance .305mm. HistoricalSilergy0.9B limitsVREFfilter to.1uF: keep onlyC815,
do not parallel/increase. Newguard checks unique fittedcap/nominalvalue/actual
powerGND/face/locality/50umvia edge, notactualtolerance/noise/stability approval.

6oldleaftracks+1oldVREFvia removed,2short025B+1explicit016In2bridge added. Oldvia
9.025/93.175 carried4In2contacts; directdelete splitgroups, so preservejunction
explicitly with fullpadguard. No live surfacejunction deleted. Now11599tracks/
1006vias/16zones185GND52critical/all43/native+ERC0;439distincttests/twofullreplays
+default/historyR35/43poses pass. WholeVREFstill~77.746mm; R8042path44.624mm,
R805planar16.140→16.454mm; notfullreferencetree/noise qualification. BothF-only
switch trials failedboundedsearch; originalVP/VNswitchCu retained.

Keep4layers/noIn1signal/negativeEP/C804dogbone/GPIO2direct/3clockGND/7power4CIN
4COUT/full46process/actualSDUSBclockrefs. SMT226/CPL226 C815Bottom, BT301postSMT
excluded,21pending. HistoricalPMICmirrorhash differs oldreference and isnotcurrent
supplier approval. Actualelectrical/noise/DCbias/SI/USB/packfullpanel/positive-
tolerance<=7mm/backSMT/capheight/full46CAM/EVT remainopen; no manufacture/charging/
panelpower. Userrequires stage成果commit&push after localvalidation; sourceonly,
featurebranch regularpush, reviewedPR beforemain, generatedCAD/reports/renders
ignored/external. Inspectors writingnetlists onlyfreshreviewcopies; sealedpackages
read-only. Preserve packaging/worktrees/unrelateddirty and allhistoricalcheckpoints.

# HISTORICAL ROUTING CONTINUATION — 2026-11-02 R35 SINGLE / DIGITAL POWER BYPASSES

Read `hardware/pico47/E02-R35-DIGITAL-POWER-BYPASSES-20261102.md` first.
DefaultR35 directR26 replay: single_r35_layout_delta.json SHA
9c478c044753a4a8fb4774a9975d3b574b4983cd8b67f7d3d1232adc0cc7bf52.
Named candidate: `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r35/engineering-candidate`.
PCB SHA256 5223786c60ad3ba16d06b49eef75afafa501e227e7c0cdc7702e94af7ebb52bf.

Only7localdigitalpowercaps C537..543,8short025surface tracks,4GND400/200vias
and1Bactual-reference GNDzone added. OriginalR34 all258parts894pads11594tracks
1003vias/IDs/fields/poses/Cu/oldlibraries/rules/oldzones/stack retained; now265parts
908pads11602tracks1007vias185GND50critical/all43/native+ERC0. C537100n+C5381u
nearMCUVDD_SPI andC543100nnearFlash areB, other4F. MCUplanar11.427/12.330→
1.152/1.091mm,Flash5.141→.798mm, allthree useoneexistingF-Bvia. IMU5/8 old
specifiedcap45.035/32.810→.769/.496mmF,displayExp7.580→.873mmF.

NewR35_MEMORY_LOCAL_GND B60.5/92..72.2/104.3 actuallyconnects toU50157 and
C537/C538groundpads; notsame-netisland. FourCIN/fourCOUT/full46solderjointvia
signature/oldpadgroups/SDUSBclockrefs/3clockGNDstitches retained.434distinctlocal
tests/twofullreplays+default/historyR34 pass;42poseenvelopes pass. NewB additions
use normalizedF libraries andofficialFlip onlyafter validparentboard, exactIDs/
padnets/coords/native roundtrip checked. Originalinput/outputfacepolicy unchanged.

SMT226/CPL226 has3newBottomcaps, excludespostSMTBT301;21pending remain. NewB
caps mustenter actualheight/clearance/positive-tolerance<=7mm qualification,
which remainsopen withactualpack/fullpanel/DCbias/waveforms/SI/USB/supply/full46
viaCAM/EVT. Keep4layers/noIn1signal/originalrules/C804dogbone/negativeEP/GPIO2.
No manufacture/charging/panelpower. Inspectors writingnetlists onlyfreshreview
copies; sealedpackages read-only. Preserve packaging/worktrees/dirty; generated
CAD/reports/renders stayignored/external. Do not rerun knownfailedboundedroutes.

# HISTORICAL ROUTING CONTINUATION — 2026-11-02 R34 SINGLE / U403 INPUT BYPASS

Read `hardware/pico47/E02-R34-U403-INPUT-BYPASS-20261102.md` first. Default
R34 replays directly from immutableR26, single_r34_layout_delta.json SHA
d989eade7a73cf0e18f7fa888a2eed459f1ba6d446b896dffda59117db546388.
Named candidate: `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r34/engineering-candidate`.
PCB SHA256 d98e436d8ee0e4b363945733060c51e65a30f65bbcc7339b970e1730b761e48f.

Only C536 FH1uF0402 nearU403.IN atF42.2/67.95/0,2short025Ftracks and1GND
400/200via43.275/67.7 added. OldC509 remains; it is28.936mm fromIN, nearest
old>=1uF cap20.472mm. NewC536 pad0.971mm, nativepowerCu~0.948mm F only.
All257R33parts892pads11592tracks1002vias/IDs/fields/poses/Cu/rules/zones/stack/
oldlibraries retained; now258parts894pads11594tracks1003vias178GND36critical.
FouractualCIN/fourCOUT contracts, full46solderjointvia signature and all43/native
ERC0 retained.427distinct localtests/twofullR26replays+default/historyR33 pass.

NewC536 retains50umordinaryvia padedge. ExistingC511 hasaccepted~25um same-net
annulus gap withoutdrill-in-pad; keep originalnative rules/processinventory,
do not moveoldpowerCu just toretrofit new-component placementbudget.
SMT219/CPL219 excludespostSMTBT301;21pendingSMT remain. Keep4layers/noIn1signal,
alloldpadgroups/C804dogbone/negativeEP/GPIO2directchain/3clockGNDstitches/actual
SDUSBclockrefs. ActualDCbias/transients/SI/USB/packfullpanel/positive-tolerance
<=7mm/backSMT/height/supply/full46viaCAM/EVT remain unqualified. No manufacture,
charging or panelpower. Inspectors writingnetlists onlyfreshreviewcopies;
sealedpackages read-only. Preserve packaging/worktrees/dirty; outputs ignored/external.

# HISTORICAL ROUTING CONTINUATION — 2026-11-02 R33 SINGLE / LOCAL BYPASS AND PROCESS

Read `hardware/pico47/E02-R33-LOCAL-BYPASS-PROCESS-20261102.md` first. Default
R33 replays from immutableR26 with single_r33_layout_delta.json SHA
4a28afb7bd9b7c591e910ba3a32dfe369bf38f008146d85ea494129b8105a9f4.
Named copy: `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r33/engineering-candidate`.
PCB SHA256 c087facf0bd6b87996160b32dc51f69c58db11497bcc5d9037d9c49b4e668bc8.

Only3local1uF0402caps C533/U402,C534/U403,C535/U405 plus5short025Ftracks and
1GND400/200via added. OriginalR32 254parts886pads11587tracks1001vias/fields/
poses/nativeIDs/rules/zones/stack retained, includingC532 via officialpreserveUUID.
Now257parts892pads11592tracks1002vias177GND28critical/all43/native+ERC all0;
422distinct localtests/twoindependentfullR26replays+default/historyR32 pass.

Full native process inventory is46distinct solder-joint vias requiring filled+
capped process, not just9MCUthermal. Includes9chargerthermal+28other; bareTP8
separate, overlappingTPG2 not counted twice. Exactcomplete signature is source
checked. FourlayerPOFV option needs explicit quote/CAM acceptance; not tenting.
supplier_process_accepted=false. SMT218/CPL218 excludespostSMTBT301;pending21.

Keep4layers/noIn1signal/originalrules/outline,alloldpadgroups,C804dogbone,
negativeEP,GPIO2directchain,oldclockGNDstitches/SDUSB/clockreferences. Real
SI/powerUSB/DCbias/transient/actualpackfullpanel/positive-tolerance<=7mm/backSMT/
height/supply/fullCAM/EVT remain unqualified. No fabrication/charging/panelpower.
Inspectors exportingnetlists onlyfreshreviewcopies; sealedpackages read-only.
Preserve packaging/worktrees/dirty; generated outputsignored/external.

# HISTORICAL ROUTING CONTINUATION — 2026-11-02 R32 SINGLE / U404 OUTPUT BYPASS

Read `hardware/pico47/E02-R32-C532-BYPASS-20261102.md` first. Default R32 source
replays directly from immutable R26 using single_r32_layout_delta.json
(SHA440d581883452c8de9a43d436c7afc47f2b30e05b567cc83c6352bf0b2c0c570).
Named engineering copy:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r32/engineering-candidate`.
PCB SHA256 `8b042c08883c47b3f6475096820b8e9e19c66e00f95e2aeede641d8220b30ee2`.

Only C532 FH0402X105K100NT/C1573531uF10VX5R added atF50.95/88.4/135 plus2short
025Fground tracks; no new vias or original parts/copper moved. Original253parts/
884pads/11585tracks1001vias/rules/zones/outline/stack preserved; now254parts/
886pads/11587tracks1001vias.174GND22critical/43controls/native+ERC all0,417distinct
localtests/2independent completeR26replays+default pass; explicitR31 regression passes.
Keep strict oldpadguard; only the two declared newC532IDs are projected out for
old-inventory validation, with separate actualCOUT connections and50umSMDvia checks.

SMT215/CPL215 excludes post-SMTBT301; pending21SMT remain. Job revision/GUID binds
actual revision/PCBsha. Preserve R26..R31 history,3oldGNDstitches/SDUSB/clockrefs,
fourlayers/noIn1signals/C804dogbone/nineMCUthermal/negativeEP/GPIO2directchain.
Actual SI/powerUSB/DCbias/transients, exactbattery/fullpanel/finished<=7mm/backSMT/
height/supply/CAM/EVT remain unqualified. No fabrication/charging/panelpower.
Inspectors exporting netlists run on fresh review copies, never sealed packages.
Preserve packaging/worktrees/dirty work; generated outputs ignored/external.

# HISTORICAL ROUTING CONTINUATION — 2026-11-02 R31 SINGLE / GROUND STITCHES

Read `hardware/pico47/E02-R31-GROUND-STITCHES-20261102.md` first. Default source
replay is R31, directly from immutable R26 with single_r31_layout_delta.json.
Named engineering copy:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r31/engineering-candidate`.
PCB SHA256 `919d022d3bcdd8029247e58dc10897879bf40fa1cc9a66604e77364a95fcd265`.
Two independent full replays plus default build preserve43controls/native+ERCall0,
173GND/20critical/priorgroups/253parts884pads30poses.407distinct localtests pass.

Only3GND400/200throughvias added at51.6/85.2,49.675/101.275,40.425/105.675.
All11585tracks/998oldvias/poses/rules/15zonedefinitions retained; now1001vias.
Actual In1/B reference-ground contacts proven; three target distances
2.315/3.068/2.900mm become0.577/0.577/1.043mm. These are geometry observations,
not SI/EMI limits. SD9104/USB1224 and F/In2clock1657 references remain covered;
Bclock adjacentIn2 still495/633uncovered, explicitly unqualified.

Keep explicit R26..R30 history, fourlayers/noIn1signal, negativeEP isolation,
GPIO2 inhibit, C804 external return/nine thermalvias and R728/R731/R710 poses.
Actual electrical/USB/power qualification, backsideSMT/maxheight, exactbattery/
fullpanel/finished<=7mm, sourcing/CAM/EVT remain open. No manufacture/charging/
panelpower. Preserve packaging/worktrees/localedits and all immutable packages.
Inspectors that export netlists must use fresh copies, never sealed packages.

# HISTORICAL ROUTING CONTINUATION — 2026-11-02 R30 SINGLE / CLOCK REFERENCE

Read `hardware/pico47/E02-R30-CLOCK-REFERENCE-20261102.md` first. Current default
source replay is R30 from immutable R26 using single_r30_layout_delta.json.
Named engineering copy:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r30/engineering-candidate`.
PCB SHA256 `7f867d8fa5e519a7f448fe2980533ad9e5f791c3eed59d9f018d906f94421f07`.
Two independent full replays plus default build preserve43controls/native+ERCall0,
173GND/20critical/priorgroups/253parts884pads30poses.403distinct localtests pass.

Only two ordinary vias moved: CHIP_PU_DEBUG48.45/88.2→48.525/88.35 and D1_SRC
45.375/90.875→45.25/91.0. All track geometry and clock/power/SD/USB/GND/special
vias remain R29; all five original surface contacts retain actual native contact.
F/In2clock→In1 reference1657samples now covered, fixing5top-clock misses. Bclock
adjacentIn2 remains495uncovered samples, explicitly observational/unqualified.
Do not conflate this screen with actual SI/timing/return/EMI qualification.

Keep explicit R26..R29 history, fourlayers/noIn1signal, originalrules/outline/stack,
negativeEP isolation, GPIO2 inhibit, C804 external return and nine thermalvias.
R728F65.475/90.825/45 and R731B64.7/89.1/180 remain. R710/R731backsideSMT/maxheight,
actualbattery/fullpanel/finished<=7mm, sourcing/CAM/EVT and actualelectrical
qualification remain open. No manufacture/charging/panelpower. Preserve packaging,
worktrees/localedits and historical immutable packages; generated outputs external.

# HISTORICAL ROUTING CONTINUATION — 2026-11-02 R29 SINGLE / XSTL SOURCE QUALITY

Read `hardware/pico47/E02-R29-XSTL-SOURCE-QUALITY-20261102.md` first. Current
default is R29, directly replayed from immutable R26 with single_r29_layout_delta.
Named engineering copy:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r29/engineering-candidate`.
PCB SHA256 `b6924d0fb818552b4da0094b6b5771c9eeeafca02e0572b9fddbb4297ee404a9`.
Two independent full replays plus the final default build preserve 43 controls,
errors/warnings/opens/parity/ERC0/0/0/0/0, 173GND, 20critical links and prior pad
groups. All401 distinct local source tests pass. Keep explicit R26/R27/R28 replay
bindings and all historical packages.

R728 stays F65.475/90.825/45; R731 moves B64.7/89.1/180 with its original10k
identity/net and an existing GND via. Driver-to-series is5.097mm/2vias; pulldown
branch1.479mm/1via; output65.375mm/9vias. Combined inventory86.052→73.777mm and
effective main spatial path79.785→77.365mm, but total two-net vias8→11. No timing,
ringback/EMI or backside-SMT qualification is implied. All other Cu, SD18/USB,
power and GND vias/special holes/rules/outline/stack remain as accepted R28 except
the one reviewed R731 ground-return leaf. Actual reference SD9104/USB1224 covered.

Preserve four layers/no In1signals, 253parts884pad identities, negativeEP isolation,
GPIO2 inhibit, C804 external return and nine MCU thermal vias. R710 and R731 B
assembly/maxheight, exact2050mAhpack/fullpanel/finished<=7mm, power/USB/timing,
sourcing/CAM/EVT remain unqualified. No manufacture/charging/panelpower. Generated
outputs stay ignored/external; preserve packaging/worktrees/local edits.

# HISTORICAL ROUTING CONTINUATION — 2026-11-02 R28 SINGLE / 43 CONTROLS

Read `hardware/pico47/E02-R28-ROUTING-CLOSURE-20261102.md` first. R28 is the
current default source replay from immutable R26 `hardware/pico47/v0.1.1` via
`single_r28_layout_delta.json`. Two independent full replays and the final default
rebuild reproduced errors/warnings/opens/parity/ERC 0/0/0/0/0, all 43 controls,
173 GND pads, 20 critical links, and all prior pad groups. Named engineering copy:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r28/engineering-candidate`.
Its PCB SHA256 is `619944b984cc732597b03fbc79138c84954622956441b64cb50e9e0ec133de1e`.
Keep R26/R27 explicit historical rebuilds and all existing checkpoints.

SD spatial paths are 48.390..50.601 mm with maximum absolute CLK skew 1.195 mm;
the conservative geometric screen passes. Actual reference coverage passes using
reference-connected native fills (SD 9104 / USB 1224 samples); an independent
export-based check also passes (SD 9136 / USB 1224). Different segment-rounding
counts do not relax width or coverage. 401 distinct local source tests pass.

Preserve four layers/no In1 signals, native rules, outline, 253 parts/884 pad
identities, GPIO2 inhibit, isolated negative EP, C804 external return and nine MCU
thermal vias. C523 stays F at61.275/103.3/-45; R710 stays at its accepted B pose.
XSTL driver-to-series52mm/6vias, timing/ringback/EMI, supply transients, actual USB
impedance, backside SMT, exact battery/full panel/finished<=7mm, sourcing/CAM/EVT
remain unqualified. No fabrication, charging or panel power. Generated CAD,
reports and orderpacks stay ignored/external; source delta/tests/handoff stay
reviewable. Preserve packaging, unrelated worktrees and all local changes.

# HISTORICAL ROUTING CONTINUATION — 2026-10-31 R27 SINGLE LAYOUT

Read `hardware/pico47/E02-R27-ELECTRICAL-ANALYSIS-20261031.md` and then
`hardware/pico47/E02-R27-LAYOUT-FIXES-20261031.md` first. The current design
is the R27 Single four-layer board, rebuilt from immutable `v0.1.1` / R26 using
`build_pico47_single.py` and its SHA-bound `single_r27_layout_delta.json`.
Named engineering checkpoint:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261031-r27/engineering-candidate`.
Do not select a newer-mtime trial or resume the historical R7 two-board routing.

Two independent fresh R26 source replays reproduced native errors/warnings/open/
parity/ERC 0/0/0/0/0, all 173 GND pads, 20 critical links and every original pad
group. Seven actual-layout geometry checks pass. VBUS copper equivalent is
0.109231 ohm; SD planar paths are 46.158..46.921 mm with 0.763 mm max planar CLK skew.
The optional native-Gerber-job layer model adds actual used via spans: spatial
paths are 48.171..53.303 mm, D2/D3 are -4.365/-3.235 mm versus CLK. Its conservative
spatial screen is RED; electrical timing stays unqualified. Analysis is not a
new CAD revision or release. Do not add vias solely to chase this geometric budget.
USB has a native filled In2 reference (1,224 samples covered); 90-ohm impedance,
package/mux timing and physical electrical performance remain unqualified.

Keep four layers/no In1 signal tracks, isolated U810.49, C804's external return
via and all nine U501 thermal vias, original rules/outline/pins/BOM and direct
GPIO2 permit chains. Manufacturing release and supplier process acceptance stay
false; exact battery/full screen/<=7 mm/physical EVT gates remain open.
Use `--revision R26` for historical baseline rebuilds. Preserve v0.1.0/v0.1.1,
the old external R26 package, packaging/ and unrelated worktrees. Generated native
CAD/reports/renders remain ignored or external; only replay source/contracts/
tests/handoffs belong in Git. Never inspect immutable packages with tools that
write netlists into their candidate; use fresh copies.

# HISTORICAL ROUTING CONTINUATION — 2026-10-14 r7: SPV CONNECTED

Read `hardware/pico47/E02-R7-SPV-CLOSURE-20261014.md` first.
Canonical dated engineering checkpoint:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261014-r7/engineering-candidate`.
The requested `panda47-e0-20261012/engineering-candidate` is its verified working
copy. Previous r6 is preserved in sibling
`engineering-candidate-pre-r7-archive-20261014`; r5 and older archives remain.

Fresh native counts: Core 32 opens, Display 9 opens; DRC errors/warnings/parity/ERC
are zero. All four exact connector controls CKV/SPV/XLE/XSTL are now connected.
All 237 ground pads and eight named ground targets remain reference-connected;
the complete GPIO2/interconnect/R813/U810.EN21 chain is retained. There are still
41 non-ground native unconnected items. No fabrication, charging or panel power.

The adopted solution changes only four control nets. A separate native audit
proved all 9,429 other-net track/via items identical to r6. XLE, CKV and XSTL are
shorter; no supply/ground copper was moved and no project rules were weakened.
Fresh combined capture, clean source rebuild and independent complete-ground
recapture reproduced counts, all previous pad groups and all four control states.
539 distinct local source tests passed; Pico47's 282 also passed under KiCad
Python. These are not GitHub Actions results.

Continue with `capture_pico47_checkpoint.py --require-complete-ground`. Preserve
four layers/no In1 signal tracks, isolated negative PMIC EP, C804's prescribed
return via, source parts/pads/placement/outline and native rules. Timing/current,
analog feedback, exact battery/full panel, <=7mm fit and physical EVT remain open.
The standalone inspector still writes generated netlists into its candidate;
use fresh candidate copies for those exports, not published immutable packages.
The unintegrated evidence-wrapper draft remains ignored and is not enabled.

Generated native CAD/reports/manifests/experiments stay ignored or external.
Preserve packaging/, unrelated worktrees and local changes. Use reviewed PRs to
main and named accepted checkpoints, never a newer-mtime failed trial.

# HISTORICAL ROUTING CONTINUATION: Pico47 E0.2 — 2026-10-12

Read `hardware/pico47/E02-HANDOFF.md` first. Current external checkpoint:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261012/engineering-candidate/`.
Working ancestry: `.work/pico47-resume-20261012/integrated-current/`.
Latest native counts: Core48 opens/26 warnings;Display21 opens/5 warnings;
DRC errors/parity/ERC0. Do NOT label this fab-ready or reuse historical161/49.
Use `build_pico47.py --routing-checkpoint <current-checkpoint>` to rebuild and
resume its copper, rather than starting again from the partly unrouted base.
Ordered Core28-part placement/16 header-side data links/9MCUground vias are now
explicit source. C804.pad2 has an additional resin-filled/copper-capped return
via; its process acceptance remains false. The source and native checks enforce
both policies. GPIO2-to-FFC and DisplayFFC-to-R813 are connected, but the final
R813-to-PMIC-EN connection is still open. Do not power the panel.
Never delete a dangling via that is a live surface junction; preserve all native
pad groups and actual reference-plane connectivity. No net-wide unreviewed rip-up.
The old battery/complete panel stack/<=7mm physical and CAM/SMT gates remain open.
Generated native boards, checkpoint manifests/reports and renders stay outsideGit.
Keep user packaging/ and unrelated worktrees untouched.

# CURRENT USER OVERRIDE: Read-Pico-class display and battery — 2026-10-12

Continue `hardware/pico47/README.md` and `hardware/pico47/design.json` on develop.
The user confirmed the same Pico 4.7-inch 1216x684 ~297PPI E0470A01 family AND
same actual replaceable2050mAh LCO pack. The old4.26-inch SPI/1100mAh ProductD is
now only a reversible donor/regression; do not resume it as the requested product.
Keep two PCBs, <=7mm finished maximum, touch/frontlight/audio/IMU/SD/RTC,
mainland manufacturer identities and GPIO2 direct inhibit. The132mm trial envelope
is NOT an approved enclosure. Exact Pico pack dimensions/MPN/connector/NTC/CV and
full screen stack remain unknown, not inferred from capacity or bare glass.
E0 is still unrouted/partly routed and NOT FOR FABRICATION OR PANEL/BATTERY POWER.
Never reuse ProductD zero-DRC evidence as E0 acceptance. Preserve live pad groups
when pruning; the native pad-cluster guard must not be bypassed. Router completion
and fewer airwires after deleting orphans are not manufacturing qualification.
Generated CAD, SES/DSN, evidence, renders and reports stay ignored/external, not Git.
Keep the existing untracked packaging/ untouched. Use the handoff's named current
candidate rather than newest mtime; do not delete it as disposable work.

# Current sourcing continuation — 2026-10-12

For procurement/BOM work read `hardware/thin18-compact/SEVEN-MM-SOURCING.md`.
The default `build_seven_mm_product.py` includes the20-reference sourcing overlay;
`--routing-only` is only the immutable pre-sourcing regression checkpoint. Do not
edit old donor/model strings globally or lose source-bound routing. Keep required
pending7 SMT parts and manualBT301 visible; blankcodes/unsignedRFQs are not receipt.
Generated sourcing requests,BOM CSV,evidence HTML/PDF and native outputs stay outsideGit.

# CURRENT OVERRIDE: <=7mm native product relayout

The user explicitly rejected the22mm prototype and asked for PCB relayout.
Finished whole-device thickness MUST be <=7mm, including positive tolerances.
USB-C is allocated to bottom center and microSD to the right side near the lower
corner. Read `hardware/thin18-compact/SEVEN-MM-RELAYOUT.md` and
`seven_mm_layout.json`. They supersede older text freezing the existing outline,
WROOM module, stacked connector or treating7mm as merely optional.

The latest develop is the electrical/BOM donor; preserve the proven functionality,
all-mainland identity policy,16MB Flash/8MB PSRAM,>=24h isolated RTC and direct
shutdown. Do not merge the old R2/media branches or claim its work is verified here.
New native candidates must stay in ignored/external output; only reviewed source,
contracts, tests and reusable builders belong in Git. No renders/models/reports/ZIPs.

The source allocation and initial footprint packing are NOT finished native
routing, supplier maximum-envelope qualification, or fabrication approval. The
old product-render/RFQ/release entry points are deliberately blocked. Do not remove
that stop based on a budget calculation, old DRC, or scaled visuals. New parts,
footprints, pin maps, current/returned-path routing, mechanical tolerance and full
native rebuild checks must precede release. Keep the old routed CAD reversible.
MacBook canonical checkout remains `/Users/isaac/workspace/AI/panda-standard-board`;
any Mac-mini cache clone is temporary validation, not another long-lived worktree.

# Earlier guidance (current override above governs product geometry)

# Panda Standard Board continuation

The user's current task is **the already split, routed main-branch Split-C1**
plus completion of mainland-chip functional migration. Read
`hardware/thin18-compact/SPLIT-C1-HANDOFF.md` first.

Inspect `git worktree list`, current status and remote main before editing.
Choose the design requested by the user, not whichever experiment has the newest
mtime. `thin7/portrait-r2` is a separate experiment and is not the source of the
current Core-C1 96x68 / Display-C1 45x36 prototype. Do not import its board shape,
MCU bare-chip design, interconnect, placement or internal-layer policy.

Preserve all unrelated worktrees and existing user edits. Do not reset, overwrite
or run a constructor directly on the saved routed PCB. Test a fresh candidate,
check source hashes before adoption, and keep reversible originals under .work.

Every electrical ECO must update schematic, native PCB, local libraries, exact
BOM identity, sourcing gaps and deterministic replay together. Require both
current and immutable-baseline rebuild DRC/open/parity/ERC 0/0/0/0, independent
functional pin/variant checks, 60-pin interface and unchanged-rule checks before
adoption. Do not remove required ICs, relax DRC or invent catalog codes to pass.
Run `release_split_c1.py --target split-c1` explicitly. Thin7 remains a separate
uncompleted mechanical requirement, not an export gate for this bench prototype.

Mainland-manufacturer identity does not certify module internal die provenance,
firmware correctness, accepted supply, USB compliance or physical EVT. The PG
supervisor is informational, not MCU reset; XL9535 P14 must stay input. The REGN
PSEL divider selects a nominal reset limit, not a firmware-independent ceiling.
Keep these limitations in engineering handoffs and generated manufacturing data.

Generated .work trials, production ZIPs/Gerbers/BOMs and native temporary outputs
stay untracked. Commit reproducible source, exact contracts, tests and concise
verification evidence. Never place synthetic supplier receipts into real data.

The hardware-finish checkpoint is documented in SPLIT-C1-HARDWARE-FINISH.md.
P05 is now active-high CHG_REQUEST, P15 is unused/input, and native GPIO2 through
R931 provides the direct FL_HWEN/charger permit. Never reintroduce the old
active-low P05 policy or expander-driven HWEN. TP19 can be grounded manually;
there is no claimed autonomous watchdog. Replay `_split_c1_hardware_finish_eco.py`
after the prior power ECO and require its independent pin/land/identity checks.

## Generated-output Git policy — user instruction 2026-10-04

Do NOT commit or push generated or intermediate render deliverables without
explicit user authorization for those artifacts. Rendering, viewing, or delivering
a result is not permission to put it in Git. This includes rendered PNG/JPEG,
MP4/GIF, frame sequences, generated Blender/GLB exports, preview galleries,
render manifests/checksums, and disposable scripts stored with those outputs.

Keep render output under ignored `/.work/` or `/visualization/`, or another
user-designated delivery location. Never use a source-code repository as a file
transfer workaround. Reusable rendering source belongs in a reviewed source
location separately from generated assets. Native PCB/schematic libraries and
required source contracts remain versioned according to the existing CAD policy.

Inspect the exact staged paths and diff before any commit; do not broadly stage
an output directory or force-add ignored render files. Preserve local deliverables
when removing them from tracking. Do not rewrite pushed history, delete remote
branches, or force-push as a cleanup shortcut without explicit authorization.

## Canonical checkout and integration branch

Continue the validated Split-C1 in `/Users/isaac/workspace/AI/panda-standard-board`
on `develop`. This branch starts from merged main `be0ef37`, not the discarded
Thin7/R2 or media-only branch. Worktree cleanup archives stay outside this repo.
Keep the existing untracked `packaging/` untouched. Reusable renderer code may
be reviewed as source; output goes to an external delivery directory or `.work`.

Fresh verification JSON, native interface measurements and release-candidate reports
are generated outputs and explicitly ignored. Run the release pipeline to recreate
them; do not force-add them. Source replay plans, precise BOM/part contracts, tests
and handoffs remain versioned. Keep any actual supplier receipts separately from
synthetic tests, and never mark them received based on a public catalog page.
