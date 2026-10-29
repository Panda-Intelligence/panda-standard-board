"""验证 R25 路由终态的通道网名，不启动完整寻路器。"""
import ast
import json
import tempfile
import types
import unittest
from pathlib import Path


def finalize_function(namespace):
    # 仅加载生产 finalize，避免模块顶层初始化整板网格和外部依赖。
    path = Path(__file__).parent / 'r25_router' / 'router5.py'
    module = ast.parse(path.read_text(), filename=str(path))
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'finalize')
    code = compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec')
    exec(code, namespace)
    return namespace['finalize']


class FinalizeMuxAssignment(unittest.TestCase):
    def run_case(self, common_nets):
        commons = [('U710', '4'), ('U710', '7'), ('U710', '9'), ('U710', '12'),
                   ('U711', '4'), ('U711', '7'), ('U711', '9'), ('U711', '12')]
        gpios = [('U501', str(i)) for i in (10, 11, 12, 13, 14, 15, 49, 50)]
        # 两个 UART 通道固定，其余六对为可重新指派的 common/GPIO。
        uart_channels = (2, 3)
        swaps = [(commons[i], gpios[j]) for i, j in zip((0, 1, 4, 5, 6, 7), (0, 1, 2, 3, 4, 5))]
        original_nets = dict(zip(commons, common_nets))
        original_nets.update({gpios[6]: common_nets[2], gpios[7]: common_nets[3]})
        pads = [{'ref': key[0], 'num': key[1], 'net': original_nets[key]} for key in
                (commons[2], commons[3], gpios[6], gpios[7])]
        assignment = {'A': [], 'B': [], 'C': [], 'D': swaps}
        orig_net, sources = {}, {'A': [], 'B': [], 'C': [], 'D': []}
        tracks, vias, nets = [], [], {}
        for i, (source, sink) in enumerate(swaps):
            src = f'DS:{source[0]}.{source[1]}'
            dst = f'DK:{sink[0]}.{sink[1]}'
            orig_net[src] = original_nets[source]
            pads += [{'ref': source[0], 'num': source[1], 'net': src},
                     {'ref': sink[0], 'num': sink[1], 'net': dst}]
            sources['D'].append(src)
            tracks.append({'uuid': f'old-track-{i}', 'net': src})
            vias.append({'uuid': f'old-via-{i}', 'net': dst})
            nets[src] = {'tracks': [['F.Cu', i, 1, i + 0.1, 1]], 'vias': [[i, 2]]}
        state = {'assign': assignment, 'nets': nets, 'committed': sources['D'], 'pending': []}
        context = {'json': json, 'groups': assignment, 'orig_net': orig_net,
                   'g': {'pads': pads, 'tracks': tracks, 'vias': vias},
                   'c': types.SimpleNamespace(removed={}), 'regular': [], 'sources': sources,
                   'R': types.SimpleNamespace(W=0.15, VIA_D=0.4, VIA_DR=0.2),
                   'CH': [(ref, ('0', '0', pin)) for ref, pin in commons]}
        with tempfile.TemporaryDirectory() as tmp:
            state_file, output = Path(tmp) / 'state.json', Path(tmp) / 'final.json'
            state_file.write_text(json.dumps(state))
            finalize_function(context)(str(state_file), str(output))
            result = json.loads(output.read_text())
        actual = {(p['ref'], p['num']): p['net'] for p in result['pads']}
        for i in uart_channels:
            self.assertEqual(actual[commons[i]], common_nets[i])
            self.assertEqual(actual[gpios[i + 4]], common_nets[i])
        for source, sink in swaps:
            self.assertEqual(actual[source], original_nets[source])
            self.assertEqual(actual[sink], original_nets[source])
        self.assertEqual({actual[k] for k in commons}, {f'P47_MUX{i}' for i in range(8)})
        self.assertEqual({actual[k] for k in gpios}, {f'P47_MUX{i}' for i in range(8)})
        for i, (source, _) in enumerate(swaps):
            self.assertEqual(result['tracks'][i]['net'], original_nets[source])
            self.assertEqual(result['vias'][i]['net'], original_nets[source])
            self.assertEqual(result['tracks'][len(swaps) + i]['net'], original_nets[source])
            self.assertEqual(result['vias'][len(swaps) + i]['net'], original_nets[source])

    def test_original_common_net_order(self):
        self.run_case([f'P47_MUX{i}' for i in range(8)])

    def test_uart_channel_already_swapped(self):
        self.run_case(['P47_MUX0', 'P47_MUX1', 'P47_MUX5', 'P47_MUX3',
                       'P47_MUX4', 'P47_MUX2', 'P47_MUX6', 'P47_MUX7'])


if __name__ == '__main__':
    unittest.main()
