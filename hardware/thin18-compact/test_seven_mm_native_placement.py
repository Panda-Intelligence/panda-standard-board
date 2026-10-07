import unittest
from verify_seven_mm_native_placement import world_point,check_port_pose

class PortPoseTests(unittest.TestCase):
    def test_usb_mouth_not_origin(self):
        r=check_port_pose('J201',[37.5,105.2],0,'MUP','U22401-17')
        self.assertEqual(r['native_mouth_xy_mm'],[37.5,111.7])
        self.assertEqual(r['mouth_to_opening_distance_mm'],.3)
    def test_microsd_side_corner(self):
        r=check_port_pose('J501',[60.8,96],90,'XUNPU','TF-122-CCP9')
        self.assertEqual(r['native_mouth_xy_mm'],[74.75,96])
        self.assertFalse(r['plug_card_clearance_physically_verified'])
    def test_usb_label_as_origin_fails(self):
        with self.assertRaises(ValueError):check_port_pose('J201',[37.5,112],0,'MUP','U22401-17')
    def test_wrong_port_side(self):
        with self.assertRaises(ValueError):check_port_pose('J501',[60.8,96],270,'XUNPU','TF-122-CCP9')
    def test_side_center_rejected(self):
        with self.assertRaises(ValueError):check_port_pose('J501',[60.8,56],90,'XUNPU','TF-122-CCP9')
    def test_usb_not_centered(self):
        with self.assertRaises(ValueError):check_port_pose('J201',[30,105.2],0,'MUP','U22401-17')
    def test_changed_package(self):
        with self.assertRaises(ValueError):check_port_pose('J201',[37.5,105.2],0,'MUP','U20405-01')
    def test_rotation_convention(self):
        p=world_point([2,3],90,[1,4])
        self.assertAlmostEqual(p[0],6);self.assertAlmostEqual(p[1],2)

if __name__=='__main__':unittest.main(verbosity=2)
