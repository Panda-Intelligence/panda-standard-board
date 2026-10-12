#!/usr/bin/env python3
"""Prune native-reported E0 dead-end copper only, preserving every connected pad group.

A lower airwire count alone is NOT proof of preserved connections. This tool uses
KiCad's complete connectivity clusters for each source pad, including filled-zone
subpolygons. All originally connected pad pairs must remain connected after each
trial, otherwise that trial is restored. No pin/net/part or rule edits are made.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0,str(HERE.parent/'thin18-compact'))
from _split_c1_common import kicad_cli, kicad_python
from seven_mm_routing import native_semantic_fingerprint, sexpr_blocks
from verify_pico47_native import inspect


def pad_components(board):
    import pcbnew as P
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    pads = {str(p.m_Uuid.AsString()):p for f in board.GetFootprints() for p in f.Pads()
            if p.GetNumber()}
    groups, done = [], set()
    for uid,pad in sorted(pads.items()):
        if uid in done:
            continue
        linked = {str(x.m_Uuid.AsString()) for x in conn.GetConnectedItems(pad)
                  if str(x.m_Uuid.AsString()) in pads}
        linked.add(uid)
        groups.append(frozenset(linked))
        done.update(linked)
    if done != set(pads):
        raise ValueError('Incomplete native pad connectivity inventory')
    return groups


def preserves_groups(old,new):
    before = set().union(*old) if old else set()
    after = set().union(*new) if new else set()
    if before != after:
        return False
    lookup = {p:g for g in new for p in g}
    return all(g <= lookup[next(iter(g))] for g in old if g)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def drc(pcb,report):
    with report.with_suffix('.log').open('w') as log:
        subprocess.run([kicad_cli(),'pcb','drc','--refill-zones','--save-board',
            '--severity-all','--all-track-errors','--schematic-parity','--format','json',
            '--output',str(report),str(pcb)],cwd=pcb.parent,stdout=log,
            stderr=subprocess.STDOUT,check=True,timeout=90)
    return json.loads(report.read_text())


def snapshot(pcb,output):
    # Use an isolated KiCad Python process for connectivity traversal. Some
    # SWIG builds invalidate dynamic wrappers after repeated board destruction.
    with output.with_suffix('.log').open('w') as log:
        subprocess.run([kicad_python(),str(Path(__file__).resolve()),'--snapshot',
                        str(pcb),'--output',str(output)],stdout=log,
                       stderr=subprocess.STDOUT,check=True,timeout=90)
    return [frozenset(g) for g in json.loads(output.read_text())]


def prune(source,output,donor,board_name='Core',max_passes=12):
    source,output = Path(source).resolve(),Path(output).resolve()
    if output.exists() or (output.is_relative_to(REPO) and not output.is_relative_to(REPO/'.work')):
        raise ValueError('Choose a fresh ignored/external output')
    if board_name not in ['Core','Display'] or not (1 <= max_passes <= 30):
        raise ValueError('Invalid board or pass count')
    src = source/(board_name+'.kicad_pcb')
    source_hash = sha(src)
    output.mkdir(parents=True)
    for item in source.iterdir():
        if item.is_file() and (item.suffix in {'.kicad_pcb','.kicad_sch','.kicad_pro',
            '.kicad_dru','.kicad_sym'} or item.name in ['fp-lib-table','sym-lib-table']):
            shutil.copy2(item,output/item.name)
    shutil.copytree(source/'Panda47.pretty',output/'Panda47.pretty')
    pcb = output/(board_name+'.kicad_pcb')
    report = output/(board_name+'-drc.json')
    original_fp = native_semantic_fingerprint(pcb)
    initial_report = drc(pcb,report)
    baseline = snapshot(pcb,output/'pad-groups-before.json')
    records = []
    stopped_reason = None
    current = initial_report
    for index in range(max_passes):
        ids = {i['uuid'] for v in current['violations']
               if v['type'] in {'track_dangling','via_dangling'} for i in v['items']}
        if not ids:
            break
        backup = pcb.read_bytes()
        text = backup.decode('utf-8')
        selected = []
        for item in sexpr_blocks(text,'(segment') + sexpr_blocks(text,'(via'):
            uid = re.search(r'\(uuid "([^"]+)"\)',item)
            if uid and uid[1] in ids:
                name = re.search(r'\(net "([^"]+)"\)',item)
                if not name:
                    raise ValueError('Copper net name missing')
                selected.append((uid[1],name[1],item))
        if {row[0] for row in selected} != ids:
            raise ValueError('DRC dead ends did not resolve exclusively to copper')
        removed = [{'uuid':u,'net':n} for u,n,_ in selected]
        for _,_,item in selected:
            text = text.replace(item,'',1)
        pcb.write_text(text)
        try:
            trial = drc(pcb,report)
            next_groups = snapshot(pcb,output/('pad-groups-trial-%02d.json'%index))
            keep = preserves_groups(baseline,next_groups)
            keep = keep and native_semantic_fingerprint(pcb) == original_fp
            keep = keep and not trial.get('schematic_parity')
        except Exception:
            pcb.write_bytes(backup)
            drc(pcb,report)
            raise
        previous_errors = sum(v['severity']=='error' for v in current['violations'])
        new_errors = sum(v['severity']=='error' for v in trial['violations'])
        keep = keep and new_errors <= previous_errors
        if not keep:
            pcb.write_bytes(backup)
            current = drc(pcb,report)
            stopped_reason = 'Trial restored: pad-group continuity or native error guard rejected it'
            print(stopped_reason,flush=True)
            break
        records.append({'pass':index+1,'removed_copper':removed,
                        'drc':len(trial['violations']),'open':len(trial['unconnected_items'])})
        current = trial
        print('PRUNE',index+1,'removed',len(removed),'DRC',len(current['violations']),
              'OPEN',len(current['unconnected_items']),flush=True)
    other = 'Display' if board_name=='Core' else 'Core'
    other_report = drc(output/(other+'.kicad_pcb'),output/(other+'-drc.json'))
    verified = inspect(output,donor)
    if sha(src) != source_hash:
        raise ValueError('Source changed during prune')
    result = {'board':board_name,'source_sha256':source_hash,
              'original_pad_groups':len(baseline),'all_original_pad_groups_preserved':True,
              'removed_copper_count':sum(len(r['removed_copper']) for r in records),
              'passes':records,'stopped_reason':stopped_reason,
              'before':{'drc':len(initial_report['violations']),'open':len(initial_report['unconnected_items'])},
              'after':{'drc':len(current['violations']),'open':len(current['unconnected_items'])},
              'independent_native':verified,'manufacturing_release':False,
              'airwire_reduction_is_not_newly_routed_connections':True}
    (output/'PRUNING-REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    (output/'DO-NOT-ORDER-OR-POWER.txt').write_text('Incomplete E0 redesign. Dead-end cleanup is not completed routing or physical qualification. Do not order or power.\n')
    print(json.dumps({k:result[k] for k in ['before','after','removed_copper_count',
          'original_pad_groups','all_original_pad_groups_preserved','stopped_reason']},indent=2))
    return result


if __name__=='__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path)
    ap.add_argument('--snapshot',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--donor',type=Path)
    ap.add_argument('--board',choices=['Core','Display'],default='Core')
    ap.add_argument('--max-passes',type=int,default=12)
    a = ap.parse_args()
    if a.snapshot:
        import wx
        app=wx.App(False)
        import pcbnew as P
        board=P.LoadBoard(str(a.snapshot.resolve()))
        groups=pad_components(board)
        a.output.write_text(json.dumps([sorted(g) for g in groups])+'\n')
    else:
        if not a.source or not a.donor:
            ap.error('--source and --donor required')
        prune(a.source,a.output,a.donor,a.board,a.max_passes)
