# Full-product Split-C1 rendering

Use the canonical checkout on `develop`. Run the hardware release pipeline first;
it creates current interface/mechanical reports which are intentionally untracked.

```sh
python3 hardware/thin18-compact/release_split_c1.py --target split-c1
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
OUT=/Users/isaac/workspace/AI/panda-board-deliverables/split-c1-product
"$KPY" tools/render/export_split_c1_scene.py --output "$OUT/source"
python3 tools/render/verify_product_envelope.py --test
"$BLENDER" -b --factory-startup --python-exit-code 1 --python tools/render/build_product_scene.py -- --source "$OUT/source" --output "$OUT/render" --mode stills
"$BLENDER" -b --factory-startup --python-exit-code 1 --python tools/render/build_product_scene.py -- --source "$OUT/source" --output "$OUT/render" --mode video
ffmpeg -framerate 24 -i "$OUT/render/frames/frame_%04d.jpg" -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart -an "$OUT/render/Full-Product-Exploded-1080p.mp4"
```

The full-product scene includes front/rear shells, the nominal FT01C screen,
gasket/ledge, two side buttons, native USB-C and microSD connector positions,
current populated Core and Display PCBs, a removable edge retainer, fastener
envelopes and an explicitly unselected battery-pack envelope. FPC tails are
shown detached: contact orientation, bend radius, length and insertion tools
are NOT verified. Mainstream library component solids and simplified missing
bodies are visualization aids, not supplier-certified maximum envelopes.

The prototype is **112x75x22mm**, preserving the current stacked PCBs and large
RTC capacitor. It does not meet or replace the separate **7mm product target**.
The nominal envelope checks are not full solid-body collision or tolerance
analysis. Button force/travel, pack/harness, thermal/RF/audio, retention and
physical assembly remain unqualified. Do not mill a production enclosure based
on these images. STL files are exported only for manifold enclosure-study meshes;
they are candidates for a fit prototype, not a manufacturing release.

Only these reusable scripts and the explicit source contract belong in Git.
Keep PNG/MP4, GLB/Blender/STL, frames, generated logs and reports in the external
output directory. Never use a media branch as a file-transfer mechanism.
Fonts are runtime system references; font files must never be bundled or shared.
