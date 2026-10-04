# Split-C1 工程打樣交接

目前主線是已完成拆板的 Core-C1＋Display-C1。Thin7／portrait-R2 是另一個未完成的機構方案，不能替代本次台架原型的來源。

## 唯一製造入口

在完整 Git 歷史的工作目錄執行：

```sh
python3 hardware/thin18-compact/release_split_c1.py --target split-c1
```

產出 `production/Panda-Split-C1-JLC-Prototype.zip`。總包內的 **START-HERE.md** 由這次已核對的 PCB、BOM、Gerber 與製程契約自動生成；位號數、缺料位號、來源雜湊及分板檔名均以它為準。這份文件不再疊加已失效的歷史說明。

裸板分別上傳：

```text
Core-C1/Core-C1-Gerber-Drill.zip
Display-C1/Display-C1-Gerber-Drill.zip
```

不要把完整總包當成單板 Gerber，也不要加入舊整合板或 Thin7 空板框。

## 板廠參數

| 項目 | Core-C1 | Display-C1 |
|---|---|---|
| 名義成品尺寸 | 96 × 68 mm | 45 × 36 mm |
| 銅層順序 | F.Cu／In1.Cu／In2.Cu／B.Cu | F.Cu／B.Cu |
| 名義板厚 | 0.8 mm | 0.8 mm |
| 從上到下銅厚 | 35／35／35／35 µm | 35／35 µm |
| 表面／阻焊 | ENIG／綠油 | ENIG／綠油 |
| 板型 | 單板、銑外形 | 單板、銑外形 |

**Core 內銅約 1 oz，不是旧表中的 0.5 oz。** 此項保持原生 CAD 的銅厚，不能直接接受板廠預設較薄內銅。原廠公開能力列出內銅 0.5／1／2 oz，0.5 oz 是預設；實際層疊、0.8 mm 公差與訂單選項仍需 CAM 確認。

製造匯出會保留原始 KiCad job 作核對，再修正交付 `.gbrjob` 的來源版本、名義尺寸、ENIG 與綠油。原來無對應阻抗配方的 `ImpedanceControlled` 聲明不再出現在交付 job。這不是取消電氣／阻抗要求，也不是宣告阻抗測試通過；禁止擅自改線寬或堆疊。銅箔、阻焊圖形、外形與鑽孔座標均不因這項元資料處理而改變。

## 必須取得的 CAM 確認

Core C301 現在使用 **1.9 mm 鍍通圓孔／2.3 mm 圓焊盤**、20 mm 腳距，已消除原本短橢圓槽的加工例外。每個孔的位置、孔徑與極性都由原生 CAD 和鑽孔匯出核對；不改成 NPTH，不回用舊槽孔。公差計算與首板插入／手焊條件見 `SPLIT-C1-CAP-DRILL.md`。

Core 包含 0.20 mm 小孔；USB 外殼槽和 C301 圓孔在 PTH 檔。PTH、NPTH 兩份檔案都保留。Display 的 NPTH 檔可以是零孔，不應因此猜測檔案遺失。兩板不要縮放、整體鏡像或對調內層。

正式 PCBA 還需要封裝供料、WLCSP／細間距、過孔處理、鋼網、工藝邊及底面旋轉確認。沒有批准的組合拼板；單板 CPL 不能直接當作拼板 CPL。Assembly-Bottom.svg 是觀察圖，不是額外鏡像座標的指令。

## 裝配與後裝

`BOM_JLCPCB.csv` 只對應同板 `CPL_JLCPCB.csv` 的 SMT 位號。完整系統 BOM 另包含後裝 C301 與板外 TH301。TP19 是裸銅測試點，不是漏貼元件。

C301 精確料號是 KAMCAP SE-5R5-D105VYH3C／C2894294；正端接 pad1 RTC_VBACKUP，負端接 pad2 GND。獨立供料，PCBA 回板後手焊，不混入 SMT 回流；引腳修剪、毛刺及 1.5 mm 板間隙按硬體交接要求核對。TH301 固定於電池並接 J302；浮地 BTL 喇叭 J502 兩端不可接地。

Core J601 與 Display J1 使用同廠配套 HCTL 60-pin 連接器。插接方向、pin1、35/36 電源及底面旋轉按生成圖確認；不混用旧 Hirose 件。Q907／Q908／Display Q1 的 JSM MOS 是 **1G／2D／3S**，不可套用別家同外形的腳序。

七個既有 SMT 位號 U402–U405、U902、U905、U906 仍需精確映射或客供接收。參見生成包的 sourcing、consignment 與 supply-plan 記錄。公開庫存、已有 C 碼或全國產身份都不代表料已預留／被裝配廠接收；不得不貼或相似料號替代。

## 首板上電與放行邊界

先按 `SPLIT-C1-HARDWARE-FINISH.md` 接地 TP19，撤銷前光／充電許可，再做限流上電、電源與極性檢查。P05 已是主動高 CHG_REQUEST，P15 不再控制前光，GPIO2 為直接硬體許可；舊韌體不相容。

零原生 DRC／未連接／一致性／ERC，以及不可變基線重建一致，是設計資料檢查；不是 CAM、貼片供料或實板驗證。USB／充電／NTC／溫升／RF／面板／RTC 以及電池機構仍按首板計畫測試。沒有外部自動看門狗、沒有宣稱已通過實板測試。

`ready_for_cam_review=true`；`cam_accepted=false`、`automatic_fabrication_order_ready=false`、`assembly_order_ready=false`、`manufacturing_release=false` 直到各自條件取得證據。生成入口會清楚顯示這些不同狀態。

## 參考與可追溯性

製程能力原廠來源（2026-10-04 核對）：https://jlcpcb.com/capabilities/pcb-capabilities 。Gerber job 用於傳遞製造特性：https://www.ucamco.com/en/gerber 。

實際契約為 `split-c1-fabrication-contract.json`；各板 `fabrication.json`／`FABRICATION.md` 包含來源與槽孔／圖層核對。`SHA256SUMS` 覆蓋總包，最後的 `verify_split_c1_fabrication.py` 重新比對分板與總包。生成檔案留在 production，不把大型 ZIP 混進 CAD 原始碼。
