# v8 現代化 GUI 設計

## 目標

將「遺忘曲線提醒工具」v8 建置為現代化的 PySide6/Qt 桌面應用程式，同時保留匯入目前 Tkinter 版本所匯出 CSV 檔案的能力。

只有在既有使用者資料能安全移轉到新版時，這次發行才算成功。

## 不可協商的相容性需求

v8 必須能匯入目前 `curve.py` 匯出器產生的 legacy CSV 格式。該格式使用 `record_type` 列，至少包含兩種記錄類型：

- `task`
- `reminder`

必須持續支援的 legacy 欄位如下：

- `record_type`
- `id`
- `task_id`
- `title`
- `category`
- `difficulty`
- `notes`
- `reminder_method`
- `start_time`
- `is_completed`
- `progress_percent`
- `remind_time`
- `reminded`

v8 可以在匯出的 CSV 檔案中新增欄位，但這些 legacy 欄位必須保持存在，讓匯出的資料仍然可理解且可移轉。

## 建議做法

v8 GUI 使用 PySide6/Qt，並在接上介面之前先將應用程式拆分成可測試的模組。

這比只刷新 Tkinter 更合適，因為使用者想要更大幅度的視覺升級，也偏好左側 sidebar command-center 的方向。這也比完整且無結構的重寫更合適，因為 legacy CSV 移轉必須先用測試證明可靠，新的介面才值得信任。

## 架構

建立新的 package，同時在轉換期間保留目前的 `curve.py` 作為 legacy 版本。

規劃模組：

- `src/renew_curve/models.py`：tasks、reminders、settings 與 import results 的 dataclasses 或 typed model objects。
- `src/renew_curve/db.py`：SQLite connection handling、schema creation、migrations、transactions，以及 repository-style operations。
- `src/renew_curve/csv_compat.py`：legacy CSV import、v8 CSV export、CSV validation、import preview counts，以及安全的 replace/merge flows。
- `src/renew_curve/scheduler.py`：forgetting-curve interval generation、progress calculation、due reminder queries、completion updates，以及 snooze time calculation。
- `src/renew_curve/app.py`：PySide6 application entrypoint。
- `src/renew_curve/ui/`：PySide6 widgets and windows。
- `tests/`：compatibility 與 non-GUI business logic 的 pytest coverage。

資料與排程模組不得 import PySide6。GUI 程式碼透過清楚的 functions/classes 使用這些模組。

## 資料模型

v8 繼續使用 SQLite 作為本機資料庫。

最低限度的資料表：

- `tasks`
- `reminders`
- `settings`
- `backgrounds`

schema 可以演進，但必須保留目前的概念：

- 任務標題、分類、難度、筆記、提醒方式、開始時間、完成狀態與進度。
- Reminder 與 task 的關聯、提醒時間，以及 reminded/completed 狀態。
- 用於個人化與通知偏好的 key-value settings。
- 背景圖片 metadata 與 active/random 行為。

應啟用 foreign key constraints。刪除任務時，也應透過受控的 repository operation 或 foreign-key cascade 移除其 reminders。

應針對常用 reminder 查詢加入 indexes：

- 依 `reminded` 與 `remind_time` 查詢 due reminders
- 依 `task_id` 查詢 reminders
- 依 category 與 completion state 查詢 tasks

## Legacy CSV 匯入

CSV 匯入是 v8 的核心功能，不是可選工具。

匯入流程有兩種模式：

- `replace`：從 CSV 建立新資料庫，並且只有在驗證成功後才切換使用。
- `merge`：將 CSV 資料插入目前資料庫，同時將 legacy IDs remap 到新的 task IDs。

安全規則：

- 在 CSV 已解析、驗證、寫入暫存資料庫並檢查之前，絕不刪除或覆寫目前資料庫。
- 如果匯入失敗，保持目前資料庫不變。
- 匯入後根據 reminder completion 重新計算 progress，而不是信任 `progress_percent`。
- 有效時以 ISO strings 保留 reminder timestamps。
- 針對缺少必要欄位、無效 integer 欄位、無效 reminder references，以及無效 datetime values 回報清楚的 validation errors。

匯入驗證應確認：

- 所有必要 legacy 欄位都存在。
- 在 replace mode 中，每個 reminder 都 reference 已知 task。
- Completion fields 可解讀為 `0` 或 `1`。
- Datetime fields 可解析，或在允許處明確視為空白。
- 產生的 task 與 reminder counts 符合預期。

