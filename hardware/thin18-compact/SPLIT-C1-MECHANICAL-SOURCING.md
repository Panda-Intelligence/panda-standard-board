# Split-C1 current mechanical and sourcing state
2026-10-02. Core-C1 + Display-C1,PCB design only;no physical samples.
Current source documents supersede older integrated-board studies in Git history.

| Item | Current state |
|---|---|
| Boards |Core96×68×0.8mm/4layers;Display45×36×0.8mm/2layers|
| Mating |HCTL DS/DP60pin pair;1.5mm nominal gap,physical maximum/tolerance fit pending|
| Interface |xCore=xDisplay+38,yCore=66−yDisplay,zCore=−1.5−zDisplay;all60pins verified|
| Domestic identity |155 populated refs,155 mainland,0 foreign/unknown;separate supply/qualification gates|
| SMT mapping |Core110/116,Display37/37;six Core exact IDs/consignment acceptance missing|
| Manual assembly |Core C301 horizontal1F cap after SMT;offboard Shiheng TH301|
| Main pack |complete54×36×5.5mm maximum budget;1100mAh nominal/900mAh minimum targets;no selected exact mainland pack|
| Enclosure |112×75×21mm engineering box;calculated thickness20.5mm;not released CAD/fit|
| RTC |SD3078+KAMCAP rechargeable cap;>=24h isolated backup target,physical testsNOT_RUN|

The side pack sits below Core B in[1,11,37,65];Display projects[38,30,83,66].
It is1mm apart in XY and avoids the static J503 body;its mated antenna cable
still needs a solid volume. Backside parts/bosses budget1.5mm plus0.3mm insulation,
pack5.5mm plus0.7mm swelling and rear wall0.8mm give rearZ−8.8mm.
Core0.8+front max6.5+mount0.2+panel clearance0.5+panel2.2+front wall0.8
give frontZ11.0mm;reserve0.7mm gives20.5mm,rounded enclosure box21mm. These are explicit engineering
allowances,not supplier-signed pack/panel/mounted maxima.

C301 KAMCAP SE-5R5-D105VYH3C/C2894294 has max diameter19.2mm/overall H6.5mm on Core F,20mm nominal pitch.
It is horizontal THT,mounted0.2mm above PCB and hand-soldered after SMT;
rear lead protrusion must be<=0.5mm. Both plated pads overlap Display XY and
must clear the opposite board/connector/solder/retention solids. Native
copper/hole clearances are checked;they do not verify Z clearance.
H804 must not receive a boss/fastener that enters the main battery.
Model exact FPC bending/latch/tool,USB/microSD travel,antennas,speaker,
supports and battery harness before releasing a case.

J301 is HCTL HC-HY-2AWT,2mm pitch,5.2mm body/5.5mm preliminary max budget.
Pack housing HC-HY-2Y/HC-HY-T,AWG26,100..120mm preliminary harness;pin1 BAT+.
TH301 is independent10k/B3435K Shiheng100mm harness;no unknown pack NTC parallel.
The EEMB historical52×34.5×5.3mm protected pack only screens body size:
imported JST connector,45mm wires,1A continuous PCM and unspecified chip origin
prevent adopting that old assembly as an all-mainland selected pack.

Existing0.2mm main power branches/vias still need current/temperature redesign
or an approved lower-current contract. Connector3A/5A ratings do not qualify
the whole PCB current path. Charge/current/thermal and startup/RCB conditions
remain after physical samples;approved limits/firmware are still required.
This is distinct from native DRC/parity/electrical continuity checks.

Six SMT positions/three procurement groups,net maps,prohibited substitutions and
unaccepted JLC IDs are in split-c1-smt-consignment.json.
Actual stock,MSL/lot/tape attrition,double-sided carrier panel and assembler
acceptance are pending. C301/H3C/C2894294 catalog is exact but current stock quantity is unverified;D202/C55274065 observation0;
read-only catalog results do not reserve supply. No orders/messages shipped.
Current plans and primary source links:
- SPLIT-C1-DOMESTICIZATION.md / split-c1-domestic-eco.json
- C4D8-RTC-DECISION.md / SPLIT-C1-RTC-FIRMWARE.md
- SPLIT-C1-PACK-INPUTS.md / SPLIT-C1-ENCLOSURE-STUDY.scad
- SPLIT-C1-PROCUREMENT-QUESTIONS.md / split-c1-sourcing-evidence.json
- JLC-PROTOTYPE-HANDOFF.md / split-c1-mechanical-audit.json

XTEINK X4 Pro1100mAh/5.95mm is a reference. No matched measured runtime or
5.95mm Panda fit is claimed. Q04–Q14 remainNOT_RUN;no physical EVT is invented.
