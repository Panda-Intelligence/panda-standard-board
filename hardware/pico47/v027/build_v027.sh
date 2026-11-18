#!/bin/zsh
# build_v027.sh: v0.2.6 board -> v0.2.7 project (1.45 mm microSD socket, 0805 front-light capacitor). Work files in .work/v027.
set -e
R=${0:A:h:h:h:h}; W=$R/.work/v027; H=$R/hardware/pico47; P=$H/v0.2.7; B=$H/v0.2.6
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$R/.work/wxshim:$H/v027 PANDA47_VARIANT=v027
q() { grep -v -E "traits|Debug|GetWidth called|memory leak" || true; }
mkdir -p $W/b && cd $W
python3 $H/v020/make_netlist_v020.py $R/.work/v020/r50.json $R/.work/v020/r49.json netlist_v027.json
rm -rf lib && cp -R $B/Panda47v2.pretty lib
for n in a r p w s h; do sed 's/Panda47-v026/Panda47-v027/g' $B/Panda47-v026.kicad_pro > b/$n.kicad_pro; done
$PY $H/v027/eco_sd.py $B/Panda47-v026.kicad_pcb netlist_v027.json b/a.kicad_pcb $W/lib $H/v026/v026_silk.json $H/v027/v027_silk.json 2>&1 | q
$PY $H/r25_router/export_geom.py b/a.kicad_pcb b/geom.json 2>&1 | q | tail -1
ASTAR_LIB=$R/.work/v020/tools/libastar3.dylib $R/.work/venv-router/bin/python $H/v020/router_v020.py b/geom.json $H/v027/spec_sd.json b/routed.json 2>&1 | tail -1
$PY $H/v020/apply_router_v020.py b/a.kicad_pcb b/routed.json b/r.kicad_pcb 2>&1 | q
$PY $H/v027/prune_stubs.py b/r.kicad_pcb b/p.kicad_pcb SD_D0 SD_D1 SD_D2 SD_D3 SD_CMD SD_CLK SD_CD 3V3_SD P47_VCOM_EN 2>&1 | q
PANDA47_WIDEN_ONLY=3V3_SD $PY $H/v023/widen_v023.py b/p.kicad_pcb b/w.kicad_pcb 2>&1 | q | tail -1
$PY $H/v020/silk_v020.py b/w.kicad_pcb b/s.kicad_pcb 2>&1 | q
$PY $H/v020/info_silk_v02x.py b/s.kicad_pcb $H/v027/v027_silk.json b/h.kicad_pcb 2>&1 | q
rm -rf $P/_sch_build $P/Panda47v2.pretty && mkdir -p $P && cp b/h.kicad_pcb $P/Panda47-v027.kicad_pcb && cp -R lib $P/Panda47v2.pretty
cp $B/fp-lib-table $B/sym-lib-table $P/ && cp b/a.kicad_pro $P/Panda47-v027.kicad_pro
PANDA47_FP_DIR=$P/Panda47v2.pretty python3 $H/v020/build_v020_sch.py netlist_v027.json $P 2>&1 | tail -1
$PY $H/v020/sync_board_sch_v020.py $P 2>&1 | q | tail -1
PANDA47_FP_DIR=$P/Panda47v2.pretty $PY $H/v020/set_fields_v020.py netlist_v027.json $P/Panda47-v027.kicad_pcb 2>&1 | q | tail -1
rm -rf $P/_sch_build; cd $P
$K sch erc --format json --severity-all --output $W/erc.json Panda47-v027.kicad_sch >/dev/null 2>&1 || true
$K pcb drc --format json --severity-all --schematic-parity --output $W/drc.json Panda47-v027.kicad_pcb >/dev/null 2>&1 || true
rm -f $P/*.kicad_prl
python3 -c "
import json,collections;e=json.load(open('$W/erc.json'));d=json.load(open('$W/drc.json'))
print('ERC',sum(len(s.get('violations',[])) for s in e.get('sheets',[])),'DRC',len(d['violations']),collections.Counter(v['type'] for v in d['violations']).most_common(5),'unconnected',len(d['unconnected_items']),'parity',len(d.get('schematic_parity',[])))
for x in d.get('schematic_parity',[])[:8]: print('  ',x['description'][:90])
for x in d['violations'][:10]: print('  ',x['type'],x['description'][:70],[(i['description'][:36],round(i['pos']['x'],1),round(i['pos']['y'],1)) for i in x['items']])
for x in d['unconnected_items'][:8]: print('  unconnected',[(i['description'][:40],round(i['pos']['x'],1),round(i['pos']['y'],1)) for i in x['items']])"
