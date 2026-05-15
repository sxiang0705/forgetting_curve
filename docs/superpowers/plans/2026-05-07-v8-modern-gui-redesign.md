# Renew Curve v8 現代化 GUI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將已核准的 v8 現代化 GUI 規格落地，包含今日任務主畫面、日期切換、任務完成/推延、新增任務雙排程模式、報表資料視窗、完整 ZIP 備份與全域個人化。

**Architecture:** 先擴充資料層與排程/備份服務，讓 UI 可以用清楚的查詢與命令操作資料；再重構 PySide6 視窗，將主畫面、資料視窗、新增任務、個人化拆成較明確的元件。資料安全以 transaction、匯入前驗證、ZIP 解壓到暫存區後再替換為核心原則。

**Tech Stack:** Python 3、PySide6、SQLite、pytest、標準函式庫 `zipfile` / `json` / `shutil` / `tempfile`。

---

## File Structure

- Modify: `src/renew_curve/db.py`
  - 新增日期查詢、分類查詢、統計查詢、整批推延與素材資料表。
- Modify: `src/renew_curve/models.py`
  - 新增 UI 查詢用 dataclass，例如 `ReminderItem`、`DaySummary`、`ReportStats`、`PersonalizationAssets`。
- Modify: `src/renew_curve/scheduler.py`
  - 保留遺忘曲線產生邏輯，新增手動提醒時間驗證 helper。
- Create: `src/renew_curve/backup.py`
  - 管理完整 v8 ZIP 匯出 / 匯入。
- Create: `src/renew_curve/ui/personalization.py`
  - 集中個人化設定 key、預設值與 stylesheet 參數轉換。
- Modify: `src/renew_curve/ui/theme.py`
  - 支援全域主題與功能視窗低密度貼圖風格。
- Modify: `src/renew_curve/ui/dialogs.py`
  - 改造 `TaskDialog`、`ImportExportDialog`、`SettingsDialog`，並新增報表/資料與排程說明視窗需要的 UI。
- Modify: `src/renew_curve/ui/main_window.py`
  - 重建主畫面：左側月曆、接下來 3 天、今天任務、所有任務、各視窗入口。
- Add/Modify tests:
  - `tests/test_db.py`
  - `tests/test_scheduler.py`
  - `tests/test_backup.py`
  - `tests/test_settings.py`
  - `tests/test_gui_actions.py`
  - `tests/test_gui_imports.py`

## Task 1: 資料模型與查詢 API

