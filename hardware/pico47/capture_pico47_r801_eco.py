#!/usr/bin/env python3
"""Capture ONLY the exact reviewed R801 source/assembly-side ECO.

Ordinary checkpoint rules remain unchanged. This dedicated migration verifies
old source hashes, the single allowed layout delta, an independently transformed
old board, a fresh source build, native DRC/ERC, complete ground and every old
pad group. It never grants assembly, fabrication or hardware-power permission.
"""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'thin18-compact'))
from capture_pico47_checkpoint import (
    BOARDS, BINDINGS, sha, require, review_libraries, library_hashes,
    counts_from_reports, require_progress, stable_snapshot,
)
from seven_mm_routing import native_semantic_fingerprint
from pico47_checkpoint import validate_manifest
from pico47_contract import CONTRACT
from pico47_placement import LAYOUT, validate_layout
from pico47_r801_placement_eco import (
    PREVIOUS_LAYOUT_SHA256, validate_r801_eco, apply_r801_eco, normalize_r801_groups,
)
from prune_pico47_stubs import drc, preserves_groups
from import_pico47_route import run
from _split_c1_common import kicad_python
from verify_pico47_native import inspect
from pico47_complete_ground_gate import require_complete_ground_returns


def expected_display(old_pcb, output):
    """Child-process transform: the old board changes only by apply_r801_eco."""
    import wx
    app = wx.App(False)
    import pcbnew as P
    old_pcb, output = Path(old_pcb).resolve(), Path(output).resolve()
    require(not output.exists() and output != old_pcb, 'Expected geometry must be fresh')
    before = sha(old_pcb)
    spec = json.loads(LAYOUT.read_text())['display_r801_placement_eco']
    board = P.LoadBoard(str(old_pcb))
    footprint = board.FindFootprintByReference('R801')
    require(footprint is not None, 'Missing old R801')
    identities = {
        f.GetReference(): (int(f.GetPosition().x), int(f.GetPosition().y),
                           f.GetOrientationDegrees(), int(f.GetLayer()))
        for f in board.GetFootprints()
    }
    apply_r801_eco(board, spec)
    require(all(identities[f.GetReference()] ==
                (int(f.GetPosition().x), int(f.GetPosition().y),
                 f.GetOrientationDegrees(), int(f.GetLayer()))
                for f in board.GetFootprints() if f.GetReference() != 'R801'),
            'The isolated ECO moved another component')
    P.SaveBoard(str(output), board)
    require(sha(old_pcb) == before, 'Expected-geometry generation changed its input')


