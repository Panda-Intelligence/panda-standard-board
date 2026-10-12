"""Ordered-layout regressions; synthetic changes are never hardware acceptance."""
import copy
import unittest
from pico47_placement import load_layout, validate_layout


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.data=load_layout()

    def test_source(self):
        self.assertTrue(validate_layout(self.data))

    def test_sixteen_data_positions_are_pin_ordered(self):
        poses=self.data['core_poses']
        for bit in range(16):
            self.assertEqual(poses['R'+str(710+bit)],[46.45,86.45+bit,180.0])

    def test_mcu_ep_drill_and_annulus(self):
        via=self.data['mcu_ep_vias']
        self.assertEqual((via['diameter_mm']-via['drill_mm'])/2,.125)
        self.assertEqual(len(via['offsets_mm']),9)


def mutation(path,value):
    def run(self):
        data=copy.deepcopy(self.data)
        target=data
        for key in path[:-1]:
            target=target[key]
        target[path[-1]]=value
        with self.assertRaises(ValueError):
            validate_layout(data)
    return run


CASES=[
    (['schema'],'panda-old-layout'),
    (['manufacturing_release'],True),
    (['native_routing_complete'],True),
    (['core_poses','R710'],[46.45,87.45,180.0]),
    (['core_poses','R725'],[46.45,101.45,0.0]),
    (['core_poses','R718'],[float('nan'),94.45,180.0]),
    (['core_poses','R718'],[True,94.45,180.0]),
    (['core_poses','U711'],[63.5,127.75,0]),
    (['core_poses','C711'],[50,113.25,0]),
    (['core_solid_ground_pads','U501'],['36']),
    (['core_solid_ground_pads','U810'],['49']),
    (['mcu_ep_vias','ref'],'U810'),
    (['mcu_ep_vias','pad'],'49'),
    (['mcu_ep_vias','net'],'P47_VN'),
    (['mcu_ep_vias','drill_mm'],.1),
    (['mcu_ep_vias','diameter_mm'],.4),
    (['mcu_ep_vias','offsets_mm',1],[0,0]),
    (['mcu_ep_vias','offsets_mm',1],[.25,0]),
    (['mcu_ep_vias','offsets_mm',1],[2,0]),
    (['mcu_ep_vias','supplier_process_accepted'],True),
    (['mcu_ep_vias','filled_capped_process_required'],False),
    (['display_ground_return_via','ref'],'U810'),
    (['display_ground_return_via','pad'],'1'),
    (['display_ground_return_via','drill_mm'],.25),
    (['display_ground_return_via','supplier_process_accepted'],True),
    (['display_ground_return_via','expected_via_center_mm'],[18.1,105.75]),
]
for index,(path,value) in enumerate(CASES):
    setattr(PlacementTests,f'test_reject_mutation_{index:02d}',mutation(path,value))

if __name__=='__main__':
    unittest.main(verbosity=2)