**Files:**
- Modify: `src/renew_curve/models.py`
- Modify: `src/renew_curve/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write failing repository tests**

Add these tests to `tests/test_db.py`:

```python
def test_repository_lists_due_reminders_for_date(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        task_id = repo.create_task(
            TaskDraft(
                title="英文單字 Unit 12",
                category="英文單字",
                difficulty="初級",
                notes="完整備註",
                reminder_method="遺忘曲線",
                start_time=dt.datetime(2026, 5, 6, 9, 0),
            )
        )
        due_id = repo.create_reminder(
            ReminderDraft(task_id=task_id, remind_time=dt.datetime(2026, 5, 7, 9, 0))
        )
        repo.create_reminder(
            ReminderDraft(task_id=task_id, remind_time=dt.datetime(2026, 5, 8, 9, 0))
        )

        items = repo.list_due_reminders_for_date(dt.date(2026, 5, 7))

    assert [item.reminder_id for item in items] == [due_id]
    assert items[0].task_title == "英文單字 Unit 12"
    assert items[0].notes == "完整備註"
    assert items[0].review_index == 1
```

```python
def test_repository_counts_reminders_by_date_and_categories(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        english_id = repo.create_task(
            TaskDraft("單字", "英文單字", "初級", "", "遺忘曲線", dt.datetime(2026, 5, 6, 9, 0))
        )
        cs_id = repo.create_task(
            TaskDraft("儲存單位", "計算機概論", "初級", "", "遺忘曲線", dt.datetime(2026, 5, 6, 10, 0))
        )
        repo.create_reminder(ReminderDraft(english_id, dt.datetime(2026, 5, 7, 9, 0)))
        repo.create_reminder(ReminderDraft(cs_id, dt.datetime(2026, 5, 7, 10, 0)))
        repo.create_reminder(ReminderDraft(cs_id, dt.datetime(2026, 5, 9, 10, 0)))

        counts = repo.count_pending_reminders_by_date(dt.date(2026, 5, 7), 3)
        categories = repo.list_categories()

    assert counts == {
        dt.date(2026, 5, 7): 2,
        dt.date(2026, 5, 8): 0,
        dt.date(2026, 5, 9): 1,
    }
    assert categories == ["英文單字", "計算機概論"]
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_db.py::test_repository_lists_due_reminders_for_date tests/test_db.py::test_repository_counts_reminders_by_date_and_categories -q
```

Expected: FAIL because `ReminderRepository` does not have the new methods and `ReminderItem` does not exist.

- [ ] **Step 3: Add dataclasses**

Append to `src/renew_curve/models.py`:

```python
@dataclass(frozen=True)
class ReminderItem:
    reminder_id: int
    task_id: int
    task_title: str
    category: str
    difficulty: str
    notes: str
    remind_time: dt.datetime
    review_index: int
    total_reviews: int
    progress_percent: float


@dataclass(frozen=True)
class ReportStats:
    total_tasks: int
    today_reminders: int
    pending_reminders: int
    completed_reminders: int
    total_completion_percent: float
```

- [ ] **Step 4: Implement repository queries**

In `src/renew_curve/db.py`, import `ReminderItem` and add:

```python
def list_due_reminders_for_date(self, day: dt.date) -> list[ReminderItem]:
    start = dt.datetime.combine(day, dt.time.min)
    end = start + dt.timedelta(days=1)
    rows = self._conn.execute(
        """
        SELECT
            reminders.id AS reminder_id,
            reminders.task_id,
            reminders.remind_time,
            tasks.title,
            tasks.category,
            tasks.difficulty,
            tasks.notes,
            tasks.progress_percent,
            (
                SELECT COUNT(*)
                FROM reminders AS earlier
                WHERE earlier.task_id = reminders.task_id
                  AND earlier.remind_time <= reminders.remind_time
            ) AS review_index,
            (
                SELECT COUNT(*)
                FROM reminders AS all_reviews
                WHERE all_reviews.task_id = reminders.task_id
            ) AS total_reviews
        FROM reminders
        JOIN tasks ON tasks.id = reminders.task_id
        WHERE reminders.reminded = 0
          AND reminders.remind_time >= ?
          AND reminders.remind_time < ?
        ORDER BY reminders.remind_time, reminders.id
        """,
        (_dump_datetime(start), _dump_datetime(end)),
    )
    return [
        ReminderItem(
            reminder_id=int(row["reminder_id"]),
            task_id=int(row["task_id"]),
            task_title=str(row["title"]),
            category=str(row["category"]),
            difficulty=str(row["difficulty"]),
            notes=str(row["notes"]),
            remind_time=_load_datetime(str(row["remind_time"])),
            review_index=int(row["review_index"]),
            total_reviews=int(row["total_reviews"]),
            progress_percent=float(row["progress_percent"]),
        )
        for row in rows
    ]


def count_pending_reminders_by_date(
    self, start_day: dt.date, days: int
) -> dict[dt.date, int]:
    result = {start_day + dt.timedelta(days=offset): 0 for offset in range(days)}
    start = dt.datetime.combine(start_day, dt.time.min)
    end = start + dt.timedelta(days=days)
    rows = self._conn.execute(
        """
        SELECT substr(remind_time, 1, 10) AS day_key, COUNT(*) AS count
        FROM reminders
        WHERE reminded = 0 AND remind_time >= ? AND remind_time < ?
        GROUP BY day_key
        """,
        (_dump_datetime(start), _dump_datetime(end)),
    )
    for row in rows:
        result[dt.date.fromisoformat(str(row["day_key"]))] = int(row["count"])
    return result


def list_categories(self) -> list[str]:
    rows = self._conn.execute(
        """
        SELECT DISTINCT category
        FROM tasks
        WHERE trim(category) != ''
        ORDER BY category
        """
    )
    return [str(row["category"]) for row in rows]
```

- [ ] **Step 5: Run tests**

Run:

```powershell
pytest tests/test_db.py -q
```

Expected: all `test_db.py` tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/renew_curve/models.py src/renew_curve/db.py tests/test_db.py
git commit -m "feat: add reminder query APIs"
```

## Task 2: 推延與報表統計資料層

**Files:**
- Modify: `src/renew_curve/db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_db.py`:

```python
def test_repository_bulk_snoozes_future_pending_reminders(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        task_id = repo.create_task(
            TaskDraft("單字", "英文單字", "初級", "", "遺忘曲線", dt.datetime(2026, 5, 6, 9, 0))
        )
        first_id = repo.create_reminder(ReminderDraft(task_id, dt.datetime(2026, 5, 7, 9, 0)))
        second_id = repo.create_reminder(ReminderDraft(task_id, dt.datetime(2026, 5, 9, 9, 0)))
        third_id = repo.create_reminder(ReminderDraft(task_id, dt.datetime(2026, 5, 13, 9, 0)))

        changed = repo.snooze_reminder_group(first_id, dt.timedelta(days=1))
        reminders = repo.list_reminders(task_id)

    assert changed == 3
    assert [reminder.id for reminder in reminders] == [first_id, second_id, third_id]
    assert [reminder.remind_time for reminder in reminders] == [
        dt.datetime(2026, 5, 8, 9, 0),
        dt.datetime(2026, 5, 10, 9, 0),
        dt.datetime(2026, 5, 14, 9, 0),
    ]
```

```python
def test_repository_report_stats_and_weekly_completion(tmp_path):
    db_path = tmp_path / "v8.db"
    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        task_id = repo.create_task(
            TaskDraft("單字", "英文單字", "初級", "", "遺忘曲線", dt.datetime(2026, 4, 29, 9, 0))
        )
        done_id = repo.create_reminder(ReminderDraft(task_id, dt.datetime(2026, 5, 1, 9, 0)))
        repo.create_reminder(ReminderDraft(task_id, dt.datetime(2026, 5, 2, 9, 0)))
        repo.mark_reminder_done(done_id)

        stats = repo.report_stats(today=dt.date(2026, 5, 2))
        completion = repo.weekly_completion_rate(end_day=dt.date(2026, 5, 2))

    assert stats.total_tasks == 1
    assert stats.today_reminders == 1
    assert stats.pending_reminders == 1
    assert stats.completed_reminders == 1
    assert completion == (1, 2, 50.0)
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_db.py::test_repository_bulk_snoozes_future_pending_reminders tests/test_db.py::test_repository_report_stats_and_weekly_completion -q
```

Expected: FAIL because the methods are missing.

- [ ] **Step 3: Implement data methods**

Add to `ReminderRepository` in `src/renew_curve/db.py`:

```python
def snooze_reminder_group(self, reminder_id: int, delta: dt.timedelta) -> int:
    row = self._conn.execute(
        "SELECT task_id, remind_time FROM reminders WHERE id = ? AND reminded = 0",
        (reminder_id,),
    ).fetchone()
    if row is None:
        return 0
    task_id = int(row["task_id"])
    current_time = _load_datetime(str(row["remind_time"]))
    pending = self._conn.execute(
        """
        SELECT id, remind_time
        FROM reminders
        WHERE task_id = ? AND reminded = 0 AND remind_time >= ?
        ORDER BY remind_time, id
        """,
        (task_id, _dump_datetime(current_time)),
    ).fetchall()
    for item in pending:
        new_time = _load_datetime(str(item["remind_time"])) + delta
        self._conn.execute(
            "UPDATE reminders SET remind_time = ? WHERE id = ?",
            (_dump_datetime(new_time), int(item["id"])),
        )
    self.recalculate_task_progress(task_id)
    return len(pending)


def report_stats(self, today: dt.date) -> ReportStats:
    total_tasks = int(self._conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])
    start = dt.datetime.combine(today, dt.time.min)
    end = start + dt.timedelta(days=1)
    today_reminders = int(
        self._conn.execute(
            "SELECT COUNT(*) FROM reminders WHERE reminded = 0 AND remind_time >= ? AND remind_time < ?",
            (_dump_datetime(start), _dump_datetime(end)),
        ).fetchone()[0]
    )
    pending = int(self._conn.execute("SELECT COUNT(*) FROM reminders WHERE reminded = 0").fetchone()[0])
    completed = int(self._conn.execute("SELECT COUNT(*) FROM reminders WHERE reminded = 1").fetchone()[0])
    total = pending + completed
    return ReportStats(
        total_tasks=total_tasks,
        today_reminders=today_reminders,
        pending_reminders=pending,
        completed_reminders=completed,
        total_completion_percent=calculate_progress_percent(total, completed),
    )


def weekly_completion_rate(self, end_day: dt.date) -> tuple[int, int, float]:
    start_day = end_day - dt.timedelta(days=6)
    start = dt.datetime.combine(start_day, dt.time.min)
    end = dt.datetime.combine(end_day + dt.timedelta(days=1), dt.time.min)
    row = self._conn.execute(
        """
        SELECT COUNT(*) AS total, COALESCE(SUM(reminded), 0) AS completed
        FROM reminders
        WHERE remind_time >= ? AND remind_time < ?
        """,
        (_dump_datetime(start), _dump_datetime(end)),
    ).fetchone()
    completed = int(row["completed"])
    total = int(row["total"])
    return completed, total, calculate_progress_percent(total, completed)
```

- [ ] **Step 4: Run tests**

Run:

```powershell
pytest tests/test_db.py -q
```

Expected: all `test_db.py` tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/renew_curve/db.py tests/test_db.py
git commit -m "feat: add snooze and report data APIs"
```

## Task 3: 完整 ZIP 備份服務

**Files:**
- Create: `src/renew_curve/backup.py`
- Create: `tests/test_backup.py`

- [ ] **Step 1: Write failing backup tests**

Create `tests/test_backup.py`:

```python
import json
import zipfile

from renew_curve.backup import export_full_backup, import_full_backup
from renew_curve.db import ReminderRepository, connect, init_db


def test_full_backup_zip_contains_database_manifest_and_assets(tmp_path):
    db_path = tmp_path / "renew_curve_v8.sqlite"
    assets_dir = tmp_path / "assets"
    backgrounds = assets_dir / "backgrounds"
    stickers = assets_dir / "stickers"
    backgrounds.mkdir(parents=True)
    stickers.mkdir(parents=True)
    (backgrounds / "sky.png").write_bytes(b"sky")
    (stickers / "star.png").write_bytes(b"star")

    with connect(db_path) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            repo.set_setting("theme_style", "healing_pastel")

    out_zip = tmp_path / "backup.zip"
    export_full_backup(db_path, assets_dir, out_zip)

    with zipfile.ZipFile(out_zip) as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))

    assert "renew_curve_v8.sqlite" in names
    assert "manifest.json" in names
    assert "assets/backgrounds/sky.png" in names
    assert "assets/stickers/star.png" in names
    assert manifest["format"] == "renew-curve-v8-backup"
