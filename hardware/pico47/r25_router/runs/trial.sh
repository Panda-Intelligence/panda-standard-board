#!/bin/zsh
# usage: trial.sh GEOM BASESPEC LEGAL_STATE TAG
# finalize a legal router state, rebuild a KiCad Core board from r24 into trial-TAG/, clean it and run DRC
cd "${R25_WORK:?set R25_WORK to the ignored working directory (it holds tools/, runs/ and the geometries)}"
PY=${R25_PY:-python3}
KPY=${KICAD_PY:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3}
K=${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
GEOM=$1; BASE=$2; STATE=$3; TAG=$4; FIN=geom-$TAG-final.json
set -e
python3 -c "import json;s=json.load(open('$BASE'));[s.pop(k,None) for k in ('legalize_from','polish_from','warm_from','region_from','diagnose_from')];s.update(finalize_from='$STATE',finalize_to='$FIN');json.dump(s,open('runs/spec-fin-$TAG.json','w'))"
$PY tools/router5.py $GEOM runs/spec-fin-$TAG.json runs/design-r24.json runs/fin-$TAG.json > runs/fin-$TAG.log 2>&1
$PY tools/exact_check.py $FIN geom-r24.json | tail -3
rm -rf trial-$TAG; cp -R base-r24 trial-$TAG
$KPY tools/apply_final.py base-r24/Core.kicad_pcb geom-r24.json $FIN runs/moves-E6.json trial-$TAG/Core.kicad_pcb 2>&1 | grep -v -e assert -e leak | tail -3
$KPY tools/kicad_split_tees.py trial-$TAG/Core.kicad_pcb 2>&1 | grep -v -e assert -e leak
$KPY tools/kicad_prune.py trial-$TAG/Core.kicad_pcb 2>&1 | grep -v -e assert -e leak | tail -2
$KPY tools/kicad_split_tees.py trial-$TAG/Core.kicad_pcb 2>&1 | grep -v -e assert -e leak
$K pcb drc --refill-zones --severity-all --format json -o trial-$TAG/d.json trial-$TAG/Core.kicad_pcb > /dev/null
python3 -c "
import json,collections;r=json.load(open('trial-$TAG/d.json'))
print('unconnected',len(r['unconnected_items']));print(dict(collections.Counter((v['severity'],v['type']) for v in r['violations'])))
[print('  ',[(i['description'][:45],i['pos']['x'],i['pos']['y']) for i in u['items']]) for u in r['unconnected_items']]
[print('  ERR',v['type'],[(i['description'][:45],i['pos']['x'],i['pos']['y']) for i in v['items']]) for v in r['violations'] if v['severity']=='error']"
$KPY tools/kicad_zone_islands.py trial-$TAG/Core.kicad_pcb 2>&1 | grep -v -e assert -e leak | grep -v "isolated ('track'"
