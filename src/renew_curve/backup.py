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