```

```python
def test_import_full_backup_validates_before_replacing_current_data(tmp_path):
    current_db = tmp_path / "current.sqlite"
    current_assets = tmp_path / "current_assets"
    current_assets.mkdir()
    with connect(current_db) as conn:
        init_db(conn)
        repo = ReminderRepository(conn)
        with conn:
            repo.set_setting("theme_style", "current")

    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "wrong"}))

    try:
        import_full_backup(bad_zip, current_db, current_assets)
    except ValueError as exc:
        assert "not a Renew Curve v8 backup" in str(exc)

    with connect(current_db) as conn:
        repo = ReminderRepository(conn)
        assert repo.get_setting("theme_style", "") == "current"
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_backup.py -q
```

Expected: FAIL because `renew_curve.backup` does not exist.

- [ ] **Step 3: Implement backup module**

Create `src/renew_curve/backup.py`:

```python
from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path


BACKUP_FORMAT = "renew-curve-v8-backup"


def export_full_backup(
    db_path: str | Path, assets_dir: str | Path, out_zip: str | Path
) -> None:
    db = Path(db_path)
    assets = Path(assets_dir)
    out = Path(out_zip)
    manifest = {"format": BACKUP_FORMAT, "version": 1}
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(db, "renew_curve_v8.sqlite")
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        if assets.exists():
            for path in assets.rglob("*"):
                if path.is_file():
                    zf.write(path, Path("assets") / path.relative_to(assets))