def capture_r801_eco(baseline, core, display, donor, previous_layout, source_build, output):
    baseline, core, display, donor, previous_layout, source_build, output = [
        Path(p).resolve() for p in
        (baseline, core, display, donor, previous_layout, source_build, output)]
    require(not output.exists(), 'Use a fresh ECO capture directory')
    require(all(output != p and not output.is_relative_to(p)
                and not p.is_relative_to(output)
                for p in (baseline, core, display, donor, source_build)),
            'ECO output overlaps a native input')
    repo = HERE.parent.parent
    require(not output.is_relative_to(repo) or output.is_relative_to(repo / '.work'),
            'Generated ECO evidence must remain ignored or external')
    old = json.loads((baseline / 'ROUTING-CHECKPOINT.json').read_text())
    validate_manifest(old)
    current_layout = json.loads(LAYOUT.read_text())
    validate_layout(current_layout)
    spec = current_layout.get('display_r801_placement_eco')
    validate_r801_eco(spec)
    require(sha(previous_layout) == PREVIOUS_LAYOUT_SHA256 == old['source_layout_sha256'],
            'Wrong previous source-layout binding')
    require({key: value for key, value in current_layout.items()
             if key != 'display_r801_placement_eco'} == json.loads(previous_layout.read_text()),
            'Source layout changed beyond the exact R801 ECO')
    require(old['source_design_sha256'] == sha(CONTRACT), 'Electrical source contract changed')
    sources = {'Core': core, 'Display': display}
    inputs = {CONTRACT: sha(CONTRACT), LAYOUT: sha(LAYOUT), previous_layout: sha(previous_layout),
              baseline / 'ROUTING-CHECKPOINT.json': sha(baseline / 'ROUTING-CHECKPOINT.json')}
    libraries = library_hashes(baseline)
    library_reviews = {}
    for name in BOARDS:
        library_reviews[name] = review_libraries(sources[name], baseline)
        review_libraries(source_build, baseline)
        for suffix, key in BINDINGS.items():
            original = baseline / (name + suffix)
            require(sha(original) == old['boards'][name][key], 'Stale old ' + name + suffix)
            for folder in (baseline, sources[name], source_build):
                path = folder / (name + suffix)
                inputs[path] = sha(path)
                if suffix != '.kicad_pcb':
                    require(sha(path) == sha(original), 'Native electrical intent or rules changed')
        for folder in (baseline, sources[name], source_build):
            for rel in libraries:
                inputs[folder / rel] = sha(folder / rel)
        require(native_semantic_fingerprint(sources[name] / (name + '.kicad_pcb')) ==
                native_semantic_fingerprint(source_build / (name + '.kicad_pcb')),
                name + ': routed candidate differs from the fresh source build')
    require(native_semantic_fingerprint(core / 'Core.kicad_pcb') == old['boards']['Core']['geometry_sha256'],
            'Core geometry changed during Display-only ECO')
    output.mkdir(parents=True)
    try:
        expected = output / 'R801-EXPECTED-GEOMETRY.kicad_pcb'
        with (output / 'R801-expected-geometry.log').open('w') as log:
            subprocess.run([kicad_python(), str(Path(__file__).resolve()),
                            '--expected-display', str(baseline / 'Display.kicad_pcb'),
                            '--output', str(expected)], check=True, stdout=log,
                           stderr=subprocess.STDOUT, timeout=90)
        geometry = native_semantic_fingerprint(expected)
        require(geometry == native_semantic_fingerprint(display / 'Display.kicad_pcb'),
                'Display change is not exactly the reviewed R801 placement')
        for rel in libraries:
            target = output / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(baseline / rel, target)
        manifest = {'schema': old['schema'], 'source_design_sha256': sha(CONTRACT),
                    'source_layout_sha256': sha(LAYOUT), 'boards': {}, 'manufacturing_release': False}
        continuity = {}
        for name in BOARDS:
            for suffix in BINDINGS:
                shutil.copy2(sources[name] / (name + suffix), output / (name + suffix))
            old_groups = stable_snapshot(baseline / (name + '.kicad_pcb'),
                                         output / (name + '-old-pad-identities.json'))
            pcb = output / (name + '.kicad_pcb')
            d = drc(pcb, output / (name + '-drc.json'))
            run(['sch', 'erc', '--severity-all', '--format', 'json', '--output',
                 output / (name + '-erc.json'), output / (name + '.kicad_sch')],
                output / (name + '-erc.log'))
            counts = counts_from_reports(d, json.loads((output / (name + '-erc.json')).read_text()))
            new_groups = stable_snapshot(pcb, output / (name + '-new-pad-identities.json'))
            if name == 'Display':
                old_groups = normalize_r801_groups(old_groups, 'before', spec)
                new_groups = normalize_r801_groups(new_groups, 'after', spec)
            kept = preserves_groups(old_groups, new_groups)
            require_progress(old['boards'][name]['counts'], counts, kept)
            require(native_semantic_fingerprint(pcb) ==
                    native_semantic_fingerprint(source_build / (name + '.kicad_pcb')),
                    name + ': round trip changed the source-ECO geometry')
            continuity[name] = {'all_original_pad_groups_preserved': kept,
                                 'previous_groups': len(old_groups), 'current_groups': len(new_groups),
                                 'exception': 'exact R801 two-pad migration only' if name == 'Display' else None}
            manifest['boards'][name] = {'counts': counts,
                'geometry_sha256': native_semantic_fingerprint(pcb),
                **{key: sha(output / (name + suffix)) for suffix, key in BINDINGS.items()}}
        independent = inspect(output, donor)
        ground = require_complete_ground_returns(independent['ground_return_connectivity'])
        require(all(independent['critical_physical_connections'].values()), 'Critical inhibit/ground path lost')
        require(all(v['connected'] for v in independent['core_panel_control_connections'].values()),
                'Panel control path lost')
        require(all(sha(path) == digest for path, digest in inputs.items()), 'An ECO input changed')
        validate_manifest(manifest)
        def write(name, data):
            (output / name).write_text(json.dumps(data, indent=2) + '\n')
        write('INDEPENDENT-CHECK.json', independent)
        write('COMPLETE-GROUND-CHECK.json', ground)
        write('CONTINUITY-CHECK.json', continuity)
        write('LIBRARY-CHECK.json', library_reviews)
        write('R801-SOURCE-ECO.json', {'spec': spec, 'old_source_layout_sha256': sha(previous_layout),
              'new_source_layout_sha256': sha(LAYOUT), 'expected_display_geometry_sha256': geometry,
              'fresh_build': str(source_build), 'all_other_native_geometry_unchanged': True,
              'native_checks_passed': True, 'assembly_height_and_process_qualified': False,
              'source_replay_still_required': True, 'manufacturing_release': False})
        write('CURRENT-STATUS.json', {'baseline_checkpoint': str(baseline),
              'sources': {n: str(p) for n, p in sources.items()},
              'native_counts': {n: r['counts'] for n, r in manifest['boards'].items()},
              'critical_physical_connections': independent['critical_physical_connections'],
              'complete_ground_gate': ground, 'source_ECO': 'R801 backside placement',
              'manufacturing_release': False, 'physical_qualification_complete': False})
        (output / 'START-HERE.md').write_text(
            '# Panda47 exact R801 ECO engineering checkpoint\n\n'
            'NOT FOR FABRICATION OR POWER. Routing and physical qualification remain incomplete.\n'
            'R801 requires two-sided assembly and a separate height/CPL/process review.\n')
        write('ROUTING-CHECKPOINT.json', manifest)
        write('MANIFEST.json', {'files': {str(p.relative_to(output)): sha(p)
              for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json'},
              'manufacturing_release': False})
        print(json.dumps({'output': str(output), 'counts': {n: r['counts'] for n, r in manifest['boards'].items()},
                          'old_groups_preserved': continuity, 'manufacturing_release': False}, indent=2))
        return manifest
    except Exception:
        (output / 'ROUTING-CHECKPOINT.json').unlink(missing_ok=True)
        (output / 'ECO-CAPTURE-FAILED.txt').write_text('Rejected ECO evidence. No accepted checkpoint.\n')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-display', type=Path)
    for name in ('baseline', 'core', 'display', 'donor', 'previous-layout', 'source-build', 'output'):
        parser.add_argument('--' + name, type=Path, required=(name == 'output'))
    args = parser.parse_args()
    if args.expected_display:
        expected_display(args.expected_display, args.output)
    else:
        if not all((args.baseline, args.core, args.display, args.donor, args.previous_layout, args.source_build)):
            parser.error('Full ECO source, baseline, previous layout and fresh build are required')
        capture_r801_eco(args.baseline, args.core, args.display, args.donor,
                        args.previous_layout, args.source_build, args.output)
