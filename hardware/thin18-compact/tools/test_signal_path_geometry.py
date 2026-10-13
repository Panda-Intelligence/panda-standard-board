import math
import unittest
from shapely.geometry import LineString, Point
from signal_path_geometry import SignalPathGraph


def shape(p):
    return [{'outer': [list(x) for x in p.exterior.coords], 'holes': []}]


def pad(ref, xy, layer='F.Cu', net='SIG'):
    return {'type': 'pad', 'ref': ref, 'pad': '1', 'position': xy, 'layer': layer,
            'uuid': ref, 'smd': True, 'net': net, 'polygons': shape(Point(xy).buffer(.2))}


def track(uid, a, b, layer='F.Cu', net='SIG'):
    return {'type': 'track', 'start': a, 'end': b, 'layer': layer, 'width': .15,
            'uuid': uid, 'net': net, 'polygons': shape(LineString([a, b]).buffer(.075))}


def via(uid, xy, layer):
    return {'type': 'via', 'position': xy, 'layer': layer, 'uuid': uid, 'net': 'SIG',
            'polygons': shape(Point(xy).buffer(.2))}


class Paths(unittest.TestCase):
    def check(self, rows):
        return SignalPathGraph({'items': rows}, 'SIG').path(('A', '1'), ('B', '1'))
    def test_straight(self):
        r = self.check([pad('A', [0, 0]), pad('B', [10, 0]), track('t', [0, 0], [10, 0])])
        self.assertEqual(r['planar_path_length_mm'], 10)
        self.assertEqual(r['vias_on_path'], 0)
        self.assertFalse(r['manufacturing_release'])
    def test_midpoint_branch_not_added_to_length(self):
        r = self.check([pad('A', [0, 0]), pad('B', [10, 0]), track('t', [0, 0], [10, 0]), track('branch', [5, 0], [5, 20])])
        self.assertEqual(r['planar_path_length_mm'], 10)
        self.assertEqual(r['gross_net_track_length_mm'], 30)
    def test_disconnected_gap_rejected(self):
        rows = [pad('A', [0, 0]), pad('B', [10, 0]), track('t1', [0, 0], [4, 0]), track('t2', [5, 0], [10, 0])]
        with self.assertRaises(ValueError): self.check(rows)
    def test_other_net_is_not_bridge(self):
        rows = [pad('A', [0, 0]), pad('B', [10, 0]), track('t1', [0, 0], [4, 0]), track('t2', [5, 0], [10, 0]), track('foreign', [4, 0], [5, 0], net='OTHER')]
        with self.assertRaises(ValueError): self.check(rows)
    def test_via_barrel_is_explicitly_excluded_from_length(self):
        rows = [pad('A', [0, 0]), pad('B', [10, 0], 'B.Cu'), track('t1', [0, 0], [5, 0]), track('t2', [5, 0], [10, 0], 'B.Cu'), via('v', [5, 0], 'F.Cu'), via('v', [5, 0], 'B.Cu')]
        r = self.check(rows)
        self.assertEqual(r['planar_path_length_mm'], 10)
        self.assertEqual(r['vias_on_path'], 1)
        self.assertEqual(r['signal_layers_used'], ['B.Cu', 'F.Cu'])
        self.assertFalse(r['via_barrel_length_and_delay_modelled'])
    def test_uncoupled_layers_are_not_connected(self):
        rows = [pad('A', [0, 0]), pad('B', [10, 0], 'B.Cu'), track('t1', [0, 0], [5, 0]), track('t2', [5, 0], [10, 0], 'B.Cu')]
        with self.assertRaises(ValueError): self.check(rows)
    def test_diagonal(self):
        r = self.check([pad('A', [0, 0]), pad('B', [10, 10]), track('t', [0, 0], [10, 10])])
        self.assertAlmostEqual(r['planar_path_length_mm'], math.sqrt(200), places=5)
    def test_reverse_track(self):
        r = self.check([pad('A', [0, 0]), pad('B', [10, 0]), track('t', [10, 0], [0, 0])])
        self.assertEqual(r['planar_path_length_mm'], 10)
    def test_arc_rejected(self):
        row = track('t', [0, 0], [10, 0]);row['is_arc'] = True
        with self.assertRaises(ValueError): self.check([pad('A', [0, 0]), pad('B', [10, 0]), row])
    def test_plane_rejected(self):
        row = via('z', [5, 0], 'F.Cu');row['type'] = 'zone'
        with self.assertRaises(ValueError): self.check([pad('A', [0, 0]), pad('B', [10, 0]), row])
    def test_wrong_terminal_rejected(self):
        with self.assertRaises(ValueError): self.check([pad('A', [0, 0]), track('t', [0, 0], [10, 0])])
    def test_zero_length_bridge_is_preserved_as_physical_copper(self):
        # Both terminals touch the end cap but not one another. Traversal does
        # not advance along the bridge centreline, yet deleting it disconnects.
        a=pad('A',[-.20,0]);b=pad('B',[.20,0])
        a['polygons']=shape(Point([-.20,0]).buffer(.14))
        b['polygons']=shape(Point([.20,0]).buffer(.14))
        r=self.check([a,b,track('bridge',[0,0],[0,1])])
        self.assertIn('bridge',r['physical_path_track_uuids'])
        self.assertNotIn('bridge',r['path_track_uuids'])
        self.assertEqual(set(r['physical_path_copper_uuids']),{'A','B','bridge'})
    def test_physical_path_does_not_include_disconnected_track(self):
        r=self.check([pad('A',[0,0]),pad('B',[2,0]),track('t',[0,0],[2,0]),track('stray',[10,0],[11,0])])
        self.assertNotIn('stray',r['physical_path_track_uuids'])
    def test_non_smd_terminal_needs_explicit_model(self):
        a = pad('A', [0, 0]);a['smd'] = False
        with self.assertRaises(ValueError): self.check([a, pad('B', [10, 0]), track('t', [0, 0], [10, 0])])

class SurfaceContacts(unittest.TestCase):
    def geometry(self):
        a=pad('A',[0,0]);a.update(smd=False,surface_only_no_drill=True,drill_mm=[0.,0.])
        return [a,pad('B',[10,0]),track('t',[0,0],[10,0])]
    def path(self,rows):return SignalPathGraph({'items':rows},'SIG').path(('A','1'),('B','1'))
    def test_undrilled_single_surface_contact(self):
        self.assertEqual(self.path(self.geometry())['planar_path_length_mm'],10)
    def test_surface_flag_does_not_hide_drill(self):
        rows=self.geometry();rows[0]['drill_mm']=[.2,.2]
        with self.assertRaises(ValueError):self.path(rows)
    def test_surface_flag_needs_drill_evidence(self):
        rows=self.geometry();del rows[0]['drill_mm']
        with self.assertRaises(ValueError):self.path(rows)
    def test_duplicate_on_other_layer_requires_barrel(self):
        rows=self.geometry();rows.append(dict(rows[0],layer='B.Cu'))
        with self.assertRaises(ValueError):self.path(rows)
    def test_other_net_contact_not_a_shortcut(self):
        rows=self.geometry();rows[0]['net']='OTHER'
        with self.assertRaises(ValueError):self.path(rows)

if __name__ == '__main__': unittest.main(verbosity=2)
