# Panda 標準電子書板：工具鏈與受控輸入 Manifest

工作包：WP0（工具鏈與受控輸入）
擷取日期：2026-08-10
擷取主機：isaac.liu（macOS，arm64）
狀態：已凍結本機 EDA 工具版本與本地驗證門；板廠層疊與製造輸入**尚未**凍結（見
[unfrozen-inputs.md](unfrozen-inputs.md)）

本文件是 Panda 標準電子書板唯一的工具鏈事實來源。任何原理圖、PCB、仿真或製造輸出都必須能追溯回此處
記錄的精確工具版本。

## 1. EDA 權威源版本（實測）

| 項目 | 實測值 |
| --- | --- |
| 產品 | KiCad |
| 版本 | `10.0.5, release build` |
| 架構 | arm64 on arm64 |
| 二進位路徑 | `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` |
| Build date | `Jul 21 2026 15:54:41` |
| Compiler | Clang 16.0.0 |
| `KICAD_IPC_API` | `ON` |
| 作業系統 | macOS 26.6（Build 25G70） |

KiCad 10.0.5 是 Panda 標準板唯一受控、可編輯的原理圖／PCB／符號／封裝來源。Altium、ODB++、IPC-2581、
PDF、Gerber、CPL 與 STEP 都只是由此權威工程產生並獨立複核的派生／交換檔案，不得形成第二個可雙向編輯的
權威源。任何合作夥伴在派生副本上的修改，必須先在 KiCad 權威源重做，再重新產生全套輸出。

## 2. 隨附相依工具版本（實測）

這些版本決定了 WP3 電路仿真與 WP7／WP8 機構輸出的能力邊界，必須與 KiCad 版本一併記錄。

| 元件 | 版本 | 用途 |
| --- | --- | --- |
| KiCad 內嵌 ngspice library | 45.2 | 只供 KiCad GUI 互動式 simulator；不是 CLI |
| **standalone ngspice CLI** | **46**，`/opt/homebrew/bin/ngspice` | ✅ `ngspice -b` 可批次執行；與內嵌 45.2 分開追溯 |
| OCC (OpenCASCADE) | 7.9.3 | STEP 匯出與 3D／機構碰撞檢查 |
| wxWidgets | 3.2.8 | GUI 框架（記錄用途，非設計輸入） |
| Boost | 1.90.0 | 內部相依（記錄用途，非設計輸入） |

### 2.1 ngspice 能力邊界修正（2026-08-11 實測）

2026-08-10 的歷史狀態是只有 KiCad 內嵌 45.2 shared library、沒有 CLI。2026-08-11 已安裝並實測獨立
Homebrew ngspice 46；目前狀態必須以兩列分開描述：

| 實測事實 | 當前後果 |
| --- | --- |
| KiCad 內嵌 `libngspice.0.dylib` 報 45.2 | 只能由 KiCad GUI 使用；`kicad-cli` 仍無 `sim` 子命令 |
| `/opt/homebrew/bin/ngspice --version` 報 `ngspice-46` | `ngspice -b <netlist>` 的命令列執行器阻塞已解除 |
| TPS63802 官方 `slvmcx1` PSpice ZIP 已取得並由語法探針拒絕；`simulation/sluc687/` 實為 BQ76952 EVM board files；TPS631000 模型加密 | **器件資格阻塞仍存在**：TPS63802 尚無成功受控執行結果，TPS631000 尚無可移植網表 |

因此 L6 的正確狀態是「**executor 可用、TPS63802 model 已取得但不相容、qualification 未執行**」，不是
「無 CLI」，也不是「仿真已通過」。模型檔先經 `simulation/verify-spice-model.sh` 校驗／語法探針；若探針失敗，
改用受控 PSpice for TI 或 EVM／台架，而不是改寫後自行宣稱等價。

## 3. 官方符號／封裝／3D 庫來源

隨附官方庫位於應用程式套件內：

```text
/Applications/KiCad/KiCad.app/Contents/SharedSupport/
├── symbols/      223 個 .kicad_sym
├── footprints/   155 個 .pretty
├── 3dmodels/     105 個 .3dshapes
└── template/     36 個 .kicad_wks（圖框）
```

### 3.1 版本鎖定方式的明確限制

在該 `SharedSupport/` 目錄內**找不到任何獨立的版本標記檔**（無版本檔、無 git 中繼資料）。因此官方庫版本
只能以下列兩項共同鎖定：

1. 隨 KiCad 10.0.5 應用程式套件附帶（Build date `Jul 21 2026 15:54:41`）；
2. 上表 2026-08-10 的檔案清點數量。

**不得**為官方庫編造或假設一個 library git tag／release 版本號。若日後需要更精確的庫版本追溯，必須改為
在專案內 vendor 一份明確版本的官方庫，並在本文件補記該來源與校驗值；在完成該遷移之前，庫版本的追溯精度
就是「隨 10.0.5 套件附帶 + 清點數量」，不能寫成更強的聲明。

## 4. WP0 凍結的本地驗證門

下列命令是 WP0 凍結的本地門。`KICAD_CLI` 路徑是本機已驗證的 macOS 路徑；其他主機只能在驗證到相同的
KiCad 10.0.5 之後替換該路徑，不得退回或混用其他主版本。

```bash
KICAD_CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
"$KICAD_CLI" version
"$KICAD_CLI" sch erc --exit-code-violations <board>.kicad_sch
"$KICAD_CLI" pcb drc --schematic-parity --exit-code-violations <board>.kicad_pcb
"$KICAD_CLI" pcb export gerbers --output <fab-dir> <board>.kicad_pcb
"$KICAD_CLI" pcb export drill --output <fab-dir> <board>.kicad_pcb
"$KICAD_CLI" pcb export step --output <board>.step <board>.kicad_pcb
```

### 4.1 命令成功不等於工程正確

`--exit-code-violations` 讓 ERC／DRC 違規以非零退出碼失敗，可作為自動門；但匯出命令成功**只證明工具
執行完成**，不證明層別選擇、原點、板框、鑽孔對位或裝配方向正確。因此：

- Gerber／鑽孔必須用**獨立查看器回讀**，並由人工工程審查確認層別、原點、板框與極性；
- STEP 必須做 3D／機構碰撞檢查；
- 任何 ERC／DRC 例外都必須寫明原因與證據，不得以「命令已通過」代替。

## 5. 擷取命令

本文件事實由下列命令於 2026-08-10 擷取：

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli version
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli version --format about
sw_vers
/opt/homebrew/bin/ngspice --version
cd /Applications/KiCad/KiCad.app/Contents/SharedSupport
ls symbols/*.kicad_sym | wc -l
ls -d footprints/*.pretty | wc -l
ls -d 3dmodels/*.3dshapes | wc -l
ls template/*.kicad_wks | wc -l
ls   # 確認無獨立版本標記檔
```

## 6. 變更規則

- 升級 KiCad、更換主機或改變官方庫來源時，必須先更新本文件，再重新產生受影響的派生／製造輸出。
- 已發布板號／修訂的製造輸出，必須保留其產生時的工具版本記錄；不得以新工具版本回頭改寫舊 manifest 的
  版本欄位。
- 交叉引用：目錄邊界見 [README.md](README.md)，符號／封裝複核規則見
  [symbol-footprint-rules.md](symbol-footprint-rules.md)，板號與製造 manifest 欄位見
  [document-numbering.md](document-numbering.md)。
