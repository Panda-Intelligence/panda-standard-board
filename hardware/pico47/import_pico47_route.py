#!/usr/bin/env python3
"""Import SES copper into a NEW E0 review directory without changing native intent.

This does not qualify the route or replace its source. DRC/ERC and independent
pad/function checks always run. A completed router job is never called fab-ready.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE.parent/'thin18-compact'))
from _split_c1_common import kicad_cli
from seven_mm_routing import native_semantic_fingerprint, copper_blocks, sexpr_blocks
from verify_pico47_native import inspect


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(args, path):
    with Path(path).open('w') as log:
        subprocess.run([kicad_cli(), *map(str,args)], cwd=Path(path).parent,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)


def import_route(source, session, board_name, donor, output):
    import wx
    app = wx.GetApp() or wx.App(False)
    import pcbnew as P
    source, session, output = map(lambda v: Path(v).resolve(), [source,session,output])
    if output.exists() or source == output:
        raise ValueError('Choose a fresh candidate output, never overwrite')
    if output.is_relative_to(REPO) and not output.is_relative_to(REPO/'.work'):
        raise ValueError('Generated route candidates remain ignored/external')
    if board_name not in ['Core','Display'] or not session.is_file():
        raise ValueError('Unknown board or absent router session')
    source_pcb = source/(board_name+'.kicad_pcb')
    before, session_hash = sha(source_pcb), sha(session)
    fingerprint = native_semantic_fingerprint(source_pcb)
    output.mkdir(parents=True)
    for item in source.iterdir():
        if item.is_file() and (item.suffix in {'.kicad_pcb','.kicad_sch','.kicad_pro',
                '.kicad_dru','.kicad_sym'} or item.name in ['fp-lib-table','sym-lib-table']):
            shutil.copy2(item,output/item.name)
    shutil.copytree(source/'Panda47.pretty',output/'Panda47.pretty')
    board = P.LoadBoard(str(source_pcb))
    if not P.ImportSpecctraSES(board,str(session)):
        raise ValueError('Native SES import failed')
    transient = output/(board_name+'-imported-copper-only.kicad_pcb')
    P.SaveBoard(str(transient),board)
    parts = copper_blocks(transient)
    original = source_pcb.read_text()
    for item in copper_blocks(source_pcb):
        original = original.replace(item,'',1)
    end = original.rfind(')')
    result_pcb = output/(board_name+'.kicad_pcb')
    result_pcb.write_text(original[:end]+'\n'+'\n'.join(parts)+'\n'+original[end:])
    if native_semantic_fingerprint(result_pcb) != fingerprint:
        raise ValueError('SES changed component/pad/net/outline intent')
    counts = {}
    for name in ['Core','Display']:
        for ext in ['.kicad_pro','.kicad_dru']:
            shutil.copy2(source/(name+ext),output/(name+ext))
        run(['pcb','drc','--refill-zones','--save-board','--severity-all','--all-track-errors',
             '--schematic-parity','--format','json','--output',output/(name+'-drc.json'),
             output/(name+'.kicad_pcb')],output/(name+'-drc.log'))
        run(['sch','erc','--severity-all','--format','json','--output',output/(name+'-erc.json'),
             output/(name+'.kicad_sch')],output/(name+'-erc.log'))
        drc = json.loads((output/(name+'-drc.json')).read_text())
        erc = json.loads((output/(name+'-erc.json')).read_text())
        counts[name] = {'drc':len(drc['violations']),'open':len(drc['unconnected_items']),
                        'parity':len(drc.get('schematic_parity',[])),
                        'erc':sum(len(s['violations']) for s in erc['sheets'])}
    verified = inspect(output,donor)
    if sha(source_pcb) != before or sha(session) != session_hash:
        raise ValueError('Input changed during routing import')
    if native_semantic_fingerprint(result_pcb) != fingerprint:
        raise ValueError('Native round trip changed component intent')
    report = {'source_pcb_sha256':before,'ses_sha256':session_hash,'board':board_name,
              'copper_items':len(parts),'checks':counts,'independent_native':verified,
              'manufacturing_release':False,'route_quality_qualified':False}
    (output/'ROUTING-REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'DO-NOT-ORDER-OR-POWER.txt').write_text(
        'Incomplete E0 engineering route candidate; route success is not design qualification. '
        'Exact battery and full panel assembly unverified; do not order or enable charging/panel power.\n')
    print(json.dumps({'board':board_name,'checks':counts,'copper_items':len(parts),
                     'output':str(output),'manufacturing_release':False},indent=2))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--session',type=Path,required=True)
    p.add_argument('--board',choices=['Core','Display'],required=True)
    p.add_argument('--donor',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    import_route(a.source,a.session,a.board,a.donor,a.output)