def import_full_backup(
    zip_path: str | Path, target_db_path: str | Path, target_assets_dir: str | Path
) -> None:
    source = Path(zip_path)
    target_db = Path(target_db_path)
    target_assets = Path(target_assets_dir)
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        with zipfile.ZipFile(source) as zf:
            zf.extractall(tmp)
        manifest_path = tmp / "manifest.json"
        db_path = tmp / "renew_curve_v8.sqlite"
        if not manifest_path.exists() or not db_path.exists():
            raise ValueError("not a Renew Curve v8 backup: missing required files")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format") != BACKUP_FORMAT:
            raise ValueError("not a Renew Curve v8 backup: invalid manifest")
        backup_current = target_db.with_suffix(target_db.suffix + ".bak")
        if target_db.exists():
            shutil.copy2(target_db, backup_current)
        target_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_path, target_db)
        extracted_assets = tmp / "assets"
        if extracted_assets.exists():
            if target_assets.exists():
                shutil.rmtree(target_assets)
            shutil.copytree(extracted_assets, target_assets)
```

- [ ] **Step 4: Run backup tests**

Run:

```powershell
pytest tests/test_backup.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```powershell
git add src/renew_curve/backup.py tests/test_backup.py
git commit -m "feat: add full zip backup support"
```

## Task 4: 排程 helper 與手動輸入支援

**Files:**
- Modify: `src/renew_curve/scheduler.py`
- Modify: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing scheduler tests**

Add to `tests/test_scheduler.py`:

```python
def test_validate_manual_review_times_requires_matching_count():
    with pytest.raises(ValueError, match="expected 3 review times"):
        validate_manual_review_times(
            [dt.datetime(2026, 5, 8, 9, 0)],
            review_count=3,
        )


def test_validate_manual_review_times_sorts_and_rejects_duplicates():
    values = validate_manual_review_times(
        [
            dt.datetime(2026, 5, 10, 9, 0),
            dt.datetime(2026, 5, 8, 9, 0),
        ],
        review_count=2,
    )
    assert values == [
        dt.datetime(2026, 5, 8, 9, 0),
        dt.datetime(2026, 5, 10, 9, 0),
    ]

    with pytest.raises(ValueError, match="duplicate review time"):
        validate_manual_review_times(
            [
                dt.datetime(2026, 5, 8, 9, 0),
                dt.datetime(2026, 5, 8, 9, 0),
            ],
            review_count=2,
        )
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_scheduler.py -q
```

Expected: FAIL because `validate_manual_review_times` is missing.

- [ ] **Step 3: Implement helper**

