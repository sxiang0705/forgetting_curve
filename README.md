# 遺忘曲線提醒工具 Renew Curve v8

Renew Curve v8 是一款以 Python 製作的桌面端學習複習與任務提醒工具。這個版本將主程式從舊版 Tkinter 單檔架構逐步升級為 PySide6 現代桌面 GUI，並把資料層整理成 SQLite repository，讓後續功能擴充、測試與維護都更穩。

v8 的核心目標是：保留舊版 CSV 資料承接能力，同時建立更現代、更可持續演進的新介面。

## v8 重點

- 現代化 PySide6 GUI：三欄式工作介面，包含側邊導覽、任務表格、統計卡片與右側日曆區。
- 新增任務流程：可從新版 GUI 建立任務，並依遺忘曲線自動產生 3 到 10 次複習提醒。
- SQLite 資料層重構：以 `ReminderRepository` 管理任務、提醒與個人化設定，降低 GUI 與資料庫耦合。
- 舊版 CSV 匯入/匯出：支援從舊版匯出的 `.csv` 匯入新版資料庫，也能從新版匯出相容格式。
- 兩種匯入模式：`replace` 可替換任務資料，`merge` 可把舊 CSV 追加到現有資料庫。
- 個人化設定：支援主題、重點色、密度與預設 snooze 選項，並在 CSV replace 匯入時保留這些設定。
- 測試保護：排程、資料庫、CSV 相容、GUI import 與個人化設定都有 pytest 測試覆蓋。

## 舊資料承接

如果你之前使用舊版匯出 `.csv` 當作備份或資料庫，v8 的設計重點就是讓這些檔案能繼續使用。

- 使用 `Import/Export` 的 `Import replace`：以 CSV 內容替換目前任務與提醒資料。
- 使用 `Import/Export` 的 `Import merge`：把 CSV 內容加入目前資料庫，不覆蓋既有任務。
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

v8 目前完成現代 GUI 基礎、CSV 承接、新增任務、個人化設定與資料層重構。舊版的圖表報表寄送、完整背景圖片管理與背景提醒彈窗，仍保留在 `curve.py` 舊版架構中，後續可逐步移植到 v8。
