#!/bin/zsh
# build_v030.sh: v0.2.4 board -> v0.3.0 project (4.26-inch SPI panel). Work files go to .work/v030, the project to v0.3.0/.
# Needs .work/v020/r50.json, r49.json, tools/libastar3.dylib, .work/venv-router and .work/wxshim (same as the v0.2.x builds).
set -e
R=${0:A:h:h:h:h}; W=$R/.work/v030; H=$R/hardware/pico47; P=$H/v0.3.0
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$R/.work/wxshim:$H/v030 PANDA47_VARIANT=v030 PANDA47_FP_DIR=$W/lib
q() { grep -v -E "traits|Debug|GetWidth called|memory leak" || true; }
drc() { $K pcb drc --format json --severity-all --output ${1:r}.drc.json $1 >/dev/null 2>&1 || true
        python3 -c "import json,collections,sys;d=json.load(open(sys.argv[1]));print('  DRC',collections.Counter(v['type'] for v in d['violations']).most_common(8),'unconnected',len(d['unconnected_items']))" ${1:r}.drc.json; }
B=$H/v0.2.4
mkdir -p $W/s $W/final && cd $W
python3 $H/v020/make_netlist_v020.py $R/.work/v020/r50.json $R/.work/v020/r49.json netlist_v030.json
rm -rf lib && cp -R $B/Panda47v2.pretty lib
for n in s/a s/b s/c s/d s/r final/f final/p final/w final/s final/h; do cp $B/Panda47-v024.kicad_pro $n.kicad_pro; done
# 1. strip the SY7636A block and the 40-pin connector, prune their feed branches
$PY $H/v030/eco_strip.py $B/Panda47-v024.kicad_pcb netlist_v030.json s/a.kicad_pcb 2>&1 | q | grep -E "bridge|removed"
$PY $H/v030/prune_stubs.py s/a.kicad_pcb s/b.kicad_pcb VSYS_RAW 3V3_AON I2C_SCL I2C_SDA 2>&1 | q
# 2. place the panel connector and boost stage (hand copper), prune again
$PY $H/v030/eco_display.py s/b.kicad_pcb netlist_v030.json s/c.kicad_pcb $W/lib 2>&1 | q | grep -i "via\|error\|assert"
$PY $H/v030/prune_stubs.py s/c.kicad_pcb s/d.kicad_pcb VSYS_RAW 3V3_AON I2C_SCL I2C_SDA 3V3_SD CHIP_PU_MCU FL_FB 2>&1 | q
# 3. grid router: panel signals and rails, strap pull-downs, CHIP_PU, FL_FB, the status-LED feed
$PY $H/r25_router/export_geom.py s/d.kicad_pcb s/geom.json 2>&1 | q | tail -1
ASTAR_LIB=$R/.work/v020/tools/libastar3.dylib $R/.work/venv-router/bin/python $H/v020/router_v020.py s/geom.json $H/v030/spec_display.json s/routed.json 2>&1 | tail -1
$PY $H/v020/apply_router_v020.py s/d.kicad_pcb s/routed.json s/r.kicad_pcb 2>&1 | q; drc s/r.kicad_pcb
# 4. stubs, widening, silkscreen, title block
$PY $H/v030/finish_v030.py s/r.kicad_pcb final/f.kicad_pcb $H/v024/v024_silk.json $H/v030/v030_silk.json 2>&1 | q
$PY $H/v030/prune_stubs.py final/f.kicad_pcb final/p.kicad_pcb 3V3_AON VSYS_RAW 2>&1 | q
$PY $H/v023/widen_v023.py final/p.kicad_pcb final/w.kicad_pcb 2>&1 | q | tail -1
$PY $H/v020/silk_v020.py final/w.kicad_pcb final/s.kicad_pcb 2>&1 | q
$PY $H/v020/info_silk_v02x.py final/s.kicad_pcb $H/v030/v030_silk.json final/h.kicad_pcb 2>&1 | q; drc final/h.kicad_pcb
# 5. project: schematic from the netlist, parity sync, fields, native checks
rm -rf $P/_sch_build $P/Panda47v2.pretty && mkdir -p $P && cp final/h.kicad_pcb $P/Panda426-v030.kicad_pcb && cp -R lib $P/Panda47v2.pretty
cp $B/fp-lib-table $B/sym-lib-table $P/
python3 - $B/Panda47-v024.kicad_pro $P/Panda426-v030.kicad_pro <<'PYE'
import json, sys
d = json.load(open(sys.argv[1]))
pats = [p for p in d['net_settings']['netclass_patterns'] if not p['pattern'].startswith('P47_')]
pats += [{'netclass': 'Power', 'pattern': 'EPD_LX'}] + [{'netclass': 'HV', 'pattern': p} for p in
         ('EPD_PREVGH', 'EPD_PREVGL', 'EPD_PUMP', 'EPD_VSH1', 'EPD_VSH2', 'EPD_VSL', 'EPD_VCOM')]
d['net_settings']['netclass_patterns'] = pats
open(sys.argv[2], 'w').write(json.dumps(d, indent=2).replace('Panda47-v024', 'Panda426-v030'))
PYE
PANDA47_FP_DIR=$P/Panda47v2.pretty python3 $H/v020/build_v020_sch.py netlist_v030.json $P 2>&1 | tail -1
$PY $H/v020/sync_board_sch_v020.py $P 2>&1 | q | tail -1
$PY $H/v020/set_fields_v020.py netlist_v030.json $P/Panda426-v030.kicad_pcb 2>&1 | q | tail -1
rm -rf $P/_sch_build; cd $P
$K sch erc --format json --severity-all --output $W/erc.json Panda426-v030.kicad_sch >/dev/null 2>&1 || true
$K pcb drc --format json --severity-all --schematic-parity --output $W/drc.json Panda426-v030.kicad_pcb >/dev/null 2>&1 || true
rm -f $P/*.kicad_prl
python3 -c "
import json;e=json.load(open('$W/erc.json'));d=json.load(open('$W/drc.json'))
print('ERC',sum(len(s.get('violations',[])) for s in e.get('sheets',[])),'DRC',len(d['violations']),'unconnected',len(d['unconnected_items']),'parity',len(d.get('schematic_parity',[])))"
