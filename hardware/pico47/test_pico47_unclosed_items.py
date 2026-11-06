"""2026-11-04 Codex: 自动化回归测试未闭合硬件项与工艺约束。

覆盖范围：
1. J201 沉板 Type-C 混合焊盘结构（16 SMD + 4 THT 槽孔）；
2. C402 / C403 0603 元器件同网连接、焊盘与中心间距；
3. SDMMC_D3 高速总线长度与换层过孔约束；
4. 46 孔 IPC-4761 Type VII 盘中孔规格分布与完整性；
5. 21 项待客供物料与 BT301 后装清单完整性；
6. TH801 (CMKD103F3380HANT) 室温阻抗与分压线性化误差边界；
7. 板级 3D 统计参数与制程边界。
"""
import csv
import importlib.util
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
DELIVERABLES_DIR = Path('/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261103-r48/engineering-candidate')
ORDERPACK_DIR = DELIVERABLES_DIR / 'orderpack'


class UnclosedItemsPureDataTests(unittest.TestCase):
    """无需 pcbnew 即可运行的纯数据与数学模型测试。"""

    def test_via_in_pad_46_spec_distribution(self):
        csv_path = ORDERPACK_DIR / 'REQUIRED-VIA-IN-PAD.csv'
        self.assertTrue(csv_path.exists(), f'Missing {csv_path}')
        with open(csv_path, encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 46)

        by_spec = {}
        for r in rows:
            spec = (float(r['diameter_mm']), float(r['drill_mm']))
            by_spec[spec] = by_spec.get(spec, 0) + 1

        self.assertEqual(by_spec.get((0.4, 0.2)), 30)
        self.assertEqual(by_spec.get((0.5, 0.25)), 9)
        self.assertEqual(by_spec.get((0.6, 0.3)), 7)

        # 验证 U501.57 的 9 颗散热接地孔
        u501_vias = [r for r in rows if r['ref'] == 'U501' and r['pin'] == '57']
        self.assertEqual(len(u501_vias), 9)
        self.assertTrue(all(float(r['diameter_mm']) == 0.5 and float(r['drill_mm']) == 0.25 for r in u501_vias))

        # 验证所有孔的 process 属性均为 Type VII 规范
        self.assertTrue(all(r['process'] == 'FILLED_AND_COPPER_CAPPED_OR_SUPPLIER_APPROVED_EQUIVALENT' for r in rows))

    def test_pending_supply_21_parts_inventory(self):
        csv_path = ORDERPACK_DIR / 'PENDING-SUPPLY.csv'
        self.assertTrue(csv_path.exists(), f'Missing {csv_path}')
        with open(csv_path, encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 21)

        refs = {r['ref'] for r in rows}
        self.assertIn('U810', refs)
        self.assertIn('TH801', refs)
        self.assertIn('J201', refs)

        u810 = next(r for r in rows if r['ref'] == 'U810')
        self.assertEqual(u810['manufacturer'], 'Silergy')
        self.assertEqual(u810['mpn'], 'SY7636ARMC')

        th801 = next(r for r in rows if r['ref'] == 'TH801')
        self.assertEqual(th801['manufacturer'], 'FH (Fenghua Advanced)')
        self.assertEqual(th801['mpn'], 'CMKD103F3380HANT')

    def test_required_post_smt_bt301_inventory(self):
        csv_path = ORDERPACK_DIR / 'REQUIRED-POST-SMT.csv'
        self.assertTrue(csv_path.exists(), f'Missing {csv_path}')
        with open(csv_path, encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        bt301 = rows[0]
        self.assertEqual(bt301['ref'], 'BT301')
        self.assertEqual(bt301['mpn'], 'CR1216')
        self.assertEqual(bt301['supply_status'], 'FACTORY_ASSEMBLY_DRAWING_AND_RECEIPT_PENDING')

    def test_th801_temperature_divider_model_and_linearization(self):
        """验证 TH801 (CMKD103F3380HANT) 分压模型及其在室温区间的线性化效果。"""
        r25 = 10000.0
        beta_nom = 3380.0
        beta_high = 3380.0 * 1.03
        beta_low = 3380.0 * 0.97
        t25 = 298.15
        vref = 2.500
        r805 = 7500.0
        r806 = 36000.0

        # 验证 25°C 时的基准电压
        r_ts_25 = (r25 * r806) / (r25 + r806)
        v_ts_25 = vref * r_ts_25 / (r805 + r_ts_25)
        ratio_25 = v_ts_25 / vref
        self.assertAlmostEqual(ratio_25, 0.5106, places=3)
        self.assertAlmostEqual(v_ts_25, 1.2766, places=3)

        # 验证在 0°C ~ 50°C 核心温区内，由于 R806 36kΩ 的并联线性化作用，
        # 即便 B 值存在 ±3% 原厂极限公差，未标定温度绝对误差仍严格保持在 <= 1.0°C 以内
        for t_c in [0.0, 10.0, 20.0, 25.0, 30.0, 40.0, 45.0, 50.0]:
            tk = t_c + 273.15
            for beta_actual in [beta_high, beta_low]:
                r_act = r25 * math.exp(beta_actual * (1.0 / tk - 1.0 / t25))
                r_ts_act = (r_act * r806) / (r_act + r806)
                v_act = vref * r_ts_act / (r805 + r_ts_act)

                # 使用名义公式反推感知温度
                r_ts_per = r805 * v_act / (vref - v_act)
                r_ntc_per = (r_ts_per * r806) / (r806 - r_ts_per)
                tk_per = 1.0 / (1.0 / t25 + (1.0 / beta_nom) * math.log(r_ntc_per / r25))
                t_per_c = tk_per - 273.15

                error_deg = abs(t_per_c - t_c)
                self.assertLessEqual(error_deg, 1.0, f"Error at {t_c}°C with beta={beta_actual} is {error_deg:.3f}°C > 1.0°C")


@unittest.skipUnless(importlib.util.find_spec('pcbnew'), 'KiCad Python required')
class UnclosedItemsKiCadLayoutTests(unittest.TestCase):
    """依赖 pcbnew 的真实 PCB 版图几何与电气约束测试。"""

    @classmethod
    def setUpClass(cls):
        import pcbnew
        cls.board_path = DELIVERABLES_DIR / 'Single.kicad_pcb'
        cls.board = pcbnew.LoadBoard(str(cls.board_path))

    def test_j201_hybrid_smd_and_tht_pads(self):
        import pcbnew
        j201 = self.board.FindFootprintByReference('J201')
        self.assertIsNotNone(j201, 'J201 footprint not found on board')

        pads = list(j201.Pads())
        self.assertEqual(len(pads), 20, f'Expected 20 pads on J201, got {len(pads)}')

        smd_pads = [p for p in pads if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
        tht_pads = [p for p in pads if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)]

        self.assertEqual(len(smd_pads), 16, f'Expected 16 SMD signal pads on J201, got {len(smd_pads)}')
        self.assertEqual(len(tht_pads), 4, f'Expected 4 THT shield slot pads on J201, got {len(tht_pads)}')

    def test_c402_c403_same_net_and_spatial_clearance(self):
        c402 = self.board.FindFootprintByReference('C402')
        c403 = self.board.FindFootprintByReference('C403')
        self.assertIsNotNone(c402, 'C402 footprint not found')
        self.assertIsNotNone(c403, 'C403 footprint not found')

        # 验证两颗电容 Pin 1 均接入同名主供电网络 3V3_AON_SRC
        p402_1 = c402.FindPadByNumber('1')
        p403_1 = c403.FindPadByNumber('1')
        self.assertEqual(p402_1.GetNetname(), '3V3_AON_SRC')
        self.assertEqual(p403_1.GetNetname(), '3V3_AON_SRC')

        # 验证器件中心物理距离在合理包络范围内 (1.904 mm)
        pos2 = c402.GetPosition()
        pos3 = c403.GetPosition()
        center_dist = math.hypot((pos2.x - pos3.x) / 1e6, (pos2.y - pos3.y) / 1e6)
        self.assertGreater(center_dist, 1.80)
        self.assertLess(center_dist, 2.05)

        # 验证器件本体间距 (0603 本体 1.6 x 0.8 mm)
        # C402 (90°) X 范围 [52.85, 53.65]，C403 (180°) X 范围 [50.70, 52.30]
        # X 轴本体净间距 = 52.85 - 52.30 = 0.55 mm
        c402_min_x = (pos2.x / 1e6) - 0.40
        c403_max_x = (pos3.x / 1e6) + 0.80
        body_clearance_x = c402_min_x - c403_max_x
        self.assertGreaterEqual(body_clearance_x, 0.50, f'C402-C403 body clearance {body_clearance_x:.3f} mm < 0.50 mm')

    def test_sdmmc_d3_length_and_via_constraints(self):
        import pcbnew
        tracks = [t for t in self.board.GetTracks() if t.GetNetname() == 'SDMMC_D3' and not isinstance(t, pcbnew.PCB_VIA)]
        vias = [v for v in self.board.GetTracks() if v.GetNetname() == 'SDMMC_D3' and isinstance(v, pcbnew.PCB_VIA)]

        self.assertEqual(len(vias), 2, f'SDMMC_D3 expected 2 vias, got {len(vias)}')
        total_len = sum(t.GetLength() for t in tracks) / 1e6
        self.assertGreater(total_len, 13.5)
        self.assertLess(total_len, 14.5)

    def test_board_outline_and_layer_count(self):
        self.assertEqual(self.board.GetCopperLayerCount(), 4)
        box = self.board.GetBoardEdgesBoundingBox()
        w_mm = box.GetWidth() / 1e6
        h_mm = box.GetHeight() / 1e6
        self.assertAlmostEqual(w_mm, 71.0, delta=0.5)
        self.assertAlmostEqual(h_mm, 99.0, delta=0.5)


if __name__ == '__main__':
    unittest.main()
