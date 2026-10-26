#!/bin/zsh
# usage: loop.sh GEOM BASESPEC START_LEGAL_STATE TAG [CYCLES]
# repeat: warm PathFinder (with group reassignment) -> vertex-cover legalize -> polish; keep the global best legal state
cd "${R25_WORK:?set R25_WORK to the ignored working directory (it holds tools/, runs/ and the geometries)}"
PY=(nice -n 10 ${R25_PY:-python3})
GEOM=$1; BASE=$2; BEST=runs/loop-$4-best.json; TAG=$4; N=${5:-12}
cp $3 $BEST
count() { python3 -c "import json;d=json.load(open('$1'));print(len(d['committed']))"; }
for i in $(seq 1 $N); do
  python3 -c "import json;s=json.load(open('$BASE'));[s.pop(k,None) for k in ('legalize_from','polish_from','warm_from','region_from','finalize_from','diagnose_from')];s.update(warm_from='$BEST',warm_reassign=True,iterations=25);json.dump(s,open('runs/spec-$TAG-w.json','w'))"
  "${PY[@]}" tools/router5.py $GEOM runs/spec-$TAG-w.json runs/design-r24.json runs/route-$TAG-w.json > runs/loop-$TAG-w.log 2>&1
  python3 -c "import json;s=json.load(open('$BASE'));[s.pop(k,None) for k in ('legalize_from','polish_from','warm_from','region_from','finalize_from','diagnose_from')];s.update(legalize_from='runs/route-$TAG-w.json.last',max_steps=40);json.dump(s,open('runs/spec-$TAG-l.json','w'))"
  "${PY[@]}" tools/router5.py $GEOM runs/spec-$TAG-l.json runs/design-r24.json runs/route-$TAG-l.json > runs/loop-$TAG-l.log 2>&1
  python3 -c "import json;s=json.load(open('$BASE'));[s.pop(k,None) for k in ('legalize_from','polish_from','warm_from','region_from','finalize_from','diagnose_from')];s.update(polish_from='runs/route-$TAG-l.json');json.dump(s,open('runs/spec-$TAG-p.json','w'))"
  "${PY[@]}" tools/router5.py $GEOM runs/spec-$TAG-p.json runs/design-r24.json runs/route-$TAG-p.json > runs/loop-$TAG-p.log 2>&1
  new=$(count runs/route-$TAG-p.json); old=$(count $BEST)
  if [ $new -gt $old ]; then cp runs/route-$TAG-p.json $BEST; fi
  echo "cycle $i: polish $new legal (best before $old) $(date +%H:%M)"
  if python3 -c "import json,sys;d=json.load(open('$BEST'));sys.exit(0 if d.get('complete') else 1)"; then echo LOOP-COMPLETE; break; fi
done
echo LOOP-DONE best $(count $BEST)
