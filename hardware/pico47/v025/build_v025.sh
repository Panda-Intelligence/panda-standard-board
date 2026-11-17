#!/bin/zsh
# build_v025.sh: v0.2.4 board -> v0.2.5 project (E09 review fixes). Work files in .work/v025, project in v0.2.5/.
set -e
R=${0:A:h:h:h:h}; W=$R/.work/v025; H=$R/hardware/pico47; P=$H/v0.2.5; B=$H/v0.2.4
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$R/.work/wxshim:$H/v025 PANDA47_VARIANT=v025 PANDA47_FP_DIR=$B/Panda47v2.pretty
q() { grep -v -E "traits|Debug|GetWidth called|memory leak" || true; }
mkdir -p $W/b && cd $W
python3 $H/v020/make_netlist_v020.py $R/.work/v020/r50.json $R/.work/v020/r49.json netlist_v025.json
for n in a b r f s h; do cp $B/Panda47-v024.kicad_pro b/$n.kicad_pro; done
$PY $H/v025/eco_review.py $B/Panda47-v024.kicad_pcb netlist_v025.json b/a.kicad_pcb $PANDA47_FP_DIR 180 0 2>&1 | q
$PY $H/v025/prune_stubs.py b/a.kicad_pcb b/b.kicad_pcb BQ_TS 2>&1 | q
$PY $H/r25_router/export_geom.py b/b.kicad_pcb b/geom.json 2>&1 | q | tail -1
ASTAR_LIB=$R/.work/v020/tools/libastar3.dylib $R/.work/venv-router/bin/python $H/v020/router_v020.py b/geom.json $H/v025/spec_review.json b/routed.json 2>&1 | tail -1
$PY $H/v020/apply_router_v020.py b/b.kicad_pcb b/routed.json b/r.kicad_pcb 2>&1 | q
$PY $H/v025/finish_v025.py b/r.kicad_pcb b/f.kicad_pcb $H/v024/v024_silk.json $H/v025/v025_silk.json 2>&1 | q
$PY $H/v020/silk_v020.py b/f.kicad_pcb b/s.kicad_pcb 2>&1 | q
$PY $H/v020/info_silk_v02x.py b/s.kicad_pcb $H/v025/v025_silk.json b/h.kicad_pcb 2>&1 | q
rm -rf $P/_sch_build $P/Panda47v2.pretty && mkdir -p $P && cp b/h.kicad_pcb $P/Panda47-v025.kicad_pcb && cp -R $B/Panda47v2.pretty $P/
cp $B/fp-lib-table $B/sym-lib-table $P/ && sed 's/Panda47-v024/Panda47-v025/g' $B/Panda47-v024.kicad_pro > $P/Panda47-v025.kicad_pro
PANDA47_FP_DIR=$P/Panda47v2.pretty python3 $H/v020/build_v020_sch.py netlist_v025.json $P 2>&1 | tail -1
$PY $H/v020/sync_board_sch_v020.py $P 2>&1 | q | tail -1
$PY $H/v020/set_fields_v020.py netlist_v025.json $P/Panda47-v025.kicad_pcb 2>&1 | q | tail -1
rm -rf $P/_sch_build; cd $P
$K sch erc --format json --severity-all --output $W/erc.json Panda47-v025.kicad_sch >/dev/null 2>&1 || true
$K pcb drc --format json --severity-all --schematic-parity --output $W/drc.json Panda47-v025.kicad_pcb >/dev/null 2>&1 || true
rm -f $P/*.kicad_prl
python3 -c "
import json,collections;e=json.load(open('$W/erc.json'));d=json.load(open('$W/drc.json'))
print('ERC',sum(len(s.get('violations',[])) for s in e.get('sheets',[])),'DRC',len(d['violations']),collections.Counter(v['type'] for v in d['violations']).most_common(5),'unconnected',len(d['unconnected_items']),'parity',len(d.get('schematic_parity',[])))
for x in d.get('schematic_parity',[])[:8]: print('  ',x['description'][:90])
for x in d['violations'][:8]: print('  ',x['type'],x['description'][:70],[(i['description'][:36],round(i['pos']['x'],1),round(i['pos']['y'],1)) for i in x['items']])"
