"""Re-render the delivered Blender scene, without reading/writing native CAD.
Blender 5.2.1: blender -b Panda-Split-C1-be0ef37.blend --python render_saved_scene.py -- stills|video
For video, encode the generated frames with ffmpeg at 24fps. No fonts are bundled.
"""
import bpy,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['stills']
s=bpy.context.scene
assert s.frame_start==1 and s.frame_end==480
s.render.resolution_percentage=100
if args[0]=='stills':
 s.render.resolution_x=3840;s.render.resolution_y=2160;s.render.image_settings.file_format='PNG'
 for f,name,caption in [(181,'Exploded','EXPLODED / ASSEMBLY OFFSETS ARE ILLUSTRATIVE'),(365,'Underside','UNDERSIDE / DISPLAY COMPONENTS AND CORE BACK'),(1,'Assembled','ASSEMBLED / NATIVE BOARD-TO-BOARD TRANSFORM')]:
  s.frame_set(f);s.objects['Chapter'].data.body=caption;s.render.filepath=str(OUT/('Panda-Split-C1-'+name+'-4K.png'));bpy.ops.render.render(write_still=True)
elif args[0]=='video':
 s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.fps=24;s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=94
 frames=OUT/'frames';frames.mkdir(exist_ok=True)
 for f in range(1,481):
  s.frame_set(f);t=(f-1)/24
  s.objects['Chapter'].data.body='01 / ASSEMBLED BOARD PAIR' if t<2.5 else '02 / EXPLODE THE ASSEMBLY' if t<6 else '03 / NATIVE BOARD GEOMETRY' if t<9 else '04 / ORBIT TO THE UNDERSIDE' if t<14 else '05 / DISPLAY BOARD AND BOTTOM COMPONENTS' if t<16.5 else '06 / REASSEMBLE'
  s.render.filepath=str(frames/('frame_%04d.jpg'%f));bpy.ops.render.render(write_still=True)
else:raise SystemExit('Use stills or video')
