# curve.py 程式碼審查與更新建議

看完 `curve.py` 以及 V1~V3 的更新日誌後，我整理了幾個目前架構上的隱患、殘留的技術債，以及對於後續更新的建議：

## 1. 致命問題：Tkinter 的執行緒安全 (Thread Safety)
**問題：** `reminder_checker` 是一個跑在背景 thread 的無窮迴圈，且它在觸發提醒時，又另外開了一個新 thread 去執行 `show_reminder`。而 `show_reminder` 裡面直接呼叫了 `tk.Toplevel()` 等 GUI 操作。**Tkinter 不是 thread-safe 的**，在非主執行緒操作 GUI 非常容易導致程式隨機卡死、崩潰或畫面殘影。
**建議解法：** 廢除 thread，將 `reminder_checker` 的輪詢改用 `root.after(30000, reminder_checker)` 直接在主執行緒排程執行；或是採用 `queue.Queue` 傳遞到期事件給主執行緒建立彈窗。

## 2. 變數命名錯誤 (Typo)
**問題：** 第 24 行宣告了 `popop = None`，但在 `on_calendar_select` 等地方使用的是 `global popup`。這代表全域範圍並沒有確實做到彈窗控管，可能導致舊彈窗無法被正確關閉（呼叫 `popup.winfo_exists()` 前如果沒開過會直接拋出 NameError，雖然被 try-except 壓掉了）。

## 3. 幽靈程式碼 (Zombie Code) 與多餘 Import
**問題：** V2 移除了「寄信」與「圖表報表」功能，但在 `curve.py` 裡還殘留了大量的相依套件 import（例如 `smtplib`, `platform`, `os`, `EmailMessage`, `matplotlib` 等）。此外，相關的函式（如 `show_weekly_pie_chart` 等）雖然在第一行加了 `messagebox` 後 `return`，下方卻還保留著上百行的舊實作。
**建議解法：** 直接大掃除！刪除沒用到的 import 與不會再執行的 code block，讓主程式瘦身，提升可讀性與執行效能。

## 4. 修改任務與提醒排程脫鉤
**問題：** V3 支援雙擊修改任務，但誠如更新日誌提到的，只能改任務資訊，無法重設提醒時間。若發現一開始建立的日期或次數設錯，使用者被迫只能刪除任務重建。
**建議解法：** 可以在「修改任務資訊」的彈窗中，增加一顆「重設提醒時間」的按鈕，按下後呼叫現有的 `open_reminder_popup`（須稍加改寫以支援清除舊提醒），讓 UX 體驗更完整。

## 5. 資料庫鎖死的潛在風險 (DB Concurrency)
**問題：** 背景執行緒每 30 秒讀一次 DB，主執行緒的各種操作（新增/修改/完成/匯入）也頻繁寫入 DB。雖然有 `db_importing` 做簡單阻擋，但在某些極端情況下仍可能觸發 SQLite `database is locked` 錯誤。而且各處都是手動 `conn.close()`，若中間發生 Exception 連線可能卡死。
**建議解法：** 改用 context manager (`with sqlite3.connect(...) as conn:`) 處理資料庫連線，確保發生錯誤時自動安全釋放鎖。

---

**討論方向：**
建議優先處理 **1 (Thread Safety)** 與 **3 (代碼大掃除)**，這兩項對穩定性最有感。
你覺得如何？我們接著要先修復哪個問題？
