# 遺忘曲線提醒工具 Renew Curve v8

Renew Curve v8 是一款以 Python 製作的桌面端學習複習與任務提醒工具。這個版本將主程式從舊版 Tkinter 單檔架構逐步升級為 PySide6 現代桌面 GUI，並把資料層整理成 SQLite repository，讓後續功能擴充、測試與維護都更穩。

v8 的核心目標是：保留舊版 CSV 資料承接能力，同時建立更現代、更可持續演進的新介面。

## v8 重點

- 現代化 PySide6 GUI：左側月曆切換日期，中間顯示該日任務，下方固定所有任務表格並支援捲動。
- 主要介面繁中化：新版 GUI 的主按鈕、欄位與對話框已改為繁體中文。
- 新增任務流程：可從新版 GUI 建立任務，支援遺忘曲線自動產生與手動輸入複習時間。
- 任務處理流程：今日任務卡可直接完成或推延；推延可用於整批移動該任務後續未完成提醒。
- 報表 / 資料視窗：集中顯示統計、前 7 天總完成率，以及舊版 CSV / 新版 ZIP 資料操作。
- SQLite 資料層重構：以 `ReminderRepository` 管理任務、提醒與個人化設定，降低 GUI 與資料庫耦合。
- 舊版 CSV 匯入：支援從舊版匯出的 `.csv` 匯入新版資料庫，用於舊資料轉移。
- 完整 ZIP 備份：新版完整備份會輸出 `.zip`，包含 SQLite 資料庫、背景、貼圖與個人化設定。
- 個人化設定：支援主題、重點色、密度、預設 snooze、背景參數與貼圖顯示範圍，並在 CSV 匯入時保留設定。
- 測試保護：排程、資料庫、CSV 相容、GUI import 與個人化設定都有 pytest 測試覆蓋。

## v8 資料備份

- `匯入舊版 CSV`：用於舊版資料轉移，請選擇 `.csv`。系統會讀取舊版 `task` 與 `reminder`，並依提醒完成數重新計算進度。
- `匯出完整資料`：輸出新版完整 `.zip`，包含 SQLite 資料庫、背景、貼圖與個人化設定。
- `匯入完整資料`：還原新版完整 `.zip`，系統會先驗證 `manifest.json` 與資料庫檔案，再替換目前資料。
- CSV 是跨版本交換格式；完整備份與日後主要搬移資料請使用 ZIP，避免只搬到任務卻漏掉背景、貼圖和設定。

## 舊資料承接

如果你之前使用舊版匯出 `.csv` 當作備份或資料庫，v8 的設計重點就是讓這些檔案能繼續使用。

- 使用 `報表 / 資料` 的 `匯入舊版 CSV`：以 CSV 內容替換目前任務與提醒資料。
- replace 匯入會保留新版個人化設定，例如主題、重點色、密度與 snooze 偏好。
- 匯入失敗時不會覆蓋原資料庫，避免壞掉的 CSV 造成資料遺失。

## 安裝與執行

建議使用 Python 3.10 或以上版本。

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m renew_curve.app
```

如果只要執行測試：

```bash
.\.venv\Scripts\python -m pytest -q
```

## 專案結構

- `src/renew_curve/app.py`：v8 PySide6 app 入口。
- `src/renew_curve/ui/`：新版 GUI 主視窗、對話框與主題樣式。
- `src/renew_curve/db.py`：SQLite 連線、schema 初始化與 repository。
- `src/renew_curve/csv_compat.py`：舊版 CSV 匯入、匯出與資料轉換。
- `src/renew_curve/scheduler.py`：遺忘曲線排程、進度計算與 snooze 邏輯。
- `tests/`：v8 自動化測試。
- `curve.py`：保留的 Tkinter 舊版主程式，可作為 v7 行為參考。
- `update_record/`：歷代版本更新紀錄。

## 版本狀態

v8 目前完成現代 GUI 主畫面、CSV 承接、新增任務雙排程、今日任務完成/推延、報表資料入口、ZIP 完整備份、個人化設定與資料層重構。舊版的背景提醒彈窗與更完整的素材管理操作，仍可參考 `curve.py` 舊版架構，後續逐步移植到 v8。
