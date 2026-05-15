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