Add to `src/renew_curve/scheduler.py`:

```python
def validate_manual_review_times(
    values: list[dt.datetime], review_count: int
) -> list[dt.datetime]:
    if len(values) != review_count:
        raise ValueError(f"expected {review_count} review times")
    sorted_values = sorted(values)
    if len(set(sorted_values)) != len(sorted_values):
        raise ValueError("duplicate review time")
    return sorted_values
```

- [ ] **Step 4: Run tests**

Run:

```powershell
pytest tests/test_scheduler.py -q
```

Expected: all scheduler tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/renew_curve/scheduler.py tests/test_scheduler.py
git commit -m "feat: validate manual review schedules"
```

## Task 5: 個人化設定與全域主題 service

**Files:**
- Create: `src/renew_curve/ui/personalization.py`
- Modify: `src/renew_curve/ui/theme.py`
- Modify: `tests/test_settings.py`

- [ ] **Step 1: Write failing settings tests**

Add to `tests/test_settings.py`:

```python
def test_personalization_defaults_include_global_scope():
    from renew_curve.ui.personalization import default_personalization_settings

    defaults = default_personalization_settings()

    assert defaults["theme_style"] == "clean_mountain"
    assert defaults["sticker_scope"] == "main_only"
    assert defaults["functional_window_sticker_density"] == "low"


def test_personalization_stylesheet_uses_theme_style():
    from renew_curve.ui.personalization import stylesheet_for_personalization

    css = stylesheet_for_personalization(
        {
            "theme_style": "healing_pastel",
            "density": "comfortable",
            "accent": "blue",
        }
    )

    assert "#2563eb" in css
    assert "QFrame#Panel" in css
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_settings.py -q
```

Expected: FAIL because `renew_curve.ui.personalization` is missing.

- [ ] **Step 3: Implement personalization module**

Create `src/renew_curve/ui/personalization.py`:

```python
from __future__ import annotations

from renew_curve.ui.theme import build_stylesheet


def default_personalization_settings() -> dict[str, str]:
    return {
        "theme": "light",
        "accent": "blue",
        "density": "comfortable",
        "default_snooze": "10m",
        "theme_style": "clean_mountain",
        "sticker_scope": "main_only",
        "functional_window_sticker_density": "low",
        "background_overlay": "60",
        "background_blur": "0",
        "background_darken": "20",
    }


def stylesheet_for_personalization(settings: dict[str, str]) -> str:
    dark = settings.get("theme_style") == "dark_focus" or settings.get("theme") == "dark"
    compact = settings.get("density") == "compact"
    return build_stylesheet(
        accent=settings.get("accent", "blue"),
        dark=dark,
        compact=compact,
    )
```

- [ ] **Step 4: Update MainWindow to use defaults**

Modify `src/renew_curve/ui/main_window.py` imports:

```python
from renew_curve.ui.personalization import (
    default_personalization_settings,
    stylesheet_for_personalization,
)
```

Replace `_load_personalization_settings` and `_stylesheet_for_settings` with:

```python
def _load_personalization_settings(self) -> dict[str, str]:
    defaults = default_personalization_settings()
    with closing(connect(self.db_path)) as conn:
        init_db(conn)
        repository = ReminderRepository(conn)
        return {
            key: repository.get_setting(key, default)
            for key, default in defaults.items()
        }

@staticmethod
def _stylesheet_for_settings(settings: dict[str, str]) -> str:
    return stylesheet_for_personalization(settings)
```

- [ ] **Step 5: Run tests**

Run:

```powershell
pytest tests/test_settings.py tests/test_gui_imports.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/renew_curve/ui/personalization.py src/renew_curve/ui/main_window.py tests/test_settings.py
git commit -m "feat: centralize personalization settings"
```

## Task 6: 新增任務對話框雙模式與預覽

**Files:**
- Modify: `src/renew_curve/ui/dialogs.py`
- Modify: `src/renew_curve/ui/main_window.py`
- Modify: `tests/test_gui_actions.py`

- [ ] **Step 1: Write failing GUI action tests**

Add to `tests/test_gui_actions.py`:

```python
def test_task_dialog_exposes_schedule_mode_and_manual_times():
    from renew_curve.ui.dialogs import TaskDialog

    assert hasattr(TaskDialog, "set_categories")
    assert hasattr(TaskDialog, "preview_review_times")
    assert hasattr(TaskDialog, "manual_review_times")
```

```python
def test_main_window_can_create_manual_reminders():
    from renew_curve.ui.main_window import MainWindow

    assert hasattr(MainWindow, "_create_task_from_values")
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_gui_actions.py -q
```

Expected: FAIL because the new methods are missing.

- [ ] **Step 3: Extend TaskDialog interface**

Modify `TaskDialog` in `src/renew_curve/ui/dialogs.py`:

```python
def set_categories(self, categories: list[str]) -> None:
    self.category_edit.clear()
    self.category_edit.addItems(categories)
    self.category_edit.setEditable(True)

