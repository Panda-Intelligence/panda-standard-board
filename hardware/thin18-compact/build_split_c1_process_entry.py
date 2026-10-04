#!/usr/bin/env python3
"""Attach exact via-in-SMT-pad locations and small-land review to the order pack."""
import json
import shutil
from pathlib import Path
from _split_c1_common import ROOT, REPO, sha
from _split_c1_fabrication import require
from audit_split_c1_assembly_process import REPORT, verify_fresh, contact_csv, drill_coverage


def write_process_entry(out, status):
    out = Path(out)
    report = json.loads(REPORT.read_text())
    verify_fresh(report)
    shutil.copy2(REPORT, out/'assembly-process.json')
    text = '''# Split-C1 焊盤過孔與貼片製程要求\n\n**Core 必須向板廠明確指定 Epoxy Filled & Capped（樹脂填孔、研平並蓋銅）**，至少覆蓋以下 `VIA-IN-PAD.csv` 清單。普通阻焊蓋孔／塞油不能當作同一工藝。\n\n這是目前原生 PCB 的幾何量測，不是板廠接單或焊接良率證明。沒有修改銅箔、焊盤、阻焊、孔徑或板框；DRC 為零並不會自動替你選擇填孔製程。\n\n若板廠的訂單選項是全板過孔填孔蓋銅，可依完整過孔清單確認，但 **C301 引腳孔、USB 殼腳槽、其他元件 PTH、安裝孔與 NPTH 必須保持開放**。絕對不要把整份 PTH 鑽孔檔的所有孔都當成過孔填堵。\n\n座標為 KiCad 原生 PCB 俯視毫米座標，Y 向下；背面 B.Cu 也使用同一座標，不能再鏡像。Excellon 匯出的 Y 符號相反，程式已做對應核對。\n\n'''
    overview = {}
    for board, result in report['boards'].items():
        folder = 'core-c1-96x68' if board == 'Core-C1' else 'display-c1-45x36'
        manifest = json.loads((ROOT/'production'/folder/'production-manifest.json').read_text())
        require(result['pcb'] == manifest['files']['pcb'], 'Process map differs from exported PCB')
        fabrication = json.loads((REPO/manifest['files']['fabrication_record']['path']).read_text())
        drill_coverage(result, fabrication['drills'])
        csv_path = out/board/'VIA-IN-PAD.csv'
        csv_path.write_text(contact_csv(result), encoding='utf-8')
        overview[board] = {'pcb_sha256': result['pcb']['sha256'],
                           'via_count': result['via_count'],
                           'land_overlap_hole_count': result['land_overlap_hole_count'],
                           'required_via_treatment': result['required_via_treatment'],
                           'location_csv': board+'/VIA-IN-PAD.csv', 'location_csv_sha256': sha(csv_path),
                           'drill_inventory_matched': True, 'cam_accepted': False}
        text += f"## {board}\n\n原生 PCB SHA-256：`{result['pcb']['sha256']}`。\n\n"
        text += f"共有 **{result['via_count']} 顆貫通過孔**；其中 **{result['land_overlap_hole_count']} 顆孔的鑽孔圓形與 SMT 銅焊盤相交**。只計真正孔圓形相交／中心在焊盤內，沒有用外接矩形相碰或把過孔銅環相碰當作孔在焊盤內。1 µm 多邊形近似誤差內的邊界個案保守列入。\n\n"
        text += '| 孔徑 mm | 正面／背面過孔銅盤 mm | 數量 |\n|---:|---|---:|\n'
        for size in result['via_sizes']:
            text += f"| {size['drill_mm']:g} | {size['front_copper_diameter_mm']:g} / {size['back_copper_diameter_mm']:g} | {size['count']} |\n"
        hits = result['land_overlap_contacts']
        if hits:
            text += '\n| 元件／焊盤 | 面 | X mm | Y mm | 孔徑 mm | 網路 |\n|---|---|---:|---:|---:|---|\n'
            for hit in hits:
                text += f"| {hit['ref']}.{hit['pad']} | {hit['side']} | {hit['center_mm'][0]:g} | {hit['center_mm'][1]:g} | {hit['drill_mm']:g} | {hit['net']} |\n"
        else:
            text += '\n本次沒有檢出焊盤內孔；不表示免除一般阻焊、貼片與小焊盤檢查。\n'
        text += '\n### 小焊盤／鋼網確認\n\n以下是原生銅焊盤至少一個尺寸不大於 0.25 mm 的位號，不全是 BGA。自訂焊盤採實際銅圖尺寸，不把小錨點當成真實焊盤。列出的中心距是幾何量測，不等同所有封裝的名義引腳間距。\n\n| 位號 | 精確 MPN | 面 | 銅焊盤尺寸 mm | 最小不同焊盤中心距 mm |\n|---|---|---|---|---:|\n'
        for group in result['small_smt_land_groups']:
            dimensions = '; '.join(f'{s[0]:g} × {s[1]:g}' for s in group['copper_sizes_mm'])
            text += f"| {group['ref']} | {group['mpn']} | {group['side']} | {dimensions} | {group['minimum_distinct_pad_center_distance_mm']} |\n"
    text += '''\n## 板廠與貼片廠回覆要求\n\n確認 Core 填孔／蓋銅清單、0.20/0.25 mm 過孔及 0.40 mm 小銅盤工藝；WLCSP 的 0.22/0.23 mm 圓焊盤保留 ENIG。0.20/0.23 mm 細長連接器與 QFN 焊盤也需明確接受，不得為套用一般最小值而擅改焊盤。\n\n實際鋼網厚度、縮孔、開窗比、錫膏、EP 焊料量／空洞率、元件方向與檢查方式，均須貼片廠確認。這份清單只記錄銅圖與原生 paste-layer 歸屬，沒有把它當成已批准鋼網。\n\n參考：JLCPCB 官方 Capabilities，2026-10-04 查核的 BGA、Via-in-Pad、Plugged vias、SMD pad 與小孔條目。官方區分填孔蓋銅和阻焊塞孔；四層板不能因為六層以上的預設工藝而假定已包含填孔蓋銅。\nhttps://jlcpcb.com/capabilities/Capabilities?type=1\n\n`assembly-process.json` 保存所有原生過孔、逐孔 UUID、接觸分類及來源 SHA-256；每塊板的 `VIA-IN-PAD.csv` 是最少必須覆蓋的座標清單。工藝接收、物料供料及實板 EVT 仍分開確認。\n'''
    (out/'ASSEMBLY-PROCESS.md').write_text(text)
    status['assembly_process'] = overview
    return status
