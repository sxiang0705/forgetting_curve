# 遺忘曲線提醒工具（`curve.py`）功能與操作紀錄

這份程式是一個桌面 GUI 工具，用來管理「任務（tasks）」與其「複習提醒（reminders）」，並提供：

1. 在左側用表單新增/編輯任務，並指定提醒時間（手動輸入或遺忘曲線自動排程）
2. 背景執行緒每隔一段時間檢查到期提醒，跳出提醒視窗
3. 右側月曆顯示未完成提醒的日期，點日期可看到該天的未完成提醒並可完成/推延
4. 產生完成率圖表（本週/本月/近四週）
5. 把圖表附檔寄到指定信箱

---

## 1) 資料模型（SQLite）

程式使用 SQLite，檔案路徑為程式執行目錄下的 `reminder.db`（因為 `DB_PATH = "reminder.db"`）。

表：`tasks`
- `id`：任務 ID（自增）
- `title`：任務名稱（必填）
- `category`：分類（字串）
- `difficulty`：難度（字串）
- `notes`：備註（文字）
- `reminder_method`：提醒模式（字串；目前只有從 GUI 傳入「手動輸入 / 遺忘曲線」）
- `start_time`：建立/開始時間（isoformat）
- `is_completed`：是否完成（0/1；當該任務所有 reminders 都完成後會被設為 1）
- `progress_percent`：進度百分比（由 `load_tasks()` 計算並回寫）

表：`reminders`
- `id`：提醒 ID（自增）
- `task_id`：對應 `tasks.id`
- `remind_time`：提醒時間（isoformat，iso 字串）
- `reminded`：是否已完成（0/1）

初始化入口：`init_db()` 會建立上述兩張表（不存在就建立）。

---

## 2) GUI 元件概覽

程式啟動後會建立一個 Tkinter 視窗（`root.mainloop()`），介面概分為左右兩塊：

### 左側（任務清單 + 表單）
- `filter_menu`：篩選任務（`全部` / `英文單字` / `法律讀物` / `工作備忘` / `國文課文` / `已完成任務`）
- `task_tree`：任務表格（欄位：`ID`、`任務名稱`、`分類`、`開始時間`、`Progress`）
- 表單欄位：
  - `title_entry`：任務名稱
  - `category_var`：分類（`英文單字 / 程式技能 / 工作備忘 / 日常學習`）
  - `difficulty_var`：難度（`初級 / 中級 / 高級`）
  - `notes_text`：備註
  - `reminder_mode_var`：提醒模式（`手動輸入 / 遺忘曲線`）
  - `report_type_var`：寄送圖表類型（`週報圖 / 月報圖 / 近四週圖`）

按鈕：
- `新增/儲存任務` → `save_task()`
- `刪除所選任務` → `delete_tasks()`
- `一鍵完成任務` → `complete_task_immediately()`
- `本週完成率` → `show_weekly_pie_chart()`
- `本月完成率` → `show_monthly_pie_chart()`
- `近四週完成度` → `show_weekly_bar_chart()`
- `寄送所選報告` → `send_selected_report()`

### 右側（月曆）
- `calendar`（`tkcalendar.Calendar`）：顯示日期選擇，並用 `tag_calendar_by_category()` 對「未完成 reminders」的日期做著色標籤。
- 點日期會觸發 `on_calendar_select()`，彈出該天的未完成提醒清單。

---

## 3) 從 0 開始怎麼用（操作流程）

### 3.1 啟動程式
在此資料夾執行 `curve.py` 後，程式會自動：
1. 建立/更新 `reminder.db` 的表
2. 讀取任務並填入左側列表（`load_tasks()`）
3. 用未完成提醒的日期去標色月曆（`tag_calendar_by_category()`）
4. 背景執行緒開始跑提醒檢查（`reminder_checker()`，每 30 秒查一次）

### 3.2 新增一個任務（並設定提醒）
1. 左側表單填：
   - `任務名稱`
   - `分類 / 難度`
   - `備註`（可選）
2. 設定 `提醒模式`：
   - `手動輸入`：你會在提醒設定視窗逐筆加提醒時間
   - `遺忘曲線`：你只要選「開始日期」與「複習次數」，系統會自動算出多個提醒日
3. 按 `新增/儲存任務`（`save_task()`）：
   - 若你目前沒有選中任何任務（`selected_task_id == -1`），程式會先把任務寫進 `tasks`，
   - 然後立刻跳出「編輯提醒時間」彈窗（`open_reminder_popup(task_id, reminder_method)`）。

接著在「編輯提醒時間」彈窗：

#### A) 手動輸入模式
1. 按 `＋新增提醒`：加入一列（日期 + 時 + 分）
2. 你可以 `－刪除提醒`：刪掉最後一列
3. 左下方會顯示 `預覽`：將提醒於哪些時間（會去重、排序）
4. 按 `💾 儲存提醒`：
   - 只會插入「時間 > 現在」的提醒
   - 寫入 `reminders(task_id, remind_time)`
   - 關閉彈窗，更新月曆標籤與任務列表

#### B) 遺忘曲線模式
1. 在彈窗選 `開始日期`、`時間（時/分）`
2. 選 `複習次數`（目前允許 3~10）
3. `系統會根據複習次數換算提醒間隔天數`（在 `get_curve_days(n)` 裡硬編一個 mapping），例如：
   - 3 次：`[1, 3, 7]`
   - 5 次：`[1, 3, 7, 14, 30]`
   - 10 次：`[1, 3, 7, 14, 30, 60, 90, 120, 180, 365]`
