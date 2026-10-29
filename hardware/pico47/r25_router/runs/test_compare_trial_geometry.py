"""验证试验板几何比对可以识别实际焊盘和铜差异。"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from compare_trial_geometry import compare
except ModuleNotFoundError as exc:
    if exc.name != 'shapely':
        raise
    compare = None


@unittest.skipIf(compare is None, '该几何比较测试需要安装 shapely 的路由环境')
class CompareTrialGeometry(unittest.TestCase):
    def setUp(self):
        self.model = {
            'pads': [{'ref': 'C501', 'num': '1', 'uuid': 'pad1', 'net': '3V3_AON',
                      'x': 1., 'y': 2., 'layers': ['F.Cu'], 'drill': None,
                      'polys': {'F.Cu': [[[0., 0.], [1., 0.], [1., 1.], [0., 1.]]]}}],
            'tracks': [{'net': '3V3_AON', 'layer': 'F.Cu', 'w': .15,
                        'x1': 1., 'y1': 2., 'x2': 2., 'y2': 2.}],
            'vias': [{'net': '3V3_AON', 'x': 2., 'y': 2., 'd': .4, 'drill': .2}],
        }

    def test_matching_board_and_reversed_track(self):
        actual = copy.deepcopy(self.model)
        actual['tracks'][0].update(x1=2., x2=1.)
        self.assertEqual(compare(self.model, actual), [])

    def test_changed_pad_track_and_via_are_rejected(self):
        actual = copy.deepcopy(self.model)
        actual['pads'][0]['x'] += .01
        actual['tracks'][0]['net'] = 'GND'
        actual['vias'][0]['drill'] = .25
        self.assertEqual(len(compare(self.model, actual)), 3)

    def test_missing_pad_is_rejected(self):
        actual = copy.deepcopy(self.model)
        actual['pads'].clear()
        self.assertTrue(compare(self.model, actual))

    def test_duplicate_pad_numbers_use_identity(self):
        self.model['pads'][0].update(ref='J601', num='MP', uuid='mount1')
        second = copy.deepcopy(self.model['pads'][0])
        second['uuid'] = 'mount2'
        self.model['pads'].append(second)
        actual = copy.deepcopy(self.model)
        actual['pads'].reverse()
        self.assertEqual(compare(self.model, actual), [])
        actual['pads'][0]['net'] = 'GND'
        self.assertTrue(compare(self.model, actual))

    def test_copper_shape_mismatch_is_rejected(self):
        actual = copy.deepcopy(self.model)
        actual['pads'][0]['polys']['F.Cu'][0][1][0] += .02
        self.assertTrue(compare(self.model, actual))


if __name__ == '__main__':
    unittest.main()
