#!/bin/zsh
# 生成隔离 E26 试验板。用法：trial.sh GEOM BASESPEC LEGAL_STATE TAG
# 仅供工程诊断；器件料号、原理图和最终引脚表仍须独立确认。
set -eu
setopt pipefail
SCRIPT_DIR=${0:A:h}
cd "${R25_WORK:?set R25_WORK to the ignored working directory}"
PY=${R25_PY:-python3}
KPY=${KICAD_PY:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3}
K=${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
STOCK=${KICAD_FOOTPRINTS:-/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints}
DESIGN=${R25_DESIGN:-$SCRIPT_DIR/../../design.json}
[[ $# == 4 ]] || { print -u2 'usage: trial.sh GEOM BASESPEC LEGAL_STATE TAG'; exit 2; }
GEOM=$1; BASE=$2; STATE=$3; TAG=$4
[[ $TAG =~ '^[A-Za-z0-9_-]+$' ]] || { print -u2 'invalid tag'; exit 2; }
[[ -f $DESIGN ]] || { print -u2 "R25 design contract not found: $DESIGN"; exit 2; }
TRIAL=trial-$TAG
FIN=geom-$TAG-final.json
[[ ! -e $TRIAL && ! -e $FIN && ! -e runs/spec-fin-$TAG.json ]] || { print -u2 'trial output already exists'; exit 2; }

# E26 另外移动 C501/C523，必须与 E6 移位合并；冲突时拒绝覆盖。
$PY - "$BASE" "$STATE" "$FIN" "runs/spec-fin-$TAG.json" "runs/moves-$TAG.json" <<'PY'
import json, sys
base, state, final, spec_out, moves_out = sys.argv[1:]
with open(base) as f: spec = json.load(f)
for key in ('legalize_from', 'polish_from', 'warm_from', 'region_from', 'finalize_from', 'diagnose_from'):
    spec.pop(key, None)
spec.update(finalize_from=state, finalize_to=final)
with open(spec_out, 'x') as f: json.dump(spec, f)
with open('runs/moves-E6.json') as f: moves = json.load(f)
with open('runs/moves-e24.json') as f: additional = json.load(f)
if moves.keys() & additional.keys(): raise ValueError('duplicate move refs')
moves.update(additional)
with open(moves_out, 'x') as f: json.dump(moves, f)
PY
nice -n 15 "$PY" tools/router5.py "$GEOM" "runs/spec-fin-$TAG.json" "$DESIGN" "runs/fin-$TAG.json" > "runs/fin-$TAG.log" 2>&1
nice -n 15 "$PY" tools/exact_check.py "$FIN" geom-r24.json > "runs/exact-$TAG.log" 2>&1
cp -R base-r24 "$TRIAL"
nice -n 10 "$KPY" tools/apply_final.py base-r24/Core.kicad_pcb geom-r24.json "$FIN" "runs/moves-$TAG.json" "$TRIAL/Core.kicad_pcb" > "$TRIAL/apply.log" 2>&1
nice -n 10 "$KPY" "$SCRIPT_DIR/replace_c501_trial.py" "$TRIAL/Core.kicad_pcb" "$STOCK/Capacitor_SMD.pretty" "$TRIAL/Panda47.pretty" > "$TRIAL/footprint.log" 2>&1
nice -n 10 "$KPY" tools/export_geom.py "$TRIAL/Core.kicad_pcb" "$TRIAL/geometry.json" > "$TRIAL/export.log" 2>&1
nice -n 15 "$PY" "$SCRIPT_DIR/compare_trial_geometry.py" "$FIN" "$TRIAL/geometry.json" | tee "$TRIAL/geometry-check.log"
# 保留所有原有铜，不能用未连总数判断删除是否安全。
nice -n 10 "$KPY" tools/kicad_split_tees.py "$TRIAL/Core.kicad_pcb" > "$TRIAL/split.log" 2>&1
nice -n 10 "$K" pcb drc --refill-zones --save-board --schematic-parity --severity-all --format json -o "$TRIAL/d.json" "$TRIAL/Core.kicad_pcb" > "$TRIAL/drc.log" 2>&1
nice -n 10 "$KPY" tools/kicad_zone_islands.py "$TRIAL/Core.kicad_pcb" > "$TRIAL/zones.log" 2>&1
nice -n 10 "$KPY" "$SCRIPT_DIR/check_trial_ground.py" "$TRIAL" "$TRIAL/ground.json" > "$TRIAL/ground.log" 2>&1 || true
"$PY" - "$TRIAL/d.json" "runs/exact-$TAG.log" "$TRIAL/ground.json" <<'PY'
import collections, json, sys
with open(sys.argv[1]) as f: report = json.load(f)
with open(sys.argv[2]) as f: exact = f.read().splitlines()
with open(sys.argv[3]) as f: ground = json.load(f)
violations = collections.Counter((v['severity'], v['type']) for v in report['violations'])
print('unconnected', len(report['unconnected_items']), 'violations', dict(violations))
print('schematic parity', len(report['schematic_parity']))
print('exact check:', exact[-1] if exact else 'missing')
print('complete ground:', ground['result'].get('complete'))
print('试验结果；仍需完整地、旧网络组、原理图及器件资格检查。')
if not ground['result'].get('complete') or not exact or exact[-1] != '0 issues' or report['unconnected_items'] or report['schematic_parity'] or any(v['severity'] in ('error', 'warning') for v in report['violations']):
    sys.exit(1)
PY
