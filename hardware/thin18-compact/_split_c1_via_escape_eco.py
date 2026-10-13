"""Replay the reviewed limited via escape; no auto-routing during rebuild."""
from pathlib import Path
import json,re,subprocess
from _split_c1_common import ROOT, REL, STEM, kicad_python
from _core_c1_pcb_patch import copper,digest
from _split_c1_sourcing import blocks

PLAN=ROOT/'split-c1-via-escape-layout.json'

def transform(text, plan):
    if digest(text)!=plan['source_copper_sha256']:
        raise ValueError('Via-escape copper predecessor differs; do not overwrite')
    current=copper(text)
    for uid,before in plan['removed'].items():
        if current.get(uid)!=before:raise ValueError('Removed copper predecessor differs')
    for uid,change in plan['modified'].items():
        if current.get(uid)!=change['before']:raise ValueError('Moved via predecessor differs')
        if not change['before'].startswith('(via') or not change['after'].startswith('(via'):
            raise ValueError('Only reviewed via positions may change in place')
        # A relocation never shrinks the annulus or drill, or changes its net/layers.
        strip=lambda s:re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+\)','',s,count=1)
        if strip(change['before'])!=strip(change['after']):raise ValueError('Unreviewed via geometry change')
    if set(current)&set(plan['added']):raise ValueError('Added copper UUID collision')
    for a,b,item in reversed(list(blocks(text,r'\((?:segment|via)\s'))):
        uid=re.search(r'\(uuid\s+"([^"]+)"',item)[1]
        if uid in plan['removed']:text=text[:a]+text[b:]
        elif uid in plan['modified']:text=text[:a]+plan['modified'][uid]['after']+text[b:]
    end=text.rfind(')');text=text[:end]+'\n'+'\n'.join(plan['added'].values())+'\n'+text[end:]
    if digest(text)!=plan['routed_copper_sha256']:raise ValueError('Via-escape replay differs')
    return text


def apply_native(candidate):
    import wx
    app=wx.App(False)
    from _split_c1_power_integrity_eco import refill_zones
    pcb=Path(candidate)/REL/(STEM+'.kicad_pcb')
    original=pcb.read_text();plan=json.loads(PLAN.read_text())
    new=transform(original,plan)
    before=[f for _,_,f in blocks(original,r'\(footprint\s')]
    after=[f for _,_,f in blocks(new,r'\(footprint\s')]
    if before!=after:raise ValueError('Via escape moved a component or modified its pads')
    pcb.write_text(new);refill_zones(pcb)
    if digest(pcb.read_text())!=plan['routed_copper_sha256']:raise ValueError('Refill modified routing')


def apply_via_escape_eco(candidate):
    subprocess.run([kicad_python(),str(Path(__file__).resolve()),str(Path(candidate).resolve())],check=True)


if __name__=='__main__':
    import sys
    apply_native(Path(sys.argv[1]))