## CSV 匯出

v8 匯出應寫出包含上述 legacy columns 的 CSV 檔案。

匯出列應使用：

- tasks 使用 `record_type=task`。
- reminders 使用 `record_type=reminder`。

可以附加 v8-only columns，但 legacy import 不得要求它們存在。

匯出的 CSV 應支援 round-trip testing：

1. 從 v8 匯出。
2. 匯入到全新的 v8 database。
3. 確認 task count、reminder count、completion state 與 reminder timestamps 相符。

## GUI 設計

使用已核准的 A+C hybrid 方向。

主視窗布局：

- 窄版左側 sidebar 作為主要 navigation。
- 中央 workspace 用於 task management 與 quick overview。
- 右側 panel 用於 calendar 與 selected-day reminder actions。

Sidebar sections：

- `Tasks`
- `Calendar`
- `Import/Export`
- `Settings`

sidebar 可以包含精簡 app mark，例如 `FC`、目前 notification status，以及靠近底部的 do-not-disturb toggle。

中央 workspace：

- due today、completed today、overdue 與 notification state 的 quick stats。
- Search input。
- Category/completion filters。
- Task list 顯示 title、category、next reminder、progress 與 status。
- 新增 task 的 primary action。

右側 panel：

- Monthly calendar，對未完成 reminders 顯示 visual density markers。
- Selected date reminder list。
- Selected reminders 的 actions：complete、snooze，以及適用時 edit task。

Task creation/editing：

- 使用 modal dialog 或 side drawer。
- 欄位：task name、category、difficulty、notes、reminder mode、date/time，以及 forgetting curve mode 的 repeat count。
- 儲存前預覽產生的 reminder times。

Reminder popups：

- 保留 `I reviewed this` 行為。
- 新增 snooze choices：10 minutes、1 hour、tomorrow。
- 防止同一個 reminder 出現重複 popups。
- 尊重持久化的 do-not-disturb mode。

## 個人化

個人化應實用但低風險。

Settings：

- Theme mode：light、dark、follow system。
- Accent color：固定選項，例如 blue、green、purple、orange 與 gray。
- Background image management。
- Background opacity。
- Random startup background。
- Default snooze duration。
- Task list density：comfortable 或 compact。

背景圖片不應降低 task readability。偏好將圖片用於 sidebar 或低透明度背景區域，而不是放在 dense table text 後面。

個人化設定存放於 SQLite `settings`。匯入 legacy task CSV 不應覆寫個人化設定，除非使用者未來選擇 full-backup format。

## 測試策略

使用 pytest 測試 non-GUI logic。

必要測試：

- Legacy CSV imports into a fresh v8 database。
- Import failure leaves the existing database unchanged。
- Merge import remaps task IDs and keeps reminder relationships correct。
- v8 CSV export can be imported into a fresh v8 database。
- Forgetting-curve repeat counts generate expected day offsets。
- Progress calculation reflects completed reminders。
- Snooze choices produce expected new reminder times。

GUI smoke testing 初期可手動進行，但 data migration 不能依賴手動測試。

## Git 與版本管理

使用 branch `codex/v8-modern-gui`。

Commit stages：

1. Design spec。
2. Project scaffolding and tests。
3. Data and CSV compatibility layer。
4. Scheduler logic。
5. PySide6 GUI。
6. README and v8 update record。

新增或更新 ignore rules，避免 local/generated files 意外被 commit：

- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.superpowers/`
- `build/`
- `dist/`
- local SQLite databases

不要在 design step 中移除目前已 tracked 的 build artifacts。如果需要 cleanup，應作為另一個明確的 repository-maintenance change。

## 文件

建立 `update_record/curve_tool_record_v8.md`，內容包含：

- PySide6 GUI upgrade summary。
- Legacy CSV import support 說明。
- Data safety guarantees。
- Personalization features。
- Known migration notes。

更新 `README.md`，說明：

- v8 entrypoint。
- installation dependencies。
- legacy CSV import workflow。
- 如果 report/email features 仍 out of scope，說明其目前狀態。

## v8 範圍外

除非明確核准為新增需求，v8 不需要包含：

- Email report sending。
- Advanced analytics charts。
- Cloud sync。
- Mobile app support。
- 透過 CSV 完整備份 background image binary files。

這些可以在 migration-safe GUI version 存在之後再加入。
