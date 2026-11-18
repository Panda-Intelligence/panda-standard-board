#!/bin/zsh
# build_v031.sh: v0.2.8 board -> v0.3.1 project (4.26-inch SPI panel with front light and touch). Work files in .work/v031.
# Needs .work/v020/r50.json, r49.json, tools/libastar3.dylib, .work/venv-router and .work/wxshim (same as the v0.2.x builds).
set -e -o pipefail
R=${0:A:h:h:h:h}; W=$R/.work/v031; H=$R/hardware/pico47; P=$H/v0.3.1; B=$H/v0.2.8
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$R/.work/wxshim:$H/v031 PANDA47_VARIANT=v031
q() { grep -v -E "traits|Debug|GetWidth called|memory leak" || true; }
NETS=(VSYS_RAW 3V3_AON I2C_SCL I2C_SDA 3V3_SD CHIP_PU_MCU FL_FB TOUCH_INT TOUCH_RST FL_VOUT FL_W_N FL_C_N KEY_POWER VDD_SPI FLASH_CS FLASH_Q FLASH_WP FLASH_D FLASH_CLK FLASH_HD)
rm -rf $W/b && mkdir -p $W/b && cd $W
python3 $H/v020/make_netlist_v020.py $R/.work/v020/r50.json $R/.work/v020/r49.json netlist_v031.json
rm -rf lib && cp -R $B/Panda47v2.pretty lib && cp $H/v0.3.0/Panda47v2.pretty/{FPC_XKB_X05A10L24G,SOT-323_SC-70,R_0603_1608Metric}.kicad_mod lib/
python3 - $B/Panda47-v028.kicad_pro b/a.kicad_pro <<'PYE'
import json, sys
d = json.load(open(sys.argv[1]))
pats = [p for p in d['net_settings']['netclass_patterns'] if not p['pattern'].startswith('P47_')]
pats += [{'netclass': 'Power', 'pattern': 'EPD_LX'}] + [{'netclass': 'HV', 'pattern': p} for p in
         ('EPD_PREVGH', 'EPD_PREVGL', 'EPD_PUMP', 'EPD_VSH1', 'EPD_VSH2', 'EPD_VSL', 'EPD_VCOM')]
d['net_settings']['netclass_patterns'] = pats
open(sys.argv[2], 'w').write(json.dumps(d, indent=2).replace('Panda47-v028', 'Panda426-v031'))
PYE
for n in t u d c x r f p w s h; do cp b/a.kicad_pro b/$n.kicad_pro; done
# 1. strip the SY7636A block and the 40-pin connector, prune their feed branches
$PY $H/v031/eco_strip.py $B/Panda47-v028.kicad_pcb netlist_v031.json b/t.kicad_pcb 2>&1 | q | grep -E "bridge|removed"
$PY $H/v031/prune_stubs.py b/t.kicad_pcb b/u.kicad_pcb VSYS_RAW 3V3_AON I2C_SCL I2C_SDA 2>&1 | q
# 2. panel connector and boost stage (hand copper), then the front-light and touch connectors
$PY $H/v031/eco_display.py b/u.kicad_pcb netlist_v031.json b/d.kicad_pcb $W/lib 2>&1 | q | grep -i "error\|assert" || true
$PY $H/v031/eco_conn.py b/d.kicad_pcb netlist_v031.json b/c.kicad_pcb $W/lib 2>&1 | q
$PY $H/v031/prune_stubs.py b/c.kicad_pcb b/x.kicad_pcb $NETS 2>&1 | q
# 3. grid router
$PY $H/r25_router/export_geom.py b/x.kicad_pcb b/geom.json 2>&1 | q | tail -1
ASTAR_LIB=$R/.work/v020/tools/libastar3.dylib $R/.work/venv-router/bin/python $H/v020/router_v020.py b/geom.json $H/v031/spec_display.json b/routed.json 2>&1 | tail -1
$PY $H/v020/apply_router_v020.py b/x.kicad_pcb b/routed.json b/r.kicad_pcb 2>&1 | q
# 4. widening, silkscreen, title block
$PY $H/v031/finish_v031.py b/r.kicad_pcb b/f.kicad_pcb $H/v028/v028_silk.json $H/v031/v031_silk.json 2>&1 | q
# dead ends left after routing: removed from KiCad's own dangling report, checked against the unconnected count
$PY $H/v031/trim_dangling.py b/f.kicad_pcb b/p.kicad_pcb 2>&1 | q
PANDA47_WIDEN_ONLY=3V3_AON,3V3_SD,VDD_SPI,VSYS_RAW,FL_VOUT,EPD_VDD,EPD_PREVGH,EPD_PREVGL,EPD_VSH1,EPD_VSL,EPD_VCOM $PY $H/v023/widen_v023.py b/p.kicad_pcb b/w.kicad_pcb 2>&1 | q | tail -1
$PY $H/v020/silk_v020.py b/w.kicad_pcb b/s.kicad_pcb 2>&1 | q
$PY $H/v020/info_silk_v02x.py b/s.kicad_pcb $H/v031/v031_silk.json b/h.kicad_pcb 2>&1 | q
# 5. project: schematic from the netlist, parity sync, fields, native checks
rm -rf $P && mkdir -p $P && cp b/h.kicad_pcb $P/Panda426-v031.kicad_pcb && cp -R lib $P/Panda47v2.pretty
cp $B/fp-lib-table $B/sym-lib-table $P/ && cp b/a.kicad_pro $P/Panda426-v031.kicad_pro
PANDA47_FP_DIR=$P/Panda47v2.pretty python3 $H/v020/build_v020_sch.py netlist_v031.json $P 2>&1 | tail -1
$PY $H/v020/sync_board_sch_v020.py $P 2>&1 | q | tail -1
PANDA47_FP_DIR=$P/Panda47v2.pretty $PY $H/v020/set_fields_v020.py netlist_v031.json $P/Panda426-v031.kicad_pcb 2>&1 | q | tail -1
rm -rf $P/_sch_build; cd $P
$K sch erc --format json --severity-all --output $W/erc.json Panda426-v031.kicad_sch >/dev/null 2>&1 || true
$K pcb drc --format json --severity-all --schematic-parity --output $W/drc.json Panda426-v031.kicad_pcb >/dev/null 2>&1 || true
rm -f $P/*.kicad_prl
python3 -c "
import json,collections;e=json.load(open('$W/erc.json'));d=json.load(open('$W/drc.json'))
print('ERC',sum(len(s.get('violations',[])) for s in e.get('sheets',[])),'DRC',len(d['violations']),collections.Counter(v['type'] for v in d['violations']).most_common(5),'unconnected',len(d['unconnected_items']),'parity',len(d.get('schematic_parity',[])))
for x in d.get('schematic_parity',[])[:8]: print('  ',x['description'][:90])
for x in d['violations'][:12]: print('  ',x['type'],x['description'][:70],[(i['description'][:36],round(i['pos']['x'],1),round(i['pos']['y'],1)) for i in x['items']])
for x in d['unconnected_items'][:8]: print('  unconnected',[(i['description'][:40],round(i['pos']['x'],1),round(i['pos']['y'],1)) for i in x['items']])
for s in e.get('sheets',[]):
    for x in s.get('violations',[])[:6]: print('  erc',x['type'],x['description'][:80])"
