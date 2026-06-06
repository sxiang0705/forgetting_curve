# Renew Curve v8

Renew Curve v8 是一款以 Python 製作的桌面端學習複習與任務提醒工具。v8 將舊版 Tkinter 單檔程式整理為 PySide6 桌面應用，並改用 SQLite repository 管理任務、提醒、備份與個人化設定。

這個版本的重點是：保留舊版 CSV 資料承接能力，同時建立更容易維護、測試與持續擴充的新架構。

## 目前狀態

- GitHub `main` 目前已是 v8 PySide6 版本。
- 核心功能已包含任務建立、遺忘曲線排程、今日任務完成/推延、舊版 CSV 匯入、新版 ZIP 完整備份、報表資料視窗與個人化設定。
- 專案已整理為 `src/renew_curve/` 套件結構，測試放在 `tests/`。
- 本機資料庫、使用者上傳素材、虛擬環境與打包產物會被 `.gitignore` 排除，不會進入 GitHub。

更多整理後的現況請看 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)，後續方向請看 [docs/ROADMAP.md](docs/ROADMAP.md)。

## 功能重點

- 現代化 PySide6 GUI，主畫面包含今日任務、接下來 3 天、月曆與所有任務表格。
- 主要介面與對話框已繁體中文化。
- 新增任務支援遺忘曲線自動排程與手動複習日期。
- 今日任務可直接完成或推延，推延會移動後續未完成提醒。
- 報表 / 資料視窗提供完成率統計、舊版 CSV 匯入與新版完整備份。
- SQLite 資料層集中在 `ReminderRepository`，降低 GUI 與資料庫耦合。
- 個人化設定支援主題、重點色、密度、預設 snooze、背景與貼圖素材。
- 自動化測試涵蓋排程、資料庫、CSV 相容、備份、GUI import 與個人化設定。

## 安裝與執行

建議使用 Python 3.10 或以上版本。

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m renew_curve.app
```

也可以使用 console script：

```bash
.\.venv\Scripts\renew-curve
```

## 測試

```bash
.\.venv\Scripts\python -m pytest -q
```

目前整理分支的 baseline 測試結果：

```text
93 passed
```

## 打包

GitHub repo 內提供單檔 Windows exe：

```text
release/RenewCurveV8.exe
```

開發者若要重新打包，建議先用 PyInstaller 的 `onedir` 模式驗證：

```bash
.\.venv\Scripts\python -m PyInstaller --clean --noconfirm renew_curve.spec
```

輸出位置：

```text
dist/RenewCurveV8/RenewCurveV8.exe
```

若要重新產生可直接提交或下載的單檔 exe：

```bash
.\.venv\Scripts\python -m PyInstaller --clean --noconfirm renew_curve_onefile.spec
```

詳細說明請看 [docs/PACKAGING.md](docs/PACKAGING.md)。

## 專案結構

```text
src/renew_curve/        v8 應用程式套件
src/renew_curve/ui/     PySide6 主視窗、對話框與樣式
tests/                  pytest 測試
docs/                   專案現況、路線圖與設計文件
resources/icons/        專案 icon 資源
update_record/          v1 到 v8 歷代更新紀錄
```

主要模組：

- `src/renew_curve/app.py`：v8 PySide6 app 入口。
- `src/renew_curve/db.py`：SQLite schema 初始化與 repository。
- `src/renew_curve/csv_compat.py`：舊版 CSV 匯入、匯出與資料轉換。
- `src/renew_curve/backup.py`：新版 ZIP 完整備份匯入與匯出。
- `src/renew_curve/scheduler.py`：遺忘曲線排程、進度計算與 snooze 邏輯。
- `src/renew_curve/ui/main_window.py`：主畫面。
- `src/renew_curve/ui/dialogs.py`：新增任務、報表資料與個人化對話框。

## 資料與備份

- 舊版資料轉移請使用 `匯入舊版 CSV`。
- 新版完整搬移請使用 `匯出完整資料` / `匯入完整資料`，格式為 `.zip`。
- ZIP 完整備份會包含 SQLite 資料庫、背景、貼圖與個人化設定。
- 本機執行產生的 `renew_curve_v8.db` 不會提交到 GitHub。

## 歷史文件

- [update_record/curve_tool_record_v8.md](update_record/curve_tool_record_v8.md)：v8 更新紀錄。
- [docs/superpowers/specs](docs/superpowers/specs)：v8 設計規格與重設計紀錄。
- [docs/superpowers/plans](docs/superpowers/plans)：v8 實作計畫紀錄。
