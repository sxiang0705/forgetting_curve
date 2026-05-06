# v8 Modern GUI Design

## Goal

Build v8 of the Forgetting Curve Reminder Tool as a modern PySide6/Qt desktop app while preserving the ability to import CSV files exported by the current Tkinter version.

The release is successful only if existing user data can move into the new version safely.

## Non-Negotiable Compatibility Requirement

v8 must import the legacy CSV format produced by the current `curve.py` exporter. That format uses `record_type` rows with at least two record kinds:

- `task`
- `reminder`

The legacy columns that must remain supported are:

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

v8 may add new fields in exported CSV files, but these legacy fields must remain present so exported data remains understandable and migratable.

## Recommended Approach

Use PySide6/Qt for the v8 GUI and split the application into testable modules before connecting the interface.

This is preferred over a Tkinter-only refresh because the user wants a larger visual upgrade and likes the left-sidebar command-center direction. It is preferred over a full unstructured rewrite because legacy CSV migration must be proven with tests before the new interface is trusted.

## Architecture

Create a new package while keeping the current `curve.py` as the legacy version during the transition.

Planned modules:

- `src/renew_curve/models.py`: dataclasses or typed model objects for tasks, reminders, settings, and import results.
- `src/renew_curve/db.py`: SQLite connection handling, schema creation, migrations, transactions, and repository-style operations.
- `src/renew_curve/csv_compat.py`: legacy CSV import, v8 CSV export, CSV validation, import preview counts, and safe replace/merge flows.
- `src/renew_curve/scheduler.py`: forgetting-curve interval generation, progress calculation, due reminder queries, completion updates, and snooze time calculation.
- `src/renew_curve/app.py`: PySide6 application entrypoint.
- `src/renew_curve/ui/`: PySide6 widgets and windows.
- `tests/`: pytest coverage for compatibility and non-GUI business logic.

The data and scheduling modules must not import PySide6. GUI code consumes those modules through clear functions/classes.

## Data Model

v8 continues to use SQLite as the local database.

Minimum tables:

- `tasks`
- `reminders`
- `settings`
- `backgrounds`

The schema may evolve, but it must preserve the current concepts:

- Task title, category, difficulty, notes, reminder method, start time, completion state, and progress.
- Reminder task relationship, reminder time, and reminded/completed state.
- Key-value settings for personalization and notification preferences.
- Background image metadata and active/random behavior.

Foreign key constraints should be enabled. Deleting a task should also remove its reminders through a controlled repository operation or foreign-key cascade.

Indexes should be added for common reminder queries:

- due reminders by `reminded` and `remind_time`
- reminders by `task_id`
- tasks by category and completion state

## Legacy CSV Import

CSV import is a core v8 feature, not an optional utility.

The import flow has two modes:

- `replace`: build a new database from the CSV and swap it into use only after validation succeeds.
- `merge`: insert CSV data into the current database while remapping legacy IDs to new task IDs.

Safety rules:

- Never delete or overwrite the current database until the CSV has been parsed, validated, written to a temporary database, and checked.
- If import fails, leave the current database unchanged.
- Recalculate progress from reminder completion after import instead of trusting `progress_percent`.
- Preserve reminder timestamps as ISO strings when valid.
- Report clear validation errors for missing required columns, invalid integer fields, invalid reminder references, and invalid datetime values.

Import validation should confirm:

- All required legacy columns exist.
- Every reminder references a known task in replace mode.
- Completion fields can be interpreted as `0` or `1`.
- Datetime fields are parseable or explicitly treated as blank where allowed.
- The resulting task and reminder counts match expectations.

## CSV Export

v8 export should write CSV files that include the legacy columns listed above.

Exported rows should use:

- `record_type=task` for tasks.
- `record_type=reminder` for reminders.

Additional v8-only columns may be appended, but legacy import must not require them.

The exported CSV should support round-trip testing:

1. Export from v8.
2. Import into a fresh v8 database.
3. Confirm task count, reminder count, completion state, and reminder timestamps match.

## GUI Design

Use the approved A+C hybrid direction.

Main window layout:

- Narrow left sidebar for primary navigation.
- Central workspace for task management and quick overview.
- Right panel for calendar and selected-day reminder actions.

Sidebar sections:

- `Tasks`
- `Calendar`
- `Import/Export`
- `Settings`

The sidebar may include a compact app mark such as `FC`, current notification status, and a do-not-disturb toggle near the bottom.

Central workspace:

- Quick stats for due today, completed today, overdue, and notification state.
- Search input.
- Category/completion filters.
- Task list with title, category, next reminder, progress, and status.
- Primary action for adding a task.

Right panel:

- Monthly calendar with visual density markers for uncompleted reminders.
- Selected date reminder list.
- Actions for selected reminders: complete, snooze, and edit task where appropriate.

Task creation/editing:

- Use a modal dialog or side drawer.
- Fields: task name, category, difficulty, notes, reminder mode, date/time, and repeat count for forgetting curve mode.
- Preview generated reminder times before saving.

Reminder popups:

- Keep `I reviewed this` behavior.
- Add snooze choices: 10 minutes, 1 hour, tomorrow.
- Prevent duplicate popups for the same reminder.
- Respect persistent do-not-disturb mode.

## Personalization

Personalization should be useful but low-risk.

Settings:

- Theme mode: light, dark, follow system.
- Accent color: fixed choices such as blue, green, purple, orange, and gray.
- Background image management.
- Background opacity.
- Random startup background.
- Default snooze duration.
- Task list density: comfortable or compact.

Background images should not reduce task readability. Prefer using images in the sidebar or low-opacity background areas rather than behind dense table text.

Personalization settings live in SQLite `settings`. Importing legacy task CSV should not overwrite personalization settings unless the user chooses a future full-backup format.

## Testing Strategy

Use pytest for non-GUI logic.

Required tests:

- Legacy CSV imports into a fresh v8 database.
- Import failure leaves the existing database unchanged.
- Merge import remaps task IDs and keeps reminder relationships correct.
- v8 CSV export can be imported into a fresh v8 database.
- Forgetting-curve repeat counts generate expected day offsets.
- Progress calculation reflects completed reminders.
- Snooze choices produce expected new reminder times.

GUI smoke testing can be manual initially, but data migration cannot rely on manual testing.

## Git And Versioning

Use branch `codex/v8-modern-gui`.

Commit stages:

1. Design spec.
2. Project scaffolding and tests.
3. Data and CSV compatibility layer.
4. Scheduler logic.
5. PySide6 GUI.
6. README and v8 update record.

Add or update ignore rules so local/generated files are not accidentally committed:

- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.superpowers/`
- `build/`
- `dist/`
- local SQLite databases

Do not remove currently tracked build artifacts as part of the design step. If cleanup is desired, do it as a separate explicit repository-maintenance change.

## Documentation

Create `update_record/curve_tool_record_v8.md` with:

- Summary of the PySide6 GUI upgrade.
- Explanation of legacy CSV import support.
- Data safety guarantees.
- Personalization features.
- Known migration notes.

Update `README.md` to describe:

- v8 entrypoint.
- installation dependencies.
- legacy CSV import workflow.
- current status of report/email features if they remain out of scope.

## Out Of Scope For v8

Unless explicitly approved as an added requirement, v8 does not need to include:

- Email report sending.
- Advanced analytics charts.
- Cloud sync.
- Mobile app support.
- Full backup of background image binary files through CSV.

These can be added after the migration-safe GUI version exists.
