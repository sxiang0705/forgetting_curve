# 遺忘曲線提醒工具（`curve.py`）更新紀錄（v2）

這份 v2 版本主要改動重點：
- GUI 把「新增任務」與「修改任務」分成兩個區塊與按鈕
- 移除「本週/本月/近四週完成率」與「寄送報表」的 GUI 與功能入口（程式內已做成不會再執行的移除 stub）
- 新增 `reminder.db` 的 CSV 匯入/匯出功能（匯入會覆蓋舊資料庫）
- 左側列表修正 `Start Time` 顯示格式（避免使用者看到 raw iso 時間）
- 進度顯示改成「比例長條」（依提醒總數，總格數上限 20，超過就依比例縮放）
- 分類（`category`）改為可自訂輸入，並且篩選選單會依資料庫中實際存在的分類動態更新

---

## 1) 資料庫（仍是 SQLite）

資料庫檔案仍是程式執行目錄下的 `reminder.db`（`DB_PATH = "reminder.db"`）。

表結構維持不變：
- `tasks`
- `reminders`

（v2 沒有新增表；分類可自訂是直接把 `tasks.category` 當字串存入）

---

## 2) 新 GUI 操作方式

左側上方：
- `filter_menu`：篩選
  - `全部`
  - （會動態列出資料庫中出現過的分類）
  - `已完成任務`

左側中間：
- `task_tree`：任務列表
  - `Start Time` 顯示成 `YYYY年MM月DD日 HH點mm分`
  - `Progress` 顯示比例長條：`done/total (percent)`

左側下方：分成兩個區塊

### 2.1 新行程（新增任務）
你要新增一個新的行程：
1. 填 `任務名稱`
2. `分類`：支援直接輸入自訂字串
3. `難度` / `備註`
4. `提醒模式`
   - `手動輸入`：在彈窗中一筆筆加入提醒時間
   - `遺忘曲線`：在彈窗選「開始日期 / 時分 / 複習次數」，系統自動生成提醒日（依內建 mapping）
5. 按 `新增任務並設定提醒`
   - 任務會先寫進 `tasks`
   - 然後跳出「編輯提醒時間」彈窗完成寫入 `reminders`

### 2.2 修改行程（修改舊任務資訊）
1. 在 `task_tree` 點選某一筆任務
2. 下方會自動填入「修改行程」區塊
3. 可修改 `任務名稱 / 分類 / 難度 / 備註`
4. 按 `更新選取任務資訊`

注意：v2 目前「修改行程」只更新 `tasks` 欄位，不會自動重建該任務的 `reminders` 排程（如果要改提醒時間，仍需要用新增/重新建立那類流程）。

---

## 3) 提醒與月曆

- 程式背景執行緒每 30 秒檢查一次：`reminders.reminded=0 且 remind_time <= now`
- 到期提醒會跳出視窗：
  - `我已複習`：標記該 reminder 完成；若該任務所有 reminders 都完成，會把 `tasks.is_completed=1`
  - `收到`：只關閉，不標記完成
- 月曆點日期：
  - 會列出該日未完成的 reminders
  - 允許 `完成` 或 `推延`（把該任務未完成 reminders 的時間全部 +1 天）

---

## 4) CSV 匯入 / 匯出（支援覆蓋舊資料庫）

左側右側按鈕：
- `匯出 CSV`：把目前 `tasks + reminders` 匯出到單一 `.csv` 檔
- `匯入 CSV`：選擇 `.csv` 後會覆蓋舊的 `reminder.db`（不可還原，請先備份）

### CSV 格式（單檔混合 records）
匯出的 CSV 會包含 `record_type` 欄位：
- `record_type=task`：代表一筆 `tasks`
- `record_type=reminder`：代表一筆 `reminders`

欄位會包含（以匯出內容為準）：
- tasks 欄位：`id,title,category,difficulty,notes,reminder_method,start_time,is_completed,progress_percent`
- reminders 欄位：`id,task_id,remind_time,reminded`

v2 的匯入會用這個格式反向重建兩張表。

---

## 5) 已移除的功能（完成率 / 寄信報表）

v2 不再提供下列入口：
- `本週完成率`
- `本月完成率`
- `近四週完成度`
- `寄送所選報告`

所以 GUI 上也不會再有「選擇報告類型」。