def preview_review_times(self) -> list[dt.datetime]:
    start_time = self._start_time()
    if self.mode_combo.currentText() == "遺忘曲線":
        return generated_review_times(start_time, self.review_count_spin.value())
    return self.manual_review_times()

def manual_review_times(self) -> list[dt.datetime]:
    values: list[dt.datetime] = []
    for edit in self.manual_time_edits:
        value = edit.dateTime().toPython()
        if isinstance(value, dt.datetime) and value.tzinfo is not None:
            value = value.replace(tzinfo=None)
        values.append(value)
    return validate_manual_review_times(values, self.review_count_spin.value())

def _start_time(self) -> dt.datetime:
    start_time = self.start_edit.dateTime().toPython()
    if isinstance(start_time, dt.datetime) and start_time.tzinfo is not None:
        start_time = start_time.replace(tzinfo=None)
    return start_time
```

Also change `category_edit` from `QLineEdit` to editable `QComboBox` and add `self.manual_time_edits: list[QDateTimeEdit] = []`. Import `generated_review_times` and `validate_manual_review_times`.

- [ ] **Step 4: Extract task creation in MainWindow**

Add to `MainWindow`:

```python
def _create_task_from_values(self, values: dict[str, object]) -> int:
    title = str(values["title"]).strip()
    if not title:
        raise ValueError("請輸入任務名稱。")
    start_time = values["start_time"]
    review_times = values["review_times"]
    with closing(connect(self.db_path)) as conn:
        init_db(conn)
        repository = ReminderRepository(conn)
        with conn:
            task_id = repository.create_task(
                TaskDraft(
                    title=title,
                    category=str(values["category"]),
                    difficulty=str(values["difficulty"]),
                    notes=str(values["notes"]),
                    reminder_method=str(values["reminder_method"]),
                    start_time=start_time,
                )
            )
            for remind_time in review_times:
                repository.create_reminder(
                    ReminderDraft(task_id=task_id, remind_time=remind_time)
                )
            return task_id
```

In `open_task_dialog`, load categories with `repository.list_categories()`, call `dialog.set_categories(categories)`, and pass `review_times=dialog.preview_review_times()` into `_create_task_from_values`.

- [ ] **Step 5: Run selected tests**

Run:

```powershell
pytest tests/test_gui_actions.py tests/test_scheduler.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/renew_curve/ui/dialogs.py src/renew_curve/ui/main_window.py tests/test_gui_actions.py
git commit -m "feat: support task schedule modes"
```

## Task 7: 報表 / 資料視窗與 CSV/ZIP 操作

**Files:**
- Modify: `src/renew_curve/ui/dialogs.py`
- Modify: `src/renew_curve/ui/main_window.py`
- Modify: `tests/test_gui_actions.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_gui_actions.py`:

```python
def test_data_dialog_exposes_three_primary_actions():
    from renew_curve.ui.dialogs import DataDialog

    assert hasattr(DataDialog, "import_legacy_csv_button")
    assert hasattr(DataDialog, "export_full_backup_button")
    assert hasattr(DataDialog, "import_full_backup_button")
