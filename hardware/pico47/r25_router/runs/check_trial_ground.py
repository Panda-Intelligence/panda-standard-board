"""重填两块试验板并执行现有完整地返回检查。"""
import json
import sys
from pathlib import Path
import pcbnew as p

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pico47_ground_returns import inspect_ground_returns
from pico47_complete_ground_gate import require_complete_ground_returns


def main(trial_dir, output):
    reports = {}
    for name, reference, targets, count in (
        ('Core', ('U501', '57'), [('J601', '36'), ('J601', '38')], 169),
        ('Display', ('C804', '2'), [('J820', '9'), ('J820', '22'), ('R809', '2'), ('R810', '2'), ('U810', '32'), ('U810', '41')], 68),
    ):
        board = p.LoadBoard(str(Path(trial_dir) / (name + '.kicad_pcb')))
        p.ZONE_FILLER(board).Fill(board.Zones())
        reports[name] = inspect_ground_returns(board, *reference, targets)
        if reports[name]['ground_pad_count'] != count:
            raise ValueError(name + ' 地焊盘数量与基线不一致')
    try:
        result = require_complete_ground_returns(reports)
    except ValueError as exc:
        result = {'complete': False, 'error': str(exc)}
    with open(output, 'w') as handle:
        json.dump({'result': result, 'reports': reports}, handle, indent=2)
    for name, report in reports.items():
        print(name, report['reference_group_pad_count'], '/', report['ground_pad_count'])
    return bool(result.get('complete'))


if __name__ == '__main__':
    sys.exit(0 if main(*sys.argv[1:]) else 1)
