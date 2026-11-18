#!/bin/zsh
# build_v029.sh: v0.2.8 board -> v0.2.9 project (E0470A03 panel on a 34-pin connector, two front-light drivers).
# Work files in .work/v029. Needs .work/v020/r50.json, r49.json, tools/libastar3.dylib, .work/venv-router and .work/wxshim.
set -e -o pipefail
R=${0:A:h:h:h:h}; W=$R/.work/v029; H=$R/hardware/pico47; P=$H/v0.2.9; B=$H/v0.2.8
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$R/.work/wxshim:$H/v029 PANDA47_VARIANT=v029
q() { grep -v -E "traits|Debug|GetWidth called|memory leak" || true; }
PR=(P47_VGL P47_VGH P47_VPOS P47_VNEG P47_VCOM 3V3_AON VSYS_RAW I2C_SDA I2C_SCL I2S_DIN BAT_PACKP BAT_CONN_P P47_XCL_SRC)
rm -rf $W/b && mkdir -p $W/b && cd $W
python3 $H/v020/make_netlist_v020.py $R/.work/v020/r50.json $R/.work/v020/r49.json netlist_v029.json
rm -rf lib && cp -R $B/Panda47v2.pretty lib && python3 $H/v029/make_fp_v029.py lib
python3 - $B/Panda47-v028.kicad_pro b/a.kicad_pro <<'PYE'
import json, sys
d = json.load(open(sys.argv[1])); out = []
ren = {'FL_SW': ('FL_W_SW', 'FL_C_SW'), 'FL_VOUT': ('FL_W_P', 'FL_C_P'), 'FL_W_N': ('FL_W_FB',), 'FL_C_N': ('FL_C_FB',), 'FL_FB': ()}
for p in d['net_settings']['netclass_patterns']:
    out += [dict(p, pattern=n) for n in ren[p['pattern']]] if p['pattern'] in ren else [p]
d['net_settings']['netclass_patterns'] = out
open(sys.argv[2], 'w').write(json.dumps(d, indent=2).replace('Panda47-v028', 'Panda47-v029'))
PYE
for n in e x r g m t f w d s h; do cp b/a.kicad_pro b/$n.kicad_pro; done
# 1. placement: connector, buck, gauge, front-light stages (hand copper for the hot loops)
$PY $H/v029/eco_a03.py $B/Panda47-v028.kicad_pcb netlist_v029.json b/e.kicad_pcb $W/lib 2>&1 | q | grep -v "^footprint"
$PY $H/v029/prune_stubs.py b/e.kicad_pcb b/x.kicad_pcb $PR 2>&1 | q | cut -c1-120
# 2. grid router
$PY $H/r25_router/export_geom.py b/x.kicad_pcb b/geom.json 2>&1 | q | tail -1
ASTAR_LIB=$R/.work/v020/tools/libastar3.dylib $R/.work/venv-router/bin/python $H/v020/router_v020.py b/geom.json $H/v029/spec_a03.json b/routed.json 2>&1 | tail -1
$PY $H/v020/apply_router_v020.py b/x.kicad_pcb b/routed.json b/r.kicad_pcb 2>&1 | q
# 3. ground returns, dead ends, widening, silkscreen, title block
$PY $H/v029/eco_gnd.py b/r.kicad_pcb b/g.kicad_pcb 2>&1 | q
$PY $H/v029/fix_thermals.py b/g.kicad_pcb b/m.kicad_pcb 2>&1 | q
$PY $H/v029/trim_dangling.py b/m.kicad_pcb b/t.kicad_pcb 2>&1 | q
$PY $H/v029/finish_v029.py b/t.kicad_pcb b/f.kicad_pcb $H/v028/v028_silk.json $H/v029/v029_silk.json 2>&1 | q
PANDA47_WIDEN_ONLY=3V3_AON,VSYS_RAW,P47_VGL,P47_VGH,P47_VPOS,P47_VNEG,P47_VCOM,FL_W_P,FL_C_P $PY $H/v023/widen_v023.py b/f.kicad_pcb b/w.kicad_pcb 2>&1 | q | tail -1
$PY $H/v029/trim_dangling.py b/w.kicad_pcb b/d.kicad_pcb 2>&1 | q          # the widening pass can leave a via without its track
$PY $H/v020/silk_v020.py b/d.kicad_pcb b/s.kicad_pcb 2>&1 | q
$PY $H/v020/info_silk_v02x.py b/s.kicad_pcb $H/v029/v029_silk.json b/h.kicad_pcb 2>&1 | q
# 4. project: schematic from the netlist, parity sync, fields, native checks
rm -rf $P && mkdir -p $P && cp b/h.kicad_pcb $P/Panda47-v029.kicad_pcb && cp -R lib $P/Panda47v2.pretty
cp $B/fp-lib-table $B/sym-lib-table $P/ && cp b/a.kicad_pro $P/Panda47-v029.kicad_pro
PANDA47_FP_DIR=$P/Panda47v2.pretty python3 $H/v020/build_v020_sch.py netlist_v029.json $P 2>&1 | tail -1
$PY $H/v020/sync_board_sch_v020.py $P 2>&1 | q | tail -1
PANDA47_FP_DIR=$P/Panda47v2.pretty $PY $H/v020/set_fields_v020.py netlist_v029.json $P/Panda47-v029.kicad_pcb 2>&1 | q | tail -1
rm -rf $P/_sch_build; cd $P
$K sch erc --format json --severity-all --output $W/erc.json Panda47-v029.kicad_sch >/dev/null 2>&1 || true
$K pcb drc --format json --severity-all --schematic-parity --output $W/drc.json Panda47-v029.kicad_pcb >/dev/null 2>&1 || true
rm -f $P/*.kicad_prl
python3 -c "
import json,collections;e=json.load(open('$W/erc.json'));d=json.load(open('$W/drc.json'))
print('ERC',sum(len(s.get('violations',[])) for s in e.get('sheets',[])),'DRC',len(d['violations']),collections.Counter(v['type'] for v in d['violations']).most_common(6),'unconnected',len(d['unconnected_items']),'parity',len(d.get('schematic_parity',[])))
for x in d.get('schematic_parity',[])[:10]: print('  ',x['description'][:110])
for x in d['violations'][:14]: print('  ',x['type'],x['description'][:60],[(i['description'][:36],round(i['pos']['x'],1),round(i['pos']['y'],1)) for i in x['items']])
for x in d['unconnected_items'][:8]: print('  unconnected',[(i['description'][:40],round(i['pos']['x'],1),round(i['pos']['y'],1)) for i in x['items']])
for s in e.get('sheets',[]):
    for x in s.get('violations',[])[:8]: print('  erc',x['type'],x['description'][:90],[i['description'][:40] for i in x.get('items',[])][:2])"
