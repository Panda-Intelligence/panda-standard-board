#!/usr/bin/env python3
"""Generate the actual factory entry from checked per-board output, not history."""
import json
import shutil
import subprocess
from pathlib import Path
from _split_c1_common import ROOT, REPO, sha
from _split_c1_fabrication import load_contract, require, validate_archive


def write_entry(out, report):
    out=Path(out);contract=load_contract();rows=[];identities={};pending={};fab_records={}
    shutil.copy2(ROOT/'split-c1-fabrication-contract.json',out/'split-c1-fabrication-contract.json')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    native_matches_head=True
    for board,folder in [('Core-C1','core-c1-96x68'),('Display-C1','display-c1-45x36')]:
        prod=ROOT/'production'/folder;manifest=json.loads((prod/'production-manifest.json').read_text())
        require(manifest['board_id']==board and not any(manifest['native_checks'].values()),'Invalid native board manifest')
        for entry in manifest['files'].values():
            require(sha(REPO/entry['path'])==entry['sha256'],'Stale manufacture file: '+entry['path'])
        f=manifest['files'];pcb=f['pcb'];identities[board]=pcb
        original=subprocess.check_output(['git','show',revision+':'+pcb['path']],cwd=REPO)
        native_matches_head &= original==(REPO/pcb['path']).read_bytes()
        fab=json.loads((REPO/f['fabrication_record']['path']).read_text());spec=contract['boards'][board]
        require(fab['native_pcb']==pcb and fab['selection']==spec,'Mismatched fabrication source/selection')
        require(fab['contract']['sha256']==sha(ROOT/'split-c1-fabrication-contract.json'),'Stale fabrication contract')
        dest=out/board
        zip_path=dest/(board+'-Gerber-Drill.zip')
        drills=validate_archive(zip_path,spec,board,pcb['sha256'])
        for name,key in [('FABRICATION.md','fabrication_notes'),('fabrication.json','fabrication_record'),('RAW-KICAD-JOB.json','raw_kicad_job')]:
            shutil.copy2(REPO/f[key]['path'],dest/name)
        state=report['boards'][board]
        require(state.get('standard_fabrication_ready') is True and not state.get('pending_violations'), 'Native rule DFM did not complete')
        state.update(native_rule_dfm_passed=True,standard_fabrication_ready=False,
                     cam_acceptance_required=True,cam_accepted=False,
                     fabrication_selection=spec,cam_confirmations=contract['cam_confirmations'])
        fab_records[board]={'record':board+'/fabrication.json','sha256':sha(dest/'fabrication.json'),
                            'gerber_zip':board+'/'+zip_path.name,'gerber_zip_sha256':sha(zip_path),
                            'job_revision':board+'-'+pcb['sha256'][:12]}
        pending[board]=state['unmapped_smt_refs']
        cu=' / '.join(f'{v*1000:g}' for v in spec['copper_thickness_mm'])
        rows.append(f"| {board} | {spec['dimensions_mm'][0]:g} × {spec['dimensions_mm'][1]:g} | {len(spec['layers'])} | 0.8 | {cu} | {state['smt_positions']} | {len(state['unmapped_smt_refs'])} |")
    report.update(source_git_commit_observed=revision,native_pcbs_match_observed_commit=native_matches_head,
                  fabrication_records=fab_records,ready_for_cam_review=True,cam_accepted=False,
                  automatic_fabrication_order_ready=False,
                  manufacturing_geometry_passed_does_not_mean_process_accepted=True)
    from build_split_c1_process_entry import write_process_entry
    report=write_process_entry(out,report)
    text='''# Split-C1 打樣入口 — 只使用本包兩塊板\n\n此入口由目前已核對的 PCB／BOM／Gerber 自動生成，沒有混用 Thin7 或舊整合板。\n\n**用途：板廠 CAM 審核及工程打樣資料；不是已批准的量產、貼片訂單或實板性能驗證。**\n\n## 分板上傳\n\n裸板上傳 `Core-C1/Core-C1-Gerber-Drill.zip` 與 `Display-C1/Display-C1-Gerber-Drill.zip`，分別建立兩個工作。完整總包不是單板 Gerber。\n\n| 板 | 成品名義尺寸 mm | 銅層 | 板厚 mm | 從上到下銅厚 µm | SMT 位號數 | 尚缺精確供料映射 |\n|---|---|---:|---:|---|---:|---:|\n'''+ '\n'.join(rows)+'''\n\n兩板均指定 **ENIG、綠色阻焊、名義 0.8 mm 板厚**。Core 內層是約 35 µm／1 oz，不是舊表的 0.5 oz；不要接受自動套用較薄內銅。最終公差及介質結構須由板廠確認。\n\n## 下單前 CAM 必須確認\n\nCore C301 已改為兩個 **1.9 mm 鍍通圓孔／2.3 mm 圓焊盤**，保留 20 mm 腳距及極性，消除原本短槽的加工例外；所有原有走線保持不變。圓孔公差與扁腳尺寸已做計算核對，實物插入、孔銅與手焊填錫仍須首板驗證。不要回用 1.8 × 1.4 mm 的舊槽孔版本。\n\nCore 小孔含 0.20 mm 工具，部分需小孔工藝；USB 殼腳槽與 C301 圓孔均在 PTH 檔。NPTH 檔要一併上傳，即使 Display 沒有 NPTH 孔。不得交換內層、鏡像或縮放。\n\n`.gbrjob` 的板厚、尺寸、銅厚、ENIG、綠油與本入口一致；舊的未完成版本字串和錯誤顏色已在匯出層修正。原始 RAW-KICAD-JOB.json 只作核對，不是交付加工設定。未經確認的阻抗控制聲明已移除，但這不代表取消 SI／阻抗要求或取得阻抗資格。實際層疊與任何阻抗配方仍需工程確認；禁止板廠擅改線寬。\n\n## 貼片與後裝\n\n各板使用自己目錄的 BOM_JLCPCB.csv／CPL_JLCPCB.csv。CPL 是單板座標；不可用在未重新換算的拼板。底面裝配觀察圖可以鏡像，CPL 不可再任意鏡像。\n\nC301 超級電容由客戶獨立採購、PCBA 回板後手焊；TH301 是板外熱敏元件，均不混入 SMT CPL。TP19 是裸銅測試點，不是漏貼料件。七個既有 IC 位號仍缺精確映射／客供接收，不能不貼或代碼湊數：\n\n'''
    for board,refs in pending.items():
        text+=f"- {board}: "+(', '.join(refs) if refs else '沒有缺碼位號；實際庫存／接收仍待確認')+'\n'
    process=report['assembly_process']
    text+=f"\n## 焊盤過孔：必須指定製程\n\nCore 原生 {process['Core-C1']['via_count']} 顆過孔中，**{process['Core-C1']['land_overlap_hole_count']} 顆孔與 SMT 銅焊盤相交**。下單明確指定 **Epoxy Filled & Capped** 至少覆蓋 `Core-C1/VIA-IN-PAD.csv` 清單，不要用蓋油或塞油代替。Component PTH、C301 引腳圓孔、USB 殼腳槽與 NPTH 不得填堵。\n\nDisplay 本次檢出 {process['Display-C1']['land_overlap_hole_count']} 顆；兩板的小焊盤、鋼網與貼片工藝仍須確認。詳見 `ASSEMBLY-PROCESS.md`、`assembly-process.json` 與逐板座標 CSV。此工藝成本／接收未經板廠確認，不是已下單。\n"
    text+='''\n## 首次上電\n\n先按 `SPLIT-C1-HARDWARE-FINISH.md` 接地 TP19 撤銷許可，再做限流上電與電源節點檢查。未核准的舊韌體不得沿用；P05 是主動高充電請求，P15 未使用，GPIO2 是直接硬體許可。TP19 不是自動看門狗。沒有任何實板充電、熱、USB、面板、RTC 或 RF 測試被標成完成。\n\n## 來源與防混檔\n\n'''
    text+=f"產生時觀察到的 Git HEAD：`{revision}`。兩塊原生 PCB 與該提交是否逐位元相同：`{str(native_matches_head).lower()}`。實際檔案 SHA-256 以下列為準。\n\n"
    for board,entry in identities.items():
        text+=f"- {board} PCB：`{entry['sha256']}`；Gerber ZIP：`{fab_records[board]['gerber_zip_sha256']}`。\n"
    text+='\n`SHA256SUMS` 涵蓋本包檔案；`prototype-status.json`、各板 `fabrication.json` 及 `FABRICATION.md` 保存檢查、圖層及製程條件。確認板廠回傳 CAM 預覽仍對應這些來源後再下單。\n'
    (out/'START-HERE.md').write_text(text)
    return report
