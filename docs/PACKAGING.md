# Renew Curve v8 打包說明

這份文件說明如何把 Renew Curve v8 打包成 Windows 可執行版本。

## 打包型態與 GitHub 版本

repo 內提供一份可直接下載的單檔 exe：

```text
release/RenewCurveV8.exe
```

開發與驗證時仍建議先使用 PyInstaller 的 `onedir` 模式，輸出會是一個資料夾：

```text
dist/RenewCurveV8/RenewCurveV8.exe
```

PySide6/Qt 應用程式用 `onedir` 通常比單檔 exe 穩定，也比較容易確認 Qt plugin 與資源檔是否完整。

若要放進 GitHub repo，請使用 `onefile` 模式產生單一 exe，再複製到 `release/`。

## 準備環境

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
```

`dev` 依賴包含：

- `pytest`
- `pyinstaller`

## 執行 onedir 打包

```bash
.\.venv\Scripts\python -m PyInstaller --clean --noconfirm renew_curve.spec
```

完成後執行：

```bash
.\dist\RenewCurveV8\RenewCurveV8.exe
```

## 產生 GitHub repo 內的單檔 exe

```bash
.\.venv\Scripts\python -m PyInstaller --clean --noconfirm renew_curve_onefile.spec
New-Item -ItemType Directory -Force release
Copy-Item .\dist\RenewCurveV8.exe .\release\RenewCurveV8.exe -Force
```

單檔 exe 第一次啟動會比較慢，因為 PyInstaller 需要先解包 Qt 與 Python runtime。

## Icon 與資源

- exe icon 使用 `resources/icons/FC_3_icon.ico`。
- 程式啟動時也會使用同一個 icon 設定視窗與工作列圖示。
- PyInstaller spec 會把 icon 一起放進打包輸出。

## 本機資料

打包出的 exe 會在執行位置旁建立或使用：

- `renew_curve_v8.db`
- `assets/`

這些是使用者本機資料，不會提交到 GitHub。若要搬移資料，請在程式裡使用 `匯出完整資料` 產生 ZIP 備份。

## 清理打包產物

`build/` 與 `dist/` 是本機打包產物，已被 `.gitignore` 排除。`release/RenewCurveV8.exe` 是刻意放進 GitHub 的下載版本。需要重新打包時可以刪除 `build/` 與 `dist/` 後重跑 PyInstaller。
