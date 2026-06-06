# Renew Curve v8 專案現況

最後整理日期：2026-06-06

## GitHub 狀態

- `main` 已合併 `codex/v8-modern-gui-impl`，目前主分支內容是 v8 PySide6 版本。
- `codex/v8-modern-gui-impl` 保留為 v8 GUI 實作歷史分支。
- `codex/repo-cleanup` 用於 repo 整理與打包文件更新。

## 目前完成

- PySide6 桌面 GUI 主畫面。
- 今日任務、接下來 3 天、月曆與所有任務列表。
- 新增任務流程，支援遺忘曲線與手動複習日期。
- 今日任務完成與推延。
- SQLite repository 資料層。
- 舊版 CSV 匯入與新版 CSV 匯出相容層。
- ZIP 完整備份與還原。
- 報表 / 資料視窗。
- 主題、重點色、密度、背景與貼圖等個人化設定。
- PyInstaller Windows 打包設定。
- pytest 測試保護。

## 程式架構

- `src/renew_curve/app.py` 是 app 入口。
- `src/renew_curve/models.py` 放資料模型。
- `src/renew_curve/db.py` 管理 SQLite schema、repository 與資料查詢。
- `src/renew_curve/scheduler.py` 管理遺忘曲線排程與進度計算。
- `src/renew_curve/csv_compat.py` 處理舊 CSV 格式。
- `src/renew_curve/backup.py` 處理新版 ZIP 完整備份。
- `src/renew_curve/ui/` 放 PySide6 UI。

## 測試狀態

整理與打包設定更新後：

```text
93 passed
```

主要測試範圍：

- 資料庫 repository。
- 遺忘曲線排程。
- CSV 匯入匯出。
- ZIP 備份。
- GUI 匯入與主要 action。
- 個人化設定保存與匯入保留。

## GitHub 不追蹤的本機產物

下列檔案或資料夾是本機執行、測試或打包產物，不應提交：

- `.venv/`
- `.pytest_cache/`
- `__pycache__/`
- `assets/`
- `build/`
- `dist/`
- `*.db`
- `*.sqlite`
- `*.sqlite3`

## 打包狀態

- 打包設定檔：`renew_curve.spec`
- 單檔打包設定檔：`renew_curve_onefile.spec`
- exe icon：`resources/icons/FC_3_icon.ico`
- repo 內下載版：`release/RenewCurveV8.exe`
- onedir 輸出位置：`dist/RenewCurveV8/RenewCurveV8.exe`
- 使用說明：`docs/PACKAGING.md`

## 整理後的入口文件

- `README.md`：GitHub 首頁與快速開始。
- `docs/PROJECT_STATUS.md`：目前專案狀態。
- `docs/PACKAGING.md`：Windows 打包流程。
- `docs/ROADMAP.md`：後續整理與開發方向。
- `update_record/`：歷代更新紀錄。
