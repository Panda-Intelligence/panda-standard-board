#!/bin/zsh
# usage: run_v020.sh <out dir under .work/v020> [passes] [placement.json: skip the placer]
# netlist -> placement -> board -> DSN -> Freerouting -> SES -> zones -> DRC
set -e
REPO=${0:A:h:h:h:h}
W=$REPO/.work/v020
OUT=$W/$1
PASSES=${2:-40}
PLACE=${3:-}
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
J=$(ls -d $REPO/.work/tools/jdk-25*)/Contents/Home/bin/java
S=$REPO/hardware/pico47/v020
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/.work/wxshim
cd $W
python3 $S/make_netlist_v020.py r50.json r49.json netlist_v020.json
if [ -z "$PLACE" ]; then
  python3 $S/place_v020.py netlist_v020.json sizes.json r50.json anchors_v020.json placement_v020.json
  PLACE=placement_v020.json
fi
$PY $S/build_v020_pcb.py build netlist_v020.json $PLACE $OUT 2>&1 | grep -v traits
$PY $S/gnd_stitch_v020.py $OUT/Panda47-v020.kicad_pcb $OUT/Panda47-v020.kicad_pcb $OUT/gnd_stitch.json 2>&1 | grep -v traits
$PY $S/specctra_v020.py export $OUT/Panda47-v020.kicad_pcb $OUT/v020.dsn 2>&1 | grep -v traits
(cd $OUT && $J -Djava.awt.headless=true -jar $REPO/.work/tools/freerouting-2.5.0.jar --gui.enabled=false --router.automatic_neckdown=true --router.neck_width_um=127 \
    -de v020.dsn -do v020.ses -mp $PASSES -mt 8 > fr.log 2>&1)
$PY $S/specctra_v020.py import $OUT/Panda47-v020.kicad_pcb $OUT/v020.ses $OUT/Panda47-v020.kicad_pcb 2>&1 | grep -v traits
$K pcb drc --format json --severity-all --output $OUT/drc.json $OUT/Panda47-v020.kicad_pcb > $OUT/drc.log 2>&1 || true
python3 -c "
import json,collections;d=json.load(open('$OUT/drc.json'))
print('violations',collections.Counter(v['type'] for v in d['violations']).most_common(12))
print('unconnected',len(d['unconnected_items']))"