```

```python
def test_main_window_exposes_full_backup_actions():
    from renew_curve.ui.main_window import MainWindow

    assert hasattr(MainWindow, "_export_full_backup")
    assert hasattr(MainWindow, "_import_full_backup")
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_gui_actions.py -q
```

Expected: FAIL because `DataDialog` and backup methods are missing.

- [ ] **Step 3: Replace ImportExportDialog with DataDialog**

In `src/renew_curve/ui/dialogs.py`, create:

```python
class DataDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("報表 / 資料")
        self.import_legacy_csv_button = QPushButton("1. 匯入舊版 CSV")
        self.export_full_backup_button = QPushButton("2. 匯出完整資料")
        self.import_full_backup_button = QPushButton("3. 匯入完整資料")
        self.close_button = QPushButton("關閉")
        self.close_button.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("CSV 請選擇 .csv；完整資料請使用 .zip。"))
        layout.addWidget(self.import_legacy_csv_button)
        layout.addWidget(QLabel("請選擇舊版匯出的 .csv。"))
        layout.addWidget(self.export_full_backup_button)
        layout.addWidget(QLabel("會輸出包含資料庫、背景、貼圖與設定的 .zip。"))
        layout.addWidget(self.import_full_backup_button)
        layout.addWidget(QLabel("請選擇 v8 完整資料包 .zip。"))
        layout.addWidget(self.close_button)

    def choose_csv_open(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(self, "匯入舊版 CSV", "", "CSV files (*.csv)")
        return Path(path) if path else None

    def choose_zip_open(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(self, "匯入完整資料", "", "ZIP files (*.zip)")
        return Path(path) if path else None

    def choose_zip_save(self) -> Path | None:
        path, _ = QFileDialog.getSaveFileName(self, "匯出完整資料", "", "ZIP files (*.zip)")
        return Path(path) if path else None
```

- [ ] **Step 4: Wire DataDialog in MainWindow**

In `src/renew_curve/ui/main_window.py`, replace `ImportExportDialog` import with `DataDialog`, add backup import:

```python
from renew_curve.backup import export_full_backup, import_full_backup
```

Update `open_import_export_dialog`:

```python
def open_import_export_dialog(self) -> None:
    dialog = DataDialog(self)
    dialog.import_legacy_csv_button.clicked.connect(lambda: self._import_csv(dialog, "replace"))
    dialog.export_full_backup_button.clicked.connect(lambda: self._export_full_backup(dialog))
    dialog.import_full_backup_button.clicked.connect(lambda: self._import_full_backup(dialog))
    dialog.exec()
```

Add:

```python
def _assets_dir(self) -> Path:
    return self.db_path.parent / "assets"

def _export_full_backup(self, dialog: DataDialog) -> None:
    path = dialog.choose_zip_save()
    if path is None:
        return
    export_full_backup(self.db_path, self._assets_dir(), path)
    QMessageBox.information(self, "匯出完成", f"已匯出完整資料到 {path}。")

def _import_full_backup(self, dialog: DataDialog) -> None:
    path = dialog.choose_zip_open()
    if path is None:
        return
    import_full_backup(path, self.db_path, self._assets_dir())
    self.refresh_tasks()
    QMessageBox.information(self, "匯入完成", "完整資料已還原。")
```

- [ ] **Step 5: Run tests**

Run:

```powershell
pytest tests/test_gui_actions.py tests/test_backup.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/renew_curve/ui/dialogs.py src/renew_curve/ui/main_window.py tests/test_gui_actions.py
git commit -m "feat: add data report backup dialog"
```

## Task 8: 主畫面重建

**Files:**
- Modify: `src/renew_curve/ui/main_window.py`
- Modify: `tests/test_gui_actions.py`

- [ ] **Step 1: Write failing structural tests**

Add to `tests/test_gui_actions.py`:

```python
def test_main_window_exposes_new_dashboard_refresh_methods():
    from renew_curve.ui.main_window import MainWindow

    assert hasattr(MainWindow, "refresh_dashboard")
    assert hasattr(MainWindow, "_load_day_reminders")
    assert hasattr(MainWindow, "_load_next_three_days")
    assert hasattr(MainWindow, "_load_all_tasks")
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_gui_actions.py::test_main_window_exposes_new_dashboard_refresh_methods -q
```

Expected: FAIL because dashboard methods are missing.

- [ ] **Step 3: Add dashboard method skeletons**

In `src/renew_curve/ui/main_window.py`, add:

```python
def refresh_dashboard(self, selected_day: dt.date | None = None) -> None:
    day = selected_day or dt.date.today()
    self._load_day_reminders(day)
    self._load_next_three_days(day)
    self._load_all_tasks()

def _load_day_reminders(self, day: dt.date) -> None:
    with closing(connect(self.db_path)) as conn:
        repository = ReminderRepository(conn)
        self._current_day_items = repository.list_due_reminders_for_date(day)

def _load_next_three_days(self, start_day: dt.date) -> None:
    with closing(connect(self.db_path)) as conn:
        repository = ReminderRepository(conn)
        self._next_three_day_counts = repository.count_pending_reminders_by_date(start_day, 3)

def _load_all_tasks(self) -> None:
    with closing(connect(self.db_path)) as conn:
        repository = ReminderRepository(conn)
        self._all_tasks = repository.list_tasks()
```

Keep `refresh_tasks` as a compatibility wrapper:

```python
def refresh_tasks(self) -> None:
    self.refresh_dashboard()
```

- [ ] **Step 4: Replace UI layout**

Refactor `_build_ui`, `_build_sidebar`, `_build_center`:

- Left sidebar contains logo, calendar, `回到今天`, and next three days panel.
- Center contains toolbar, today task scroll, all task table with category chips.
- Remove top stat cards and remove `完成下一次` / `稍後提醒` toolbar buttons.
- For each due reminder card, connect per-row `完成` to `repository.mark_reminder_done(reminder_id)`.
- For each due reminder card, connect `推延` to a small choice dialog using existing default `default_snooze`.

Use object names for testability:

```python
self.today_tasks_container.setObjectName("TodayTasks")
self.next_three_days_container.setObjectName("NextThreeDays")
self.all_tasks_table.setObjectName("AllTasks")
```

- [ ] **Step 5: Run import and GUI smoke tests**

Run:

```powershell
pytest tests/test_gui_actions.py tests/test_gui_imports.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/renew_curve/ui/main_window.py tests/test_gui_actions.py
git commit -m "feat: redesign main dashboard"
```

## Task 9: 個人化視窗與素材資料庫

**Files:**
- Modify: `src/renew_curve/db.py`
- Modify: `src/renew_curve/ui/dialogs.py`
- Modify: `src/renew_curve/ui/main_window.py`
- Modify: `tests/test_settings.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_settings.py`:

```python
def test_init_db_creates_stickers_table(tmp_path):
    db_path = tmp_path / "settings.db"
    with connect(db_path) as conn:
        init_db(conn)
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert "stickers" in names
```

```python
def test_settings_dialog_exposes_theme_and_asset_sections():
    from renew_curve.ui.dialogs import SettingsDialog

    assert hasattr(SettingsDialog, "values")
    assert hasattr(SettingsDialog, "set_background_assets")
    assert hasattr(SettingsDialog, "set_sticker_assets")
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest tests/test_settings.py -q
```

Expected: FAIL because stickers table and dialog methods are missing.

- [ ] **Step 3: Add stickers table**

In `init_db` after `backgrounds`:

```sql
CREATE TABLE IF NOT EXISTS stickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0
);
```

- [ ] **Step 4: Add SettingsDialog methods**

In `SettingsDialog` add method stubs and values keys:

```python
def set_background_assets(self, assets: list[tuple[int, str, str, bool]]) -> None:
    self.background_assets = assets

def set_sticker_assets(self, assets: list[tuple[int, str, str, bool]]) -> None:
    self.sticker_assets = assets
```

Update `values()` to include:

```python
"theme_style": self.theme_style_combo.currentText(),
"sticker_scope": self.sticker_scope_combo.currentText(),
"functional_window_sticker_density": self.functional_sticker_density_combo.currentText(),
"background_overlay": str(self.background_overlay_spin.value()),
"background_blur": str(self.background_blur_spin.value()),
"background_darken": str(self.background_darken_spin.value()),
```

- [ ] **Step 5: Wire MainWindow settings save**

Ensure `open_settings_dialog` persists every key returned by `SettingsDialog.values()` and calls:

```python
self.setStyleSheet(self._stylesheet_for_settings(self._load_personalization_settings()))
self.refresh_dashboard()
```

- [ ] **Step 6: Run settings tests**

Run:

```powershell
pytest tests/test_settings.py -q
```

Expected: all settings tests pass.

- [ ] **Step 7: Commit**

```powershell
git add src/renew_curve/db.py src/renew_curve/ui/dialogs.py src/renew_curve/ui/main_window.py tests/test_settings.py
git commit -m "feat: expand personalization settings"
```

## Task 10: End-to-End verification and docs update

**Files:**
- Modify: `docs/v8.md` or existing v8 release doc if present
- No production code unless verification exposes a bug

- [ ] **Step 1: Run full test suite**

Run:

```powershell
pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run compile check**

Run:

```powershell
python -m compileall src
```

Expected: compile succeeds without syntax errors.

- [ ] **Step 3: Run real CSV import smoke test**

Use the user-provided sample CSV path:

```powershell
python -m renew_curve.app --db-path .tmp-v8-smoke.sqlite
```

Manual smoke path:

- Open `報表 / 資料`.
- Click `匯入舊版 CSV`.
- Select `C:\FC-2\備份\forgetting_curve_20260224_20260505.csv`.
- Confirm import success.
- Verify task count is 42 and completed reminders are recalculated from reminders.

- [ ] **Step 4: Update Traditional Chinese docs**

Update `docs/v8.md` or the current v8 user document with:

```markdown
## v8 資料備份

- `匯入舊版 CSV`：用於舊版資料轉移，請選擇 `.csv`。
- `匯出完整資料`：輸出新版完整 `.zip`，包含 SQLite 資料庫、背景、貼圖與個人化設定。
- `匯入完整資料`：還原新版完整 `.zip`，系統會先驗證再替換目前資料。
```

- [ ] **Step 5: Commit docs and final fixes**

```powershell
git add docs
git commit -m "docs: update v8 user guide"
```

- [ ] **Step 6: Final status check**

Run:

```powershell
git status --short
```

Expected: clean output.

## Self-Review Checklist

- Spec coverage:
  - 主畫面：Task 1, 2, 8。
  - 完成與推延：Task 2, 8。
  - 新增任務：Task 4, 6。
  - 報表與資料：Task 2, 3, 7。
  - 個人化：Task 5, 9。
  - 資料承接：Task 3, 7, 10 and existing CSV tests.
  - 視窗與聲音：Task 6, 7, 8, 9; no sound APIs are introduced.
- Placeholder scan:
  - No `TODO`, `TBD`, or incomplete task descriptions.
- Type consistency:
  - `ReminderItem` and `ReportStats` are defined in Task 1 before later tasks use them.
  - `validate_manual_review_times` is defined in Task 4 before `TaskDialog` uses it in Task 6.
  - `DataDialog` is defined in Task 7 before `MainWindow` imports it.
