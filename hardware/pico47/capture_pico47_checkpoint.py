#!/usr/bin/env python3
"""Capture a fresh, non-regressing engineering checkpoint, never a fab release.

Sources and the previous external checkpoint are read-only. Both native boards
are rechecked after refill in a NEW ignored/external directory. Old pad groups,
component intent and rules must survive; a lower airwire count alone is not proof.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / 'thin18-compact'))
from seven_mm_routing import native_semantic_fingerprint, sexpr_blocks
from pico47_checkpoint import validate_manifest
from pico47_contract import CONTRACT
from pico47_placement import LAYOUT
from prune_pico47_stubs import drc, preserves_groups, pad_components
from _split_c1_common import kicad_python
from import_pico47_route import run
from verify_pico47_native import inspect
from pico47_complete_ground_gate import require_complete_ground_returns

BOARDS = ('Core', 'Display')
BINDINGS = {'.kicad_pcb': 'pcb_sha256', '.kicad_sch': 'schematic_sha256',
            '.kicad_pro': 'project_sha256', '.kicad_dru': 'rules_sha256'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def counts_from_reports(d, e):
    """Missing/malformed evidence is an error, never an implied zero."""
    for key in ('violations', 'unconnected_items', 'schematic_parity'):
        require(type(d.get(key)) is list, 'Missing native DRC evidence: ' + key)
    require(type(e.get('sheets')) is list and len(e['sheets']) > 0,
            'Missing native ERC sheets')
    for row in d['violations']:
        require(row.get('severity') in ('error', 'warning'), 'Unknown DRC severity')
    for sheet in e['sheets']:
        require(type(sheet.get('violations')) is list, 'Missing sheet ERC evidence')
    return {'drc_errors': sum(v['severity'] == 'error' for v in d['violations']),
            'drc_warnings': sum(v['severity'] == 'warning' for v in d['violations']),
            'open': len(d['unconnected_items']), 'parity': len(d['schematic_parity']),
            'erc': sum(len(s['violations']) for s in e['sheets'])}


def require_progress(before, after, groups_preserved):
    fields = {'drc_errors', 'drc_warnings', 'open', 'parity', 'erc'}
    for counts in (before, after):
        require(set(counts) == fields, 'Incomplete native counts')
        require(all(type(v) is int and v >= 0 for v in counts.values()),
                'Invalid native count')
        require(all(counts[k] == 0 for k in ('drc_errors', 'parity', 'erc')),
                'Native errors, parity or ERC prevent checkpoint acceptance')
    require(groups_preserved is True, 'Existing native pad connections were lost')
    require(after['open'] <= before['open'], 'More native unconnected items')
    require(after['drc_warnings'] <= before['drc_warnings'], 'More native DRC warnings')
    return True



def relabel_groups(groups, identities):
    """Compare physical pads across independent builds, not regenerated UUIDs."""
    require(type(groups) is list and len(groups) > 0
            and all(type(g) is list and len(g) > 0 for g in groups), 'Missing native pad groups')
    require(type(identities) is dict and all(type(v) is str and v for v in identities.values()),
            'Invalid native pad identities')
    inventory = set().union(*(set(g) for g in groups))
    require(len(inventory) == sum(len(g) for g in groups), 'Overlapping native pad groups')
    require(inventory == set(identities), 'Native pad identity inventory mismatch')
    require(len(set(identities.values())) == len(identities), 'Ambiguous physical pad identity')
    return [frozenset(identities[u] for u in group) for group in groups]


def export_pad_identities(pcb, output):
    import wx
    app = wx.App(False)
    import pcbnew as P
    pcb, output = Path(pcb).resolve(), Path(output).resolve()
    require(not output.exists() and output != pcb, 'Choose a fresh pad-identity output')
    board = P.LoadBoard(str(pcb))
    identities = {}
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if not pad.GetNumber():
                continue
            q = pad.GetPosition()
            layers = [board.GetLayerName(layer) for layer in
                      (P.F_Cu, P.In1_Cu, P.In2_Cu, P.B_Cu) if pad.IsOnLayer(layer)]
            identity = [footprint.GetReference(), pad.GetNumber(), int(q.x), int(q.y),
                        str(pad.GetNetname()), layers]
            identities[str(pad.m_Uuid.AsString())] = json.dumps(identity, separators=(',', ':'))
    groups = [sorted(group) for group in pad_components(board)]
    relabel_groups(groups, identities)
    output.write_text(json.dumps({'groups': groups, 'physical_pad_identity': identities}, indent=2) + '\n')


def stable_snapshot(pcb, output):
    output = Path(output)
    with output.with_suffix('.log').open('w') as log:
        subprocess.run([kicad_python(), str(Path(__file__).resolve()), '--pad-identities',
                        str(pcb), '--output', str(output)], check=True,
                       stdout=log, stderr=subprocess.STDOUT, timeout=90)
    data = json.loads(output.read_text())
    return relabel_groups(data['groups'], data['physical_pad_identity'])


def library_hashes(directory):
    files = [directory / name for name in ('Panda7.kicad_sym', 'fp-lib-table', 'sym-lib-table')]
    require((directory / 'Panda47.pretty').is_dir(), 'Missing local footprint library')
    files += sorted((directory / 'Panda47.pretty').glob('*.kicad_mod'))
    require(len(files) > 3, 'Empty local footprint library')
    return {str(p.relative_to(directory)): sha(p) for p in files}



def library_definition(text):
    """Ignore ONLY regenerated library IDs and non-electrical editor metadata.

    Board-instance pad UUIDs are never normalized: native continuity uses them.
    Published library bytes still come unchanged from the reviewed baseline.
    """
    text = re.sub(r'\(uuid "[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"\)',
                  '(uuid "library-instance")', text)
    text = re.sub(r'(?m)^\t\(locked yes\)\n', '', text)
    for block in sexpr_blocks(text, '(property'):
        if '(layer "F.Fab")' in block and '(hide yes)' in block:
            revised = re.sub(r'(?m)^\t{4}\(thickness 0\.15\)\n', '', block)
            text = text.replace(block, revised, 1)
    return text


def review_libraries(source, baseline):
    old, new = library_hashes(baseline), library_hashes(source)
    require(set(old) == set(new), 'Library inventory changed')
    metadata_only = []
    for relative in old:
        if old[relative] == new[relative]:
            continue
        require(relative.endswith('.kicad_mod'), 'Symbol or library-table bytes changed')
        require(library_definition((baseline / relative).read_text())
                == library_definition((source / relative).read_text()),
                'Footprint definition changed: ' + relative)
        metadata_only.append(relative)
    return {'reviewed_baseline_bytes_preserved_in_output': True,
            'metadata_only_source_differences': metadata_only,
            'baseline_sha256': old, 'source_sha256': new}


def capture(baseline, core, display, donor, output, *, require_complete_ground=False):
    require(type(require_complete_ground) is bool, 'Ground-closure requirement must be boolean')
    baseline, core, display, donor, output = [Path(p).resolve() for p in
                                             (baseline, core, display, donor, output)]
    require(not output.exists(), 'Choose a fresh output; never overwrite a checkpoint')
    require(not output.is_relative_to(REPO) or output.is_relative_to(REPO / '.work'),
            'Generated native checkpoints must stay ignored or external')
    require(all(output != p and not output.is_relative_to(p)
                for p in (baseline, core, display, donor)), 'Output overlaps an input')
    data = json.loads((baseline / 'ROUTING-CHECKPOINT.json').read_text())
    validate_manifest(data)
    require(data['source_design_sha256'] == sha(CONTRACT)
            and data['source_layout_sha256'] == sha(LAYOUT), 'Source contract changed')
    sources = {'Core': core, 'Display': display}
    source_hashes = {baseline / 'ROUTING-CHECKPOINT.json': sha(baseline / 'ROUTING-CHECKPOINT.json'),
                     CONTRACT: sha(CONTRACT), LAYOUT: sha(LAYOUT)}
    libraries = library_hashes(baseline)
    library_reviews = {}
    for name in BOARDS:
        source = sources[name]
        library_reviews[name] = review_libraries(source, baseline)
        for relative, digest in libraries.items():
            source_hashes[source / relative] = sha(source / relative)
            source_hashes[baseline / relative] = digest
        for suffix, key in BINDINGS.items():
            previous, current = baseline / (name + suffix), source / (name + suffix)
            require(sha(previous) == data['boards'][name][key], name + ': stale baseline')
            source_hashes[previous], source_hashes[current] = sha(previous), sha(current)
            if suffix != '.kicad_pcb':
                require(sha(current) == sha(previous), name + ': native intent or rules changed')
        require(native_semantic_fingerprint(source / (name + '.kicad_pcb'))
                == data['boards'][name]['geometry_sha256'], name + ': placement/pads/outline changed')
    output.mkdir(parents=True)
    try:
        for relative in libraries:
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(baseline / relative, target)
        manifest = {'schema': data['schema'], 'source_design_sha256': sha(CONTRACT),
                    'source_layout_sha256': sha(LAYOUT), 'boards': {}, 'manufacturing_release': False}
        continuity = {}
        for name in BOARDS:
            for suffix in BINDINGS:
                shutil.copy2(sources[name] / (name + suffix), output / (name + suffix))
            old_groups = stable_snapshot(baseline / (name + '.kicad_pcb'),
                                  output / (name + '-previous-pad-groups.json'))
            pcb = output / (name + '.kicad_pcb')
            d = drc(pcb, output / (name + '-drc.json'))
            run(['sch', 'erc', '--severity-all', '--format', 'json', '--output',
                 output / (name + '-erc.json'), output / (name + '.kicad_sch')],
                output / (name + '-erc.log'))
            counts = counts_from_reports(d, json.loads((output / (name + '-erc.json')).read_text()))
            groups = stable_snapshot(pcb, output / (name + '-current-pad-groups.json'))
            kept = preserves_groups(old_groups, groups)
            require_progress(data['boards'][name]['counts'], counts, kept)
            require(native_semantic_fingerprint(pcb) == data['boards'][name]['geometry_sha256'],
                    name + ': native round trip changed geometry')
            continuity[name] = {'comparison': 'reference/pad/position/net/copper-layers',
                                'previous_groups': len(old_groups), 'current_groups': len(groups),
                                'all_original_pad_groups_preserved': kept}
            manifest['boards'][name] = {'counts': counts,
                'geometry_sha256': native_semantic_fingerprint(pcb),
                **{key: sha(output / (name + suffix)) for suffix, key in BINDINGS.items()}}
        independent = inspect(output, donor)
        ground_gate = (require_complete_ground_returns(independent['ground_return_connectivity'])
                       if require_complete_ground else {'required': False})
        require(all(sha(p) == digest for p, digest in source_hashes.items()),
                'An input changed during capture')
        validate_manifest(manifest)
        for name in BOARDS:
            require(independent['native_sha256'][name] == sha(output / (name + '.kicad_pcb')),
                    'Independent evidence is stale')
        def write(name, obj):
            (output / name).write_text(json.dumps(obj, indent=2) + '\n')
        write('INDEPENDENT-CHECK.json', independent)
        write('CONTINUITY-CHECK.json', continuity)
        write('LIBRARY-CHECK.json', library_reviews)
        if require_complete_ground:
            write('COMPLETE-GROUND-CHECK.json', ground_gate)
        write('CURRENT-STATUS.json', {'baseline_checkpoint': str(baseline),
              'sources': {n: str(p) for n, p in sources.items()},
              'native_counts': {n: r['counts'] for n, r in manifest['boards'].items()},
              'critical_physical_connections': independent['critical_physical_connections'],
              'complete_ground_gate': ground_gate,
              'manufacturing_release': False, 'physical_qualification_complete': False})
        (output / 'START-HERE.md').write_text(
            '# Panda47 engineering continuation\n\nNOT FOR FABRICATION OR POWER.\n\n'
            'Read CURRENT-STATUS.json for actual remaining native opens/warnings and the '
            'inhibit-chain result. Native DRC success does not qualify power loops, timing, '
            'the exact battery/panel assembly, 7mm mechanical fit, or factory processes.\n')
        write('ROUTING-CHECKPOINT.json', manifest)
        write('MANIFEST.json', {'files': {str(p.relative_to(output)): sha(p)
              for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json'},
              'manufacturing_release': False})
        print(json.dumps({'output': str(output), 'boards': {n: r['counts'] for n, r in
                         manifest['boards'].items()}, 'continuity': continuity,
                         'manufacturing_release': False}, indent=2))
        return manifest
    except Exception:
        # No rejected directory may be used as an accepted replay checkpoint.
        (output / 'ROUTING-CHECKPOINT.json').unlink(missing_ok=True)
        (output / 'CHECKPOINT-CAPTURE-FAILED.txt').write_text(
            'Capture failed. This directory is rejected evidence, not an accepted checkpoint.\n')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pad-identities', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--require-complete-ground', action='store_true',
                        help='Require all native ground pads and all eight named ground targets to join reference; not a fabrication release')
    for name in ('baseline', 'core', 'display', 'donor', 'output'):
        parser.add_argument('--' + name, type=Path, required=(name == 'output'))
    args = parser.parse_args()
    if args.pad_identities:
        if args.require_complete_ground:
            parser.error('--require-complete-ground requires a full native capture')
        export_pad_identities(args.pad_identities, args.output)
    else:
        if not all((args.baseline, args.core, args.display, args.donor)):
            parser.error('--baseline, --core, --display and --donor are required')
        capture(args.baseline, args.core, args.display, args.donor, args.output,
                require_complete_ground=args.require_complete_ground)