4. 按 `💾 儲存提醒`：
   - 直接把 `開始時間 + mapping 的天數偏移` 全部生成到 reminders
   - 同樣只插入「時間 > 現在」的提醒
   - 更新月曆標籤與任務列表

### 3.3 編輯既有任務（注意：只會改 tasks 欄位，不會自動開提醒重設）
1. 在左側 `task_tree` 點選任務（會觸發 `on_task_select`）
2. 表單會被填入該任務的 `title / category / difficulty / notes`
3. 修改表單後按 `新增/儲存任務`
4. 程式會走更新分支（`UPDATE tasks SET ...`）
5. 注意：程式碼只有在新增新任務時才會 `open_reminder_popup()`；編輯既有任務時不會自動開提醒設定視窗（只更新任務基本欄位）

### 3.4 刪除任務
1. 在 `task_tree` 選取任務（可多選）
2. 按 `刪除所選任務`（`delete_tasks()`）
3. 確認後會同時刪掉：
   - `tasks`
   - 以及該任務的 `reminders`

### 3.5 一鍵完成任務（把該任務所有 reminders 直接標完成）
1. 先在 `task_tree` 選中任務（會更新 `selected_task_id`）
2. 按 `一鍵完成任務`（`complete_task_immediately()`）
3. 程式會：
   - `UPDATE reminders SET reminded = 1 WHERE task_id = ?`
   - `UPDATE tasks SET is_completed = 1 WHERE id = ?`
   - 更新月曆與列表

---

## 4) 提醒與日曆互動（核心行為）

### 4.1 背景提醒檢查（到期才彈窗）
- `reminder_checker()`：無限迴圈，每 30 秒做一次：
  - 查詢 `reminders` 裡 `reminded = 0` 且 `remind_time <= now` 的項目
  - 對每個到期提醒呼叫 `show_reminder(title, reminder_id)`，用 thread daemon 啟動

### 4.2 提醒彈窗（到期就跳）
`show_reminder(title, reminder_id)` 會彈出：
- 標題：`現在是時候複習：{title}`
- 若該 reminder 對應任務有 `notes`，會顯示「備註」
- 按鈕：
  - `我已複習` → 會把該 reminder 設為完成（`reminders.reminded = 1`），若該任務剩餘未完成 reminders 為 0，會把 `tasks.is_completed = 1`
  - `收到` → 只關閉彈窗，不會標完成

完成/更新後會呼叫：
- `tag_calendar_by_category()`
- `load_tasks()`

### 4.3 月曆點日期（看該天未完成提醒）
`on_calendar_select(event)` 的流程：
1. 嘗試關閉之前開過的全域 `popup`
2. 取得你選的日期字串，查詢：
   - `reminders.remind_time` 落在「該日 ~ 次日」區間
   - 且 `reminded = 0`
3. 若該天沒有提醒：顯示 `🎉 今天沒有提醒任務`
4. 若有提醒：對每個 reminder 顯示一列（時間 + 任務標題 + 分類顏色點）
   - `完成`：標記該 reminder 完成、必要時標記整個任務完成，並關閉 popup
   - `推延`：把該任務所有「未完成 reminders」的提醒時間全部 +1 天（先刪後重插），更新月曆並關閉 popup

---

## 5) 圖表與寄送（報表）

### 5.1 圖表按鈕（直接開視窗）
- `本週完成率` → `show_weekly_pie_chart()`
  - 以本週為區間，統計 `reminders.reminded` 的 1/0，畫圓餅圖
- `本月完成率` → `show_monthly_pie_chart()`
  - 以本月為區間，統計完成率，畫圓餅圖
- `近四週完成度` → `show_weekly_bar_chart()`
  - 以最近 4 週為區間逐週統計完成百分比，畫長條圖

所有圖表都會用 `set_chinese_font()` 調整中文字體（避免亂碼），並用 `FigureCanvasTkAgg` 嵌入 Tkinter 子視窗。

### 5.2 寄送所選報告（產生圖片並附檔寄信）
- GUI 按鈕 `寄送所選報告` → `send_selected_report()`
- 它會根據 `report_type_var` 產生對應圖片檔並取得回傳路徑：
  - `週報圖` → `generate_weekly_pie_chart()`：存成 `weekly_pie_chart.png`
  - `月報圖` → `generate_monthly_pie_chart()`：存成 `monthly_pie_chart.png`
  - `近四週圖` → `generate_weekly_bar_chart()`：存成 `weekly_bar_chart.png`
- 儲存位置：`os.getcwd()`（也就是你執行程式時的工作目錄）
- 然後用 `send_email_with_attachment()` 寄出：
  - 附加圖片
  - SMTP 使用 `smtp.gmail.com:465`（SSL）
  - 收件人 `to_email` 寫死為 `a1123308@mail.nuk.edu.tw`
  - 寄件帳號/密碼也在程式內硬編

---

## 6) 注意點（你實務上可能會遇到）

- `reminder_checker()` 與 `show_reminder()` 使用 thread 去觸發 Tkinter 視窗建立：Tkinter 通常要求在主執行緒操作 UI，這裡可能在部分環境出現偶發問題（例如畫面不穩定/卡住）。如果你遇到 GUI 異常，這段是優先排查點。
- `reminder.db` 與圖表圖片會落在「你執行 `curve.py` 的工作目錄」：
  - 你在不同路徑啟動，DB 與輸出圖片就會跑到不同地方。
- `send_email_with_attachment()` 的寄件密碼是硬編在程式裡：
  - 若寄送失敗，你大概率需要改成能登入的密碼/授權方式（以及確認 Gmail 是否允許該登入方式）。

