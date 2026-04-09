import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import Calendar
from tkcalendar import DateEntry
import sqlite3
import shutil
import random
from PIL import Image, ImageTk, ImageOps
import datetime
import time
import os
import csv
import hashlib

DB_PATH = "reminder.db"

class TransparentTaskTree(tk.Canvas):
    def __init__(self, master, columns, **kwargs):
        kwargs.pop("show", None)
        kwargs.pop("selectmode", None)
        super().__init__(master, bg="white", highlightthickness=0, **kwargs)
        self.columns = columns
        self.col_widths = [50, 220, 90, 110, 200]
        self.header_text = ["ID", "任務名稱", "分類", "開始時間", "進度"]
        self.row_h = 46
        self.items = []
        self.selected_item = None
        
        self.bg_photo = None
        self.last_pil_img = None
        self.bg_canvas_id = self.create_image(0, 0, anchor="nw")
        
        from PIL import Image, ImageTk
        hdr_img = Image.new('RGBA', (1500, self.row_h), (50, 50, 50, 200))
        row_img = Image.new('RGBA', (1500, self.row_h), (255, 255, 255, 220))
        sel_img = Image.new('RGBA', (1500, self.row_h), (0, 120, 215, 180))
        
        self.hdr_photo = ImageTk.PhotoImage(hdr_img)
        self.row_photo = ImageTk.PhotoImage(row_img)
        self.sel_photo = ImageTk.PhotoImage(sel_img)
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<Double-1>", self.on_double_click)
        self.bind("<MouseWheel>", self.on_mousewheel)
        self.bind("<Configure>", self.on_resize)
        
        self.scroll_y = 0
        self.max_scroll = 0

    def heading(self, col, text):
        pass 

    def insert(self, parent, index, values):
        self.items.append({'values': values})
        self.draw_grid()

    def delete(self, *args):
        if not args:
            self.items.clear()
            self.selected_item = None
            self.draw_grid()
        else:
            super().delete(*args)

    def get_children(self):
        return []
        
    def identify_row(self, y):
        row = int((y - self.scroll_y - self.row_h) / self.row_h)
        if 0 <= row < len(self.items):
            return row
        return None
        
    def item(self, iid):
        return self.items[iid]
        
    def selection(self):
        if self.selected_item is not None:
            return [self.selected_item]
        return []
        
    def on_click(self, event):
        row = int((event.y - self.scroll_y - self.row_h) / self.row_h)
        if 0 <= row < len(self.items):
            self.selected_item = row
            self.draw_grid()
            self.event_generate('<<TreeviewSelect>>')
            
    def on_double_click(self, event):
        row = int((event.y - self.scroll_y - self.row_h) / self.row_h)
        if 0 <= row < len(self.items):
            self.selected_item = row
            self.draw_grid()
            self.event_generate('<Double-1>')
            
    def on_mousewheel(self, event):
        content_h = len(self.items) * self.row_h + self.row_h
        win_h = self.winfo_height()
        if content_h > win_h:
            try:
                delta = int(-1*(event.delta/120)) * 40
            except:
                delta = 0
            self.scroll_y -= delta
            min_y = win_h - content_h
            if self.scroll_y < min_y: self.scroll_y = min_y
            if self.scroll_y > 0: self.scroll_y = 0
            self.draw_grid()
            
    def set_background(self, pil_img):
        self.last_pil_img = pil_img
        self.resize_bg()
        
    def on_resize(self, event):
        self.resize_bg()
        self.draw_grid()
        
    def resize_bg(self):
        if not self.last_pil_img: 
            self.itemconfig(self.bg_canvas_id, image="")
            return
            
        w, h = self.winfo_width(), self.winfo_height()
        if w > 10 and h > 10:
            from PIL import ImageOps, ImageTk, Image
            img = ImageOps.fit(self.last_pil_img, (w, h), Image.Resampling.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(img)
            self.itemconfig(self.bg_canvas_id, image=self.bg_photo)

    def draw_grid(self):
        self.delete("grid_elem")
        y = self.scroll_y
        x = 0
        
        self.create_image(0, y, anchor="nw", image=self.hdr_photo, tags="grid_elem")
        for i, hd in enumerate(self.header_text):
            self.create_text(x + 15, y + self.row_h/2, text=hd, anchor="w", font=("微軟正黑體", 11, "bold"), fill="white", tags="grid_elem")
            x += self.col_widths[i]
            
        y += self.row_h
        
        for idx, item in enumerate(self.items):
            if y + self.row_h > 0 and y < self.winfo_height():
                img = self.sel_photo if idx == self.selected_item else self.row_photo
                self.create_image(0, y, anchor="nw", image=img, tags="grid_elem")
                
                x = 0
                for i, val in enumerate(item['values']):
                    color = "white" if idx == self.selected_item else "black"
                    wrap_w = self.col_widths[i] - 15 if i != 4 else 350
                    self.create_text(x + 15, y + self.row_h/2, text=str(val), anchor="w", font=("微軟正黑體", 11), fill=color, width=wrap_w, tags="grid_elem")
                    x += self.col_widths[i]
            y += self.row_h

BG_DIR = "backgrounds"
bg_image_keep_ref = None
popup = None
db_importing = False
notifications_paused = False

DEFAULT_CATEGORIES = ["英文單字", "程式技能", "工作備忘", "日常學習"]
DEFAULT_DIFFICULTIES = ["初級", "中級", "高級"]
_CATEGORY_COLOR_PALETTE = [
    "#ff9999", "#99ccff", "#99ff99", "#ffcc99", "#ccccff",
    "#ffccff", "#c6f7d0", "#f7d7a6", "#d0e2ff", "#ffd1d1",
]


def get_category_color(category: str) -> str:
    """
    為任意字串的分類產生穩定顏色（跨執行不隨 Python hash 隨機化而改變）。
    """
    if not category:
        return "#000000"
    digest = hashlib.md5(category.encode("utf-8")).hexdigest()
    idx = int(digest, 16) % len(_CATEGORY_COLOR_PALETTE)
    return _CATEGORY_COLOR_PALETTE[idx]


def export_db_to_csv(csv_path: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, category, difficulty, notes, reminder_method, start_time, is_completed, progress_percent FROM tasks")
    task_rows = cursor.fetchall()

    cursor.execute("SELECT id, task_id, remind_time, reminded FROM reminders")
    reminder_rows = cursor.fetchall()

    conn.close()

    fieldnames = [
        "record_type",
        "id",
        "task_id",
        "title",
        "category",
        "difficulty",
        "notes",
        "reminder_method",
        "start_time",
        "is_completed",
        "progress_percent",
        "remind_time",
        "reminded",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in task_rows:
            task_id, title, category, difficulty, notes, reminder_method, start_time, is_completed, progress_percent = row
            writer.writerow(
                {
                    "record_type": "task",
                    "id": task_id,
                    "task_id": "",
                    "title": title,
                    "category": category,
                    "difficulty": difficulty,
                    "notes": notes,
                    "reminder_method": reminder_method,
                    "start_time": start_time,
                    "is_completed": is_completed,
                    "progress_percent": progress_percent,
                    "remind_time": "",
                    "reminded": "",
                }
            )

        for row in reminder_rows:
            reminder_id, task_id, remind_time, reminded = row
            writer.writerow(
                {
                    "record_type": "reminder",
                    "id": reminder_id,
                    "task_id": task_id,
                    "title": "",
                    "category": "",
                    "difficulty": "",
                    "notes": "",
                    "reminder_method": "",
                    "start_time": "",
                    "is_completed": "",
                    "progress_percent": "",
                    "remind_time": remind_time,
                    "reminded": reminded,
                }
            )


def import_db_from_csv(csv_path: str) -> None:
    global db_importing
    db_importing = True
    try:
        # 覆蓋舊的 reminder.db
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()

        with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        task_rows = [r for r in rows if r.get("record_type") == "task"]
        reminder_rows = [r for r in rows if r.get("record_type") == "reminder"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for r in task_rows:
            cursor.execute(
                """
                INSERT INTO tasks (id, title, category, difficulty, notes, reminder_method, start_time, is_completed, progress_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(r["id"]) if r.get("id") else None,
                    r.get("title", ""),
                    r.get("category", ""),
                    r.get("difficulty", ""),
                    r.get("notes", ""),
                    r.get("reminder_method", ""),
                    r.get("start_time", ""),
                    int(r["is_completed"]) if r.get("is_completed") not in (None, "", "null") else 0,
                    float(r["progress_percent"]) if r.get("progress_percent") not in (None, "", "null") else 0.0,
                ),
            )

        for r in reminder_rows:
            cursor.execute(
                """
                INSERT INTO reminders (id, task_id, remind_time, reminded)
                VALUES (?, ?, ?, ?)
                """,
                (
                    int(r["id"]) if r.get("id") else None,
                    int(r.get("task_id", "")),
                    r.get("remind_time", ""),
                    int(r["reminded"]) if r.get("reminded") not in (None, "", "null") else 0,
                ),
            )

        conn.commit()
        conn.close()
    finally:
        db_importing = False


def on_click_import_csv():
    csv_path = filedialog.askopenfilename(
        title="選擇要匯入的 CSV 檔案",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
    )
    if not csv_path:
        return

    if not messagebox.askyesno("確認匯入", "確定要用這份 CSV 覆蓋目前的 reminder.db 嗎？此動作不可還原。"):
        return

    try:
        import_db_from_csv(csv_path)
    except Exception as e:
        messagebox.showerror("匯入失敗", f"CSV 匯入失敗：{e}")
        return

    tag_calendar_by_category()
    load_tasks()
    messagebox.showinfo("完成", "CSV 匯入成功，已覆蓋舊資料。")


def on_click_export_csv():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(start_time), MAX(start_time) FROM tasks")
    row = cursor.fetchone()
    conn.close()

    default_name = "forgetting_curve"
    if row and row[0] and row[1]:
        first = row[0][:10].replace("-", "")
        last = row[1][:10].replace("-", "")
        default_name = f"forgetting_curve_{first}_{last}"

    csv_path = filedialog.asksaveasfilename(
        title="匯出資料成 CSV",
        initialfile=default_name,
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
    )
    if not csv_path:
        return

    try:
        export_db_to_csv(csv_path)
    except Exception as e:
        messagebox.showerror("匯出失敗", f"CSV 匯出失敗：{e}")
        return

    messagebox.showinfo("完成", f"CSV 匯出成功：{csv_path}")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            difficulty TEXT,
            notes TEXT,
            reminder_method TEXT,
            start_time TEXT,
            is_completed INTEGER DEFAULT 0,
            progress_percent REAL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            remind_time TEXT,
            reminded INTEGER DEFAULT 0,
            FOREIGN KEY(task_id) REFERENCES tasks(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backgrounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            path TEXT,
            upload_time TEXT,
            is_active INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

# 標示任務分類顏色（日期 → {分類: [任務1, 任務2]})
def tag_calendar_by_category():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT remind_time FROM reminders WHERE reminded = 0')
    rows = cursor.fetchall()
    conn.close()

    # 統計每天的提醒數量
    date_count = {}
    for (remind_time,) in rows:
        date = remind_time.split('T')[0]
        date_count[date] = date_count.get(date, 0) + 1

    # 移除現有標籤與樣式
    calendar.calevent_remove('all')

    for date, count in date_count.items():
        if count <= 2:
            color = '#ffcccc'  # 淺紅
        elif count <= 5:
            color = '#ff6666'  # 中紅
        else:
            color = '#cc0000'  # 深紅

        tag_name = f"tag_{date}"
        event_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        calendar.calevent_create(event_date, f"{count} 筆任務", tag_name)
        calendar.tag_config(tag_name, background=color, foreground='white')

def open_reminder_popup(task_id, mode_from_main="手動輸入"):
    
    popup = tk.Toplevel()
    popup.title("編輯提醒時間")
    popup.geometry("450x550")

    mode_var = tk.StringVar(value= mode_from_main)
    repeat_count_var = tk.StringVar(value="5")

    reminder_widgets = []
    preview_label = tk.Label(popup, text="", font=('Arial', 10), fg="gray")
    preview_label.grid(row=102, column=0, columnspan=4, pady=(10, 0))

    def get_curve_days(n):
        mapping = {
            3: [1, 3, 7],
            4: [1, 3, 7, 14],
            5: [1, 3, 7, 14, 30],
            6: [1, 3, 7, 14, 30, 60],
            7: [1, 3, 7, 14, 30, 60, 90],
            8: [1, 3, 7, 14, 30, 60, 90, 120],
            9: [1, 3, 7, 14, 30, 60, 90, 120, 180],
            10: [1, 3, 7, 14, 30, 60, 90, 120, 180, 365]
        }
        return mapping.get(n, [])

    def update_preview():
        previews = []
        if mode_var.get() == "手動輸入":
            for date_entry, hour_cb, min_cb in reminder_widgets:
                try:
                    date = date_entry.get_date()
                    hour = int(hour_cb.get())
                    minute = int(min_cb.get())
                    dt = datetime.datetime.combine(date, datetime.time(hour, minute))
                    previews.append(dt)
                except:
                    continue
        else:
            try:
                base_date = date_entry_curve.get_date()
                hour = int(hour_cb_curve.get())
                minute = int(min_cb_curve.get())
                base_dt = datetime.datetime.combine(base_date, datetime.time(hour, minute))
                days = get_curve_days(int(repeat_count_var.get()))
                previews = [base_dt + datetime.timedelta(days=d) for d in days]
            except:
                pass

        previews = sorted(set(previews))
        if previews:
            preview_label.config(text="🔔 將提醒於：\n" + "\n".join("✔️ " + d.strftime("%Y-%m-%d %H:%M") for d in previews))
        else:
            preview_label.config(text="（尚未設定提醒）")

    # 新增提醒欄位
    def add_reminder_row():
        row = len(reminder_widgets) + 2
        date_entry = DateEntry(popup, width=12, font=('Arial', 11), date_pattern='yyyy-mm-dd')
        hour_cb = ttk.Combobox(popup, values=[f"{h:02}" for h in range(0, 24)], width=3, font=('Arial', 11))
        hour_cb.set("09")
        min_cb = ttk.Combobox(popup, values=["00", "12 ","15", "30", "45"], width=3, font=('Arial', 11))
        min_cb.set("00")

        date_entry.grid(row=row, column=0, padx=5, pady=5)
        hour_cb.grid(row=row, column=1, padx=5, pady=5)
        min_cb.grid(row=row, column=2, padx=5, pady=5)

        reminder_widgets.append((date_entry, hour_cb, min_cb))
        update_preview()

        hour_cb.bind("<<ComboboxSelected>>", lambda e: update_preview())
        min_cb.bind("<<ComboboxSelected>>", lambda e: update_preview())

    # 刪除最後一個提醒欄位
    def remove_last_row():
        if reminder_widgets:
            widgets = reminder_widgets.pop()
            for w in widgets:
                w.destroy()
            update_preview()


    def save_reminders():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        times = []

        if mode_var.get() == "手動輸入":
            # 手動輸入的處理邏輯
            for date_entry, hour_cb, min_cb in reminder_widgets:
                try:
                    date = date_entry.get_date()
                    hour = int(hour_cb.get())
                    minute = int(min_cb.get())
                    dt = datetime.datetime.combine(date, datetime.time(hour, minute))
                    times.append(dt)
                except:
                    continue
        else:
            # 遺忘曲線模式
            base_date = date_entry_curve.get_date()
            hour = int(hour_cb_curve.get())
            minute = int(min_cb_curve.get())
            base_dt = datetime.datetime.combine(base_date, datetime.time(hour, minute))
            days = get_curve_days(int(repeat_count_var.get()))  # 自動生成的複習天數
            times = [base_dt + datetime.timedelta(days=d) for d in days]

        times = sorted(set(times))

        # 若是更新現有任務的提醒，先清空舊的 reminders
        cursor.execute("DELETE FROM reminders WHERE task_id = ?", (task_id,))

        for remind_dt in times:
            if remind_dt > datetime.datetime.now():
                cursor.execute("INSERT INTO reminders (task_id, remind_time) VALUES (?, ?)", (task_id, remind_dt.isoformat()))
        conn.commit()
        conn.close()
        popup.destroy()
        tag_calendar_by_category()
        load_tasks()
        messagebox.showinfo("完成", "提醒時間已設定！")

    # 預先建立控制按鈕，但不立即 grid，等待 render_mode 處理
    button_new = tk.Button(popup, text="＋新增提醒", command=add_reminder_row, font=('Arial', 10))
    button_remove = tk.Button(popup, text="－刪除提醒", command=remove_last_row, font=('Arial', 10))


    # 遺忘曲線設定欄位
    date_entry_curve = DateEntry(popup, width=12, font=('Arial', 11), date_pattern='yyyy-mm-dd')
    hour_cb_curve = ttk.Combobox(popup, values=[f"{h:02}" for h in range(0, 24)], width=3, font=('Arial', 11))
    hour_cb_curve.set("18")
    min_cb_curve = ttk.Combobox(popup, values=["00", "15", "30", "45"], width=3, font=('Arial', 11))
    min_cb_curve.set("00")
    tk.Label(popup, text="複習次數", font=('Arial', 11)).grid(row=1, column=0, sticky='e')
    count_menu = ttk.OptionMenu(popup, repeat_count_var, "5", *[str(i) for i in range(3, 11)], command=lambda e: update_preview())
    count_menu.grid(row=1, column=1, sticky='w')

    def render_mode():
        # 清除手動提醒欄位
        for widgets in reminder_widgets:
            for w in widgets:
                w.destroy()
        reminder_widgets.clear()

        # 移除舊有控制按鈕（避免殘留）
        for widget in popup.grid_slaves():
            if int(widget.grid_info()["row"]) in (3, 4, 5):
                widget.grid_remove()

        if mode_var.get() == "手動輸入":
            # 顯示新增/刪除按鈕
            button_new.grid(row=100, column=0, pady=(20, 5), padx=5, sticky='w')
            button_remove.grid(row=100, column=1, pady=(20, 5), padx=5, sticky='w')

            # 隱藏遺忘曲線欄位
            date_entry_curve.grid_remove()
            hour_cb_curve.grid_remove()
            min_cb_curve.grid_remove()
            count_menu.grid_remove()

            # 顯示一組手動輸入提醒欄位
            add_reminder_row()
        else:
            # 日期與時間選擇
            tk.Label(popup, text="開始日期", font=('Arial', 11)).grid(row=0, column=0, padx=5, pady=(10, 2), sticky='e')
            date_entry_curve.grid(row=0, column=1, padx=5, pady=(10, 2), sticky='w')

            tk.Label(popup, text="時間", font=('Arial', 11)).grid(row=0, column=2, padx=5, pady=(10, 2), sticky='e')
            hour_cb_curve.grid(row=0, column=3, pady=(10, 2), sticky='w')
            tk.Label(popup, text=":").grid(row=0, column=4, pady=(10, 2))
            min_cb_curve.grid(row=0, column=5, pady=(10, 2), sticky='w')

            # 複習次數與說明
            tk.Label(popup, text="複習次數", font=('Arial', 11)).grid(row=1, column=0, sticky='e', padx=5, pady=(5, 2))
            count_menu.grid(row=1, column=1, sticky='w', padx=5)
            tk.Label(popup, text="（系統將自動安排提醒時間）", font=('Arial', 9), fg="gray").grid(row=1, column=2, columnspan=4, sticky='w', pady=(5, 2))

            update_preview()



    render_mode()

    # 控制按鈕
    tk.Button(popup, text="💾 儲存提醒", command=save_reminders, font=('Arial', 11)).grid(row=101, column=0, columnspan=3, pady=10)

def clear_new_form():
    new_title_entry.delete(0, tk.END)
    new_category_var.set(DEFAULT_CATEGORIES[0])
    new_difficulty_var.set(DEFAULT_DIFFICULTIES[0])
    new_notes_text.delete("1.0", tk.END)
    new_reminder_mode_var.set("遺忘曲線")


def clear_edit_form():
    # v3：修改行程面板已移除，不再使用
    return


def add_task_and_set_reminders():
    title = new_title_entry.get().strip()
    category = new_category_var.get().strip()
    difficulty = new_difficulty_var.get()
    notes = new_notes_text.get("1.0", tk.END).strip()
    reminder_method = new_reminder_mode_var.get()

    if not title:
        messagebox.showwarning("提示", "請輸入任務名稱")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    start_time = datetime.datetime.now()
    cursor.execute(
        """
        INSERT INTO tasks (title, category, difficulty, notes, reminder_method, start_time, is_completed)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (title, category, difficulty, notes, reminder_method, start_time.isoformat()),
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()

    load_tasks()
    tag_calendar_by_category()
    clear_new_form()

    open_reminder_popup(task_id, reminder_method)


def update_selected_task_info():
    # v3：修改行程面板已移除，請改用任務列雙擊彈窗修改
    messagebox.showinfo("功能已移除", "v3 請在左上任務清單雙擊任務列來修改。")
    load_tasks()

def delete_tasks():
    selected_items = task_tree.selection()
    if not selected_items:
        messagebox.showwarning("提示", "請先選擇要刪除的任務")
        return

    if not messagebox.askyesno("確認刪除", "你確定要刪除這些已完成任務嗎？此操作無法還原。"):
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for item in selected_items:
        task_id = task_tree.item(item)['values'][0]
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        cursor.execute("DELETE FROM reminders WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()

    load_tasks()
    tag_calendar_by_category()
    messagebox.showinfo("完成", "已成功刪除所選任務")



def complete_task_immediately():
    task_id = selected_task_id.get()
    if task_id == -1:
        messagebox.showwarning("提示", "請先選擇要一鍵完成的任務")
        return

    if not messagebox.askyesno("確認", "你確定要直接完成此任務嗎？未完成的提醒將不再出現。"):
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 將所有 reminder 標記為完成
    cursor.execute("UPDATE reminders SET reminded = 1 WHERE task_id = ?", (task_id,))
    # 將任務本身標記為完成
    cursor.execute("UPDATE tasks SET is_completed = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    tag_calendar_by_category()
    load_tasks()
    messagebox.showinfo("完成", "此任務已被直接完成並從提醒中移除。")


def refresh_filter_menu():
    """
    依照目前 tasks 裡出現過的 category 動態更新左側篩選選單。
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM tasks")
        cats = sorted({(r[0] or "").strip() for r in cursor.fetchall() if (r[0] or "").strip()})
        conn.close()
    except Exception:
        return

    options = ["全部"] + cats + ["已完成任務"]

    # 修正目前選擇的 filter 值（避免載入後值不在選單）
    if filter_var.get() not in options:
        filter_var.set("全部")

    # 重建 OptionMenu 的 menu 內容
    try:
        menu = filter_menu["menu"]
        menu.delete(0, "end")
        for opt in options:
            menu.add_command(
                label=opt,
                command=lambda v=opt: (filter_var.set(v), load_tasks()),
            )
    except Exception:
        pass

    # 讓新增/修改的分類下拉也能看到既有分類（仍允許使用者自行輸入）
    try:
        new_category_combo.configure(values=cats if cats else DEFAULT_CATEGORIES)
    except Exception:
        pass


def load_tasks():
    refresh_filter_menu()
    task_tree.delete()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    selected_filter = filter_var.get()
    if selected_filter == "全部":
        cursor.execute("SELECT id, title, category, start_time FROM tasks WHERE is_completed = 0")
    elif selected_filter == "已完成任務":
        cursor.execute("SELECT id, title, category, start_time FROM tasks WHERE is_completed = 1")
    else:
        cursor.execute("SELECT id, title, category, start_time FROM tasks WHERE category = ? AND is_completed = 0", (selected_filter,))
    
    tasks = cursor.fetchall()

    for task in tasks:
        task_id, title, category, start_time = task
        # 查詢進度
        cursor.execute("SELECT COUNT(*) FROM reminders WHERE task_id = ?", (task_id,))
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM reminders WHERE task_id = ? AND reminded = 1", (task_id,))
        done = cursor.fetchone()[0]
        # 計算完成百分比
        percent = round((done / total) * 100, 1) if total > 0 else 0.0
        # 儲存到 tasks 表格中
        cursor.execute("UPDATE tasks SET progress_percent = ? WHERE id = ?", (percent, task_id))
        if total > 0:
            # 依照 reminders 總數做「比例長條」，避免固定 10 格造成使用者誤解。
            segments = min(total, 20)
            filled = int((done / total) * segments)
            bar = '🟩' * filled + '⬜' * (segments - filled)
            progress = f"{bar} {done}/{total} ({percent:.0f}%)"
        else:
            progress = "-"
        formatted = datetime.datetime.fromisoformat(start_time).strftime("%Y-%m-%d\n%H:%M")
        task_tree.insert('', 'end', values=(task_id, title, category, formatted, progress))
    
    conn.close()



def on_task_select(event):
    selected = task_tree.selection()
    if not selected:
        return
    item = task_tree.item(selected[0])
    task_id = item['values'][0]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id=?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        selected_task_id.set(row[0])
        # v3：不再顯示「修改行程」面板；改用 task_tree 雙擊彈窗修改


def get_categories_for_combo():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM tasks")
        cats = sorted({(r[0] or "").strip() for r in cursor.fetchall() if (r[0] or "").strip()})
        conn.close()
    except Exception:
        cats = []
    base = cats if cats else list(DEFAULT_CATEGORIES)
    # 去重但保持穩定順序
    seen = set()
    result = []
    for c in base + list(DEFAULT_CATEGORIES):
        if c and c not in seen:
            seen.add(c)
            result.append(c)
    return result


def open_task_edit_popup(task_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title, category, difficulty, notes, reminder_method FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        messagebox.showwarning("提示", "找不到該任務")
        return

    title_val, category_val, difficulty_val, notes_val, method_val = row

    popup = tk.Toplevel()
    popup.title("修改任務資訊")
    popup.geometry("420x360")
    popup.attributes("-topmost", True)

    tk.Label(popup, text="任務名稱", font=("Arial", 12)).grid(row=0, column=0, sticky="e", padx=10, pady=(12, 4))
    title_entry = tk.Entry(popup, width=28, font=("Arial", 12))
    title_entry.grid(row=0, column=1, sticky="w", padx=5, pady=(12, 4))
    title_entry.insert(0, title_val or "")

    tk.Label(popup, text="分類", font=("Arial", 12)).grid(row=1, column=0, sticky="e", padx=10, pady=4)
    category_combo = ttk.Combobox(
        popup,
        values=get_categories_for_combo(),
        state="normal",
        width=26,
    )
    category_combo.grid(row=1, column=1, sticky="w", padx=5, pady=4)
    category_combo.set(category_val or (DEFAULT_CATEGORIES[0] if DEFAULT_CATEGORIES else ""))

    tk.Label(popup, text="難度", font=("Arial", 12)).grid(row=2, column=0, sticky="e", padx=10, pady=4)
    difficulty_var = tk.StringVar(value=difficulty_val or DEFAULT_DIFFICULTIES[0])
    ttk.OptionMenu(popup, difficulty_var, difficulty_var.get(), *DEFAULT_DIFFICULTIES).grid(
        row=2, column=1, sticky="w", padx=5, pady=4
    )

    tk.Label(popup, text="備註", font=("Arial", 12)).grid(row=3, column=0, sticky="ne", padx=10, pady=4)
    notes_text = tk.Text(popup, height=5, width=24, font=("Arial", 12))
    notes_text.grid(row=3, column=1, sticky="w", padx=5, pady=4)
    notes_text.insert("1.0", notes_val or "")

    def save():
        new_title = title_entry.get().strip()
        new_category = category_combo.get().strip()
        new_difficulty = difficulty_var.get()
        new_notes = notes_text.get("1.0", tk.END).strip()

        if not new_title:
            messagebox.showwarning("提示", "請輸入任務名稱")
            return

        conn2 = sqlite3.connect(DB_PATH)
        cursor2 = conn2.cursor()
        cursor2.execute(
            "UPDATE tasks SET title=?, category=?, difficulty=?, notes=? WHERE id=?",
            (new_title, new_category, new_difficulty, new_notes, task_id),
        )
        conn2.commit()
        conn2.close()

        tag_calendar_by_category()
        load_tasks()
        popup.destroy()

    # 修改儲存鍵貼齊中間（加寬並置中）
    tk.Button(popup, text="儲存修改", command=save, font=("Arial", 11), height=2, width=15).grid(
        row=4, column=0, columnspan=2, pady=(16, 4)
    )

    def reset_reminders():
        popup.destroy()
        open_reminder_popup(task_id, method_val or "遺忘曲線")

    tk.Button(popup, text="重設提醒時間", command=reset_reminders, font=("Arial", 11), height=2, width=15).grid(
        row=5, column=0, columnspan=2, pady=(4, 10)
    )


def on_task_double_click(event):
    # 由滑鼠位置找出對應列，再取出 task_id
    row_id = task_tree.identify_row(event.y)
    if row_id is None:
        return
    values = task_tree.item(row_id).get("values", [])
    if not values:
        return
    try:
        task_id = int(values[0])
    except Exception:
        return
    open_task_edit_popup(task_id)


def reminder_checker():
    if db_importing:
        root.after(1000, reminder_checker)
        return

    global notifications_paused
    if notifications_paused:
        root.after(30000, reminder_checker)
        return

    try:
        now = datetime.datetime.now().isoformat()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.id, t.title, r.remind_time FROM reminders r
            JOIN tasks t ON r.task_id = t.id
            WHERE r.reminded = 0 AND r.remind_time <= ?
        ''', (now,))
        rows = cursor.fetchall()
        conn.close()
    except Exception:
        # DB 可能被 CSV 匯入覆蓋中，先延後執行避免錯誤
        root.after(3000, reminder_checker)
        return

    for reminder_id, title, _remind_time in rows:
        show_reminder(title, reminder_id)

    root.after(30000, reminder_checker)


active_popups = set()

def show_reminder(title, reminder_id):
    if reminder_id in active_popups:
        return
    active_popups.add(reminder_id)

    def on_close():
        active_popups.discard(reminder_id)
        popup.destroy()

    def mark_as_done():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 先標記此提醒為完成
        cursor.execute("UPDATE reminders SET reminded = 1 WHERE id = ?", (reminder_id,))

        # 找出這個提醒屬於哪個任務
        cursor.execute("SELECT task_id FROM reminders WHERE id = ?", (reminder_id,))
        result = cursor.fetchone()
        if result:
            task_id = result[0]

            # 判斷是否該任務的所有提醒都完成了
            cursor.execute("SELECT COUNT(*) FROM reminders WHERE task_id = ? AND reminded = 0", (task_id,))
            remaining = cursor.fetchone()[0]

            if remaining == 0:
                cursor.execute("UPDATE tasks SET is_completed = 1 WHERE id = ?", (task_id,))

        conn.commit()
        conn.close()
        tag_calendar_by_category()
        load_tasks()
        on_close()

    def acknowledge():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        new_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
        cursor.execute("UPDATE reminders SET remind_time = ? WHERE id = ?", (new_time, reminder_id))
        conn.commit()
        conn.close()
        tag_calendar_by_category()
        load_tasks()
        on_close()

    # 額外查詢備註
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.notes FROM reminders r
        JOIN tasks t ON r.task_id = t.id
        WHERE r.id = ?
    ''', (reminder_id,))
    result = cursor.fetchone()
    conn.close()
    notes = result[0] if result else ""

    # 建立視窗
    popup = tk.Toplevel()
    popup.title("🔔 提醒")
    popup.geometry("380x200+300+300")
    popup.attributes("-topmost", True)
    popup.protocol("WM_DELETE_WINDOW", on_close)
    
    tk.Label(popup, text=f"📌 現在是時候複習：{title}", font=("Arial", 12)).pack(pady=10)

    if notes:
        tk.Label(popup, text=f"備註：{notes}", font=("Arial", 10), wraplength=330, justify="left", fg="gray").pack(pady=5)

    btn_frame = tk.Frame(popup)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="我已複習", font=('Arial', 11), command=mark_as_done, bg="#4CAF50", fg="white", width=10).pack(side="left", padx=10)
    tk.Button(btn_frame, text="1小時後提醒", font=('Arial', 11), command=acknowledge, bg="#f0ad4e", fg="white", width=12).pack(side="right", padx=10)


def on_calendar_select(event):
    global popup
    try:
        if popup.winfo_exists():
            popup.destroy()
    except:
        pass
    selected_date = calendar.get_date()
    date_start = datetime.datetime.strptime(selected_date, "%Y-%m-%d")
    date_end = date_start + datetime.timedelta(days=1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.id, t.id, t.title, r.remind_time, t.category FROM reminders r
        JOIN tasks t ON r.task_id = t.id
        WHERE r.remind_time BETWEEN ? AND ? AND r.reminded = 0
        ORDER BY r.remind_time ASC
    ''', (date_start.isoformat(), date_end.isoformat()))
    rows = cursor.fetchall()
    conn.close()

    def mark_complete(reminder_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # 找出 reminder 所屬任務
        cursor.execute("SELECT task_id FROM reminders WHERE id = ?", (reminder_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return
        task_id = result[0]

        # 將該提醒標記為完成
        cursor.execute("UPDATE reminders SET reminded = 1 WHERE id = ?", (reminder_id,))

        # 檢查這個任務的其他提醒是否也都完成
        cursor.execute("SELECT COUNT(*) FROM reminders WHERE task_id = ? AND reminded = 0", (task_id,))
        remaining = cursor.fetchone()[0]

        if remaining == 0:
            cursor.execute("UPDATE tasks SET is_completed = 1 WHERE id = ?", (task_id,))

        conn.commit()
        conn.close()
        tag_calendar_by_category()
        load_tasks()
        try:
            popup.destroy()
        except:
            pass
        print("提醒已標記為完成")
        
    def postpone_reminders(task_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT remind_time FROM reminders WHERE task_id = ? AND reminded = 0', (task_id,))
        upcoming = cursor.fetchall()
        cursor.execute('DELETE FROM reminders WHERE task_id = ? AND reminded = 0', (task_id,))
        for (remind_time,) in upcoming:
            new_time = datetime.datetime.fromisoformat(remind_time) + datetime.timedelta(days=1)
            cursor.execute('INSERT INTO reminders (task_id, remind_time) VALUES (?, ?)', (task_id, new_time.isoformat()))
        conn.commit()
        conn.close()
        tag_calendar_by_category()
        popup.destroy()
        print("提醒已推延")
            
            
    popup = tk.Toplevel()
    popup.title(f"{selected_date} 的提醒")
    popup.geometry("520x420")
    tk.Label(popup, text=f"{selected_date} 的提醒任務", font=("Arial", 14)).pack(pady=10)

    if not rows:
        tk.Label(popup, text="🎉 今天沒有提醒任務", font=("Arial", 12)).pack(pady=20)
        return

    for reminder_id, task_id, title, remind_time, category in rows:
        frame = tk.Frame(popup)
        frame.pack(fill="x", padx=10, pady=4)

        color = get_category_color(category)
        tk.Label(frame, text="●", fg=color, font=("Arial", 12)).pack(side="left", padx=(0, 4))
        tk.Label(frame, text=f"{remind_time[11:16]} - {title}", anchor="w", width=30).pack(side="left")
        tk.Button(frame, text="完成", command=lambda rid=reminder_id: mark_complete(rid)).pack(side="right", padx=2)
        tk.Button(frame, text="推延", command=lambda tid=task_id: postpone_reminders(tid)).pack(side="right")



# --- 背景個人化功能開始 ---
def ensure_bg_dir():
    if not os.path.exists(BG_DIR):
        os.makedirs(BG_DIR)


bg_overlay_win = None
bg_overlay_label = None

def get_bg_opacity():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='bg_opacity'")
    row = cursor.fetchone()
    conn.close()
    if row:
        return float(row[0])
    return 0.3

def sync_bg_overlay(event=None):
    if bg_overlay_win and bg_overlay_win.winfo_exists() and root.winfo_exists():
        if root.state() == 'iconic':
            if bg_overlay_win.state() != 'withdrawn':
                bg_overlay_win.withdraw()
            return
        if bg_overlay_win.state() == 'withdrawn':
            bg_overlay_win.deiconify()
        
        w = root.winfo_width()
        h = root.winfo_height()
        x = root.winfo_rootx()
        y = root.winfo_rooty()
        bg_overlay_win.geometry(f"{w}x{h}+{x}+{y}")
        bg_overlay_win.lift()


def load_background(is_startup=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='random_startup_bg'")
    rand_setting = cursor.fetchone()
    is_random = (rand_setting and rand_setting[0] == '1')
    
    bg_record = None
    if is_random and is_startup:
        cursor.execute("SELECT id, path FROM backgrounds ORDER BY RANDOM() LIMIT 1")
        bg_record = cursor.fetchone()
        if bg_record:
            cursor.execute("UPDATE backgrounds SET is_active = 0")
            cursor.execute("UPDATE backgrounds SET is_active = 1 WHERE id = ?", (bg_record[0],))
            conn.commit()
    
    if not bg_record:
        cursor.execute("SELECT id, path FROM backgrounds WHERE is_active = 1")
        bg_record = cursor.fetchone()
    conn.close()
    
    if bg_record and os.path.exists(bg_record[1]):
        try:
            from PIL import Image
            pil_img = Image.open(bg_record[1])
            task_tree.set_background(pil_img)
        except Exception as e:
            print("載入背景失敗:", e)
    else:
        task_tree.set_background(None)

def open_personalization_popup():
    ensure_bg_dir()
    pop = tk.Toplevel(root)
    pop.title("個人化背景設定")
    pop.geometry("600x550")
    pop.attributes("-topmost", True)
    
    ctrl_frame = tk.Frame(pop)
    ctrl_frame.pack(fill=tk.X, padx=10, pady=10)
    
    def on_upload():
        filepath = filedialog.askopenfilename(
            parent=pop,
            title="選擇背景圖片",
            filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.webp")]
        )
        if not filepath: return
        
        if os.path.getsize(filepath) > 20 * 1024 * 1024:
            messagebox.showerror("上傳失敗", "圖片檔案過大，請選擇小於 20MB 的圖片", parent=pop)
            return
            
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1]
        unique_name = f"bg_{int(time.time())}{ext}"
        dest_path = os.path.join(BG_DIR, unique_name)
        
        try:
            shutil.copy(filepath, dest_path)
        except Exception as e:
            messagebox.showerror("上傳失敗", f"無法複製圖片: {e}", parent=pop)
            return
            
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO backgrounds (filename, path, upload_time, is_active) VALUES (?, ?, ?, 0)",
                  (filename, dest_path, datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        refresh_list()
        messagebox.showinfo("成功", "圖片上傳成功！", parent=pop)
        
    tk.Button(ctrl_frame, text="上傳新圖片", command=on_upload, font=("Arial", 11), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)


    
    rand_var = tk.IntVar()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='random_startup_bg'")
    r = c.fetchone()
    rand_var.set(1 if (r and r[0] == '1') else 0)
    conn.close()
    
    def toggle_random():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        val = '1' if rand_var.get() == 1 else '0'
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('random_startup_bg', ?)", (val,))
        conn.commit()
        conn.close()
        
    tk.Checkbutton(ctrl_frame, text="啟動程式時隨機切換背景", variable=rand_var, command=toggle_random, font=("Arial", 11)).pack(side=tk.RIGHT, padx=5)
    
    list_frame = tk.Frame(pop)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    canvas = tk.Canvas(list_frame)
    scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )
    
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
    canvas.configure(yscrollcommand=scrollbar.set)
    
    def _on_mousewheel(event):
        try:
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass
    pop.bind("<MouseWheel>", _on_mousewheel)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    pop.thumbnails = []
    
    def set_active(bg_id):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE backgrounds SET is_active = 0")
        c.execute("UPDATE backgrounds SET is_active = 1 WHERE id = ?", (bg_id,))
        conn.commit()
        conn.close()
        load_background(is_startup=False)
        refresh_list()
        messagebox.showinfo("套用成功", "背景已成功更換！", parent=pop)
        
    def delete_bg(bg_id, bg_path, is_active):
        if messagebox.askyesno("確認刪除", "確定要刪除這張背景圖片嗎？", parent=pop):
            try:
                if os.path.exists(bg_path):
                    os.remove(bg_path)
            except Exception as e:
                print("刪除檔案失敗:", e)
                
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM backgrounds WHERE id = ?", (bg_id,))
            if is_active:
                c.execute("SELECT id FROM backgrounds LIMIT 1")
                nxt = c.fetchone()
                if nxt:
                    c.execute("UPDATE backgrounds SET is_active = 1 WHERE id = ?", (nxt[0],))
            conn.commit()
            conn.close()
            
            if is_active:
                load_background(is_startup=False)
            refresh_list()
    
    def refresh_list():
        for widget in scrollable_frame.winfo_children():
            widget.destroy()
        pop.thumbnails.clear()
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, filename, path, upload_time, is_active FROM backgrounds ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        
        for idx, row in enumerate(rows):
            bg_id, fname, path, utime, is_active = row
            item_frame = tk.Frame(scrollable_frame, bd=1, relief="solid", padx=5, pady=5, bg="#e0f7fa" if is_active else "white")
            item_frame.pack(fill=tk.X, pady=4, padx=4)
            
            img_lbl = tk.Label(item_frame, bg="gray")
            try:
                from PIL import Image, ImageTk
                img = Image.open(path)
                img.thumbnail((120, 80))
                photo = ImageTk.PhotoImage(img)
                pop.thumbnails.append(photo)
                img_lbl.config(image=photo)
            except:
                img_lbl.config(text="[圖片損毀]", width=15, height=4, fg="white")
            img_lbl.pack(side=tk.LEFT, padx=5)
                
            info_frame = tk.Frame(item_frame, bg=item_frame["bg"])
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
            
            t_lbl = tk.Label(info_frame, text=fname, font=("Arial", 11, "bold"), bg=item_frame["bg"])
            t_lbl.pack(anchor="w")
            d_lbl = tk.Label(info_frame, text=f"上傳: {utime[:16].replace('T', ' ')}", font=("Arial", 9), fg="gray", bg=item_frame["bg"])
            d_lbl.pack(anchor="w")
            if is_active:
                a_lbl = tk.Label(info_frame, text="✅ 目前使用中", font=("Arial", 10), fg="green", bg=item_frame["bg"])
                a_lbl.pack(anchor="w", pady=2)
                
            btn_frame = tk.Frame(item_frame, bg=item_frame["bg"])
            btn_frame.pack(side=tk.RIGHT, padx=5)
            
            if not is_active:
                tk.Button(btn_frame, text="設為背景", command=lambda i=bg_id: set_active(i)).pack(pady=2, fill=tk.X)
            tk.Button(btn_frame, text="刪除", command=lambda i=bg_id, p=path, a=is_active: delete_bg(i, p, a), fg="red").pack(pady=2, fill=tk.X)

            # 讓整個方塊都可以點擊選取
            if not is_active:
                for w in [item_frame, img_lbl, info_frame, t_lbl, d_lbl]:
                    w.bind("<Button-1>", lambda e, i=bg_id: set_active(i))
                    w.config(cursor="hand2")

    refresh_list()
# --- 背景個人化功能結束 ---

# GUI 啟動
def resource_path(relative_path):
    import sys
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

root = tk.Tk()
root.title("遺忘曲線提醒工具")
try:
    root.iconbitmap(resource_path("IMG_2832-001.ico"))
except Exception:
    pass
screen_width = root.winfo_screenwidth()
root.geometry(f"{min(1200, max(900, screen_width - 80))}x650")
root.minsize(950, 560)



selected_task_id = tk.IntVar(value=-1)
paned = ttk.Panedwindow(root, orient="horizontal")
# 增加 padding 讓背景圖片像畫框一樣露出來，否則會被完全遮擋
paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

left_frame = tk.Frame(paned)
right_frame = tk.Frame(paned)

paned.add(left_frame, weight=1)
paned.add(right_frame, weight=2)

filter_var = tk.StringVar(value="全部")
filter_options = ["全部", "已完成任務"]
filter_menu = ttk.OptionMenu(left_frame, filter_var, filter_options[0], *filter_options, command=lambda _: load_tasks())
filter_menu.pack(pady=5)
task_tree = TransparentTaskTree(left_frame, columns=('ID', 'Title', 'Category', 'Start Time', 'Progress'), show='headings', selectmode='extended')
task_tree.heading('ID', text='ID')
task_tree.heading('Title', text='任務名稱')
task_tree.heading('Category', text='分類')
task_tree.heading('Start Time', text='開始時間')
task_tree.heading('Progress', text='進度')
task_tree.pack(fill=tk.BOTH, expand=True)
task_tree.bind('<<TreeviewSelect>>', on_task_select)
task_tree.bind('<Double-1>', on_task_double_click)

form_frame = tk.Frame(left_frame)
form_frame.pack(fill=tk.X, pady=10)

forms_panel = tk.Frame(form_frame)
forms_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

buttons_panel = tk.Frame(form_frame)
buttons_panel.pack(side=tk.RIGHT, fill=tk.Y)

new_task_frame = tk.LabelFrame(forms_panel, text=" ✨ 新增專屬任務 ", font=('微軟正黑體', 11, 'bold'), padx=20, pady=10)
new_task_frame.pack(fill=tk.X, pady=10, padx=10)

edit_task_frame = tk.LabelFrame(forms_panel, text="修改行程", padx=10, pady=5)
edit_task_frame.destroy()

# ---------- 新行程欄位 ----------
lbl_style = {"font": ('微軟正黑體', 12, 'bold'), "fg": "#444"}
tk.Label(new_task_frame, text="任務名稱", **lbl_style).grid(row=0, column=0, sticky='e', pady=6)
new_title_entry = tk.Entry(new_task_frame, width=28, font=('微軟正黑體', 12), relief="solid", bd=1)
new_title_entry.grid(row=0, column=1, padx=8, pady=6, sticky='w')

tk.Label(new_task_frame, text="分類", **lbl_style).grid(row=1, column=0, sticky='e', pady=6)
new_category_var = tk.StringVar(value=DEFAULT_CATEGORIES[0])
new_category_combo = ttk.Combobox(new_task_frame, textvariable=new_category_var, values=DEFAULT_CATEGORIES, state="normal", width=26, font=('微軟正黑體', 12))
new_category_combo.grid(row=1, column=1, padx=8, pady=6, sticky='w')

tk.Label(new_task_frame, text="難度", **lbl_style).grid(row=2, column=0, sticky='e', pady=6)
new_difficulty_var = tk.StringVar(value=DEFAULT_DIFFICULTIES[0])
ttk.OptionMenu(new_task_frame, new_difficulty_var, DEFAULT_DIFFICULTIES[0], *DEFAULT_DIFFICULTIES).grid(row=2, column=1, padx=8, pady=6, sticky='w')

tk.Label(new_task_frame, text="備註", **lbl_style).grid(row=3, column=0, sticky='ne', pady=6)
new_notes_text = tk.Text(new_task_frame, height=3, width=28, font=("微軟正黑體", 12), relief="solid", bd=1)
new_notes_text.grid(row=3, column=1, padx=8, pady=6, sticky='w')

tk.Label(new_task_frame, text="提醒模式", **lbl_style).grid(row=4, column=0, sticky='e', pady=6)
new_reminder_mode_var = tk.StringVar(value="遺忘曲線")
reminder_mode_options = ["手動輸入", "遺忘曲線"]
ttk.OptionMenu(new_task_frame, new_reminder_mode_var, reminder_mode_options[1], *reminder_mode_options).grid(row=4, column=1, padx=8, pady=6, sticky='w')

btn_primary = {"font": ('微軟正黑體', 12, 'bold'), "height": 2, "bg": "#0078D7", "fg": "white", "activebackground": "#005a9e", "activeforeground": "white", "relief": "flat", "cursor": "hand2"}
tk.Button(new_task_frame, text="＋ 新增任務並設定提醒", command=add_task_and_set_reminders, **btn_primary).grid(row=5, column=0, columnspan=2, pady=(15, 5), sticky='we')

# ---------- 右側按鈕 ----------
pad_y = 12
btn_style = {"font": ("微軟正黑體", 11, "bold"), "height": 2, "width": 18, "bg": "#f8f9fa", "fg": "#333", "relief": "groove", "bd": 2, "activebackground": "#e2e6ea", "cursor": "hand2"}

tk.Button(buttons_panel, text="✅ 一鍵完成任務", command=complete_task_immediately, **{"font": ("微軟正黑體", 11, "bold"), "height": 2, "width": 18, "bg": "#e6f8ef", "fg": "#0a5c36", "relief": "groove", "bd": 2, "activebackground": "#d1e7dd", "cursor": "hand2"}).pack(pady=(20, pad_y), padx=15, fill=tk.X)
tk.Button(buttons_panel, text="🗑 刪除所選任務", command=delete_tasks, **{"font": ("微軟正黑體", 11, "bold"), "height": 2, "width": 18, "bg": "#ffeeee", "fg": "#c00", "relief": "groove", "bd": 2, "activebackground": "#ffdddd", "cursor": "hand2"}).pack(pady=pad_y, padx=15, fill=tk.X)
tk.Button(buttons_panel, text="🖼 個人化背景", command=open_personalization_popup, **{"font": ("微軟正黑體", 11, "bold"), "height": 2, "width": 18, "bg": "#f0f8ff", "fg": "#0056b3", "relief": "groove", "bd": 2, "activebackground": "#e0f0ff", "cursor": "hand2"}).pack(pady=pad_y, padx=15, fill=tk.X)
tk.Button(buttons_panel, text="📥 匯入 CSV", command=on_click_import_csv, **btn_style).pack(pady=pad_y, padx=15, fill=tk.X)
tk.Button(buttons_panel, text="📤 匯出 CSV", command=on_click_export_csv, **btn_style).pack(pady=pad_y, padx=15, fill=tk.X)

def toggle_notifications():
    global notifications_paused
    notifications_paused = not notifications_paused
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('notifications_paused', ?)", ('1' if notifications_paused else '0',))
        conn.commit()
        conn.close()
    except Exception:
        pass

    if notifications_paused:
        btn_notify_toggle.config(text="🔕 恢復通知", bg="#ffeebb", fg="#886600")
        dnd_status_label.config(text="(🔕 勿擾模式中)")
        root.title("遺忘曲線提醒工具 [🔕 勿擾模式]")
    else:
        btn_notify_toggle.config(text="🔔 暫停通知", bg="#e6f0ff", fg="#0044cc")
        dnd_status_label.config(text="")
        root.title("遺忘曲線提醒工具")

btn_notify_toggle = tk.Button(buttons_panel, text="🔔 暫停通知", command=toggle_notifications, font=("微軟正黑體", 11, "bold"), height=2, width=18, bg="#e6f0ff", fg="#0044cc", relief="groove", bd=2, activebackground="#cce0ff", cursor="hand2")
btn_notify_toggle.pack(pady=pad_y, padx=15, fill=tk.X)

calendar_title_frame = tk.Frame(right_frame)
calendar_title_frame.pack(pady=(0, 10))
tk.Label(calendar_title_frame, text="📅 任務月曆", font=("微軟正黑體", 22, "bold"), fg="#333333").pack(side=tk.LEFT)
dnd_status_label = tk.Label(calendar_title_frame, text="", font=("微軟正黑體", 22, "bold"), fg="#d9534f")
dnd_status_label.pack(side=tk.LEFT, padx=(10, 0))
calendar = Calendar(
    right_frame,
    selectmode='day',
    date_pattern='yyyy-mm-dd',
    font=('微軟正黑體', 14),
    showweeknumbers=False,
    borderwidth=1,
    background='#0078D7',
    foreground='white',
    headersbackground='#f0f0f0',
    headersforeground='#333333',
    normalbackground='white',
    normalforeground='#333333',
    weekendbackground='#fff0f0',
    weekendforeground='#c00',
    othermonthforeground='#cccccc',
    othermonthbackground='white',
    othermonthweforeground='#ffcccc',
    othermonthwebackground='#fff0f0',
    selectbackground='#005a9e',
    selectforeground='white'
)
calendar.pack(pady=10, ipadx=40, ipady=30, expand=True, fill='both')



calendar.bind("<<CalendarSelected>>", on_calendar_select)


init_db()

try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='notifications_paused'")
    row = c.fetchone()
    conn.close()
    if row and row[0] == '1':
        notifications_paused = True
        btn_notify_toggle.config(text="🔕 恢復通知", bg="#ffeebb", fg="#886600")
        dnd_status_label.config(text="(🔕 勿擾模式中)")
        root.title("遺忘曲線提醒工具 [🔕 勿擾模式]")
except Exception:
    pass

load_tasks()
tag_calendar_by_category()
ensure_bg_dir()
load_background(is_startup=True)
root.after(1000, reminder_checker)
root.mainloop()
