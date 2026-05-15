from __future__ import annotations

ACCENTS = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "purple": "#7c3aed",
    "orange": "#ea580c",
    "gray": "#4b5563",
}


def build_stylesheet(accent: str = "blue", dark: bool = False, compact: bool = False) -> str:
    accent_color = ACCENTS.get(accent, ACCENTS["blue"])
    padding = "6px 10px" if compact else "9px 14px"
    panel_padding = "10px" if compact else "16px"

    if dark:
        window_bg = "#111827"
        surface = "#1f2937"
        panel = "#273244"
        text = "#f9fafb"
        muted = "#9ca3af"
        border = "#374151"
        hover = "#374151"
        table_alt = "#182132"
        soft = "#1e3a5f"
    else:
        window_bg = "#edf4fb"
        surface = "rgba(248, 250, 252, 0.92)"
        panel = "rgba(255, 255, 255, 0.93)"
        text = "#111827"
        muted = "#6b7280"
        border = "#d9e2ef"
        hover = "#eef4ff"
        table_alt = "#f8fafc"
        soft = "#dbeafe"

    return f"""
QMainWindow {{
    background: {window_bg};
}}

QWidget {{
    color: {text};
    font-family: "Segoe UI", "Noto Sans TC", sans-serif;
    font-size: 16px;
}}

#Sidebar {{
    background: {surface};
    border-right: 1px solid {border};
}}

QPushButton {{
    background: #ffffff;
    border: 1px solid {border};
    border-radius: 8px;
    padding: {padding};
    text-align: center;
    font-weight: 600;
}}

QPushButton:hover {{
    background: {hover};
    border-color: {border};
}}

QPushButton#PrimaryButton {{
    background: {accent_color};
    border-color: {accent_color};
    color: white;
    font-weight: 600;
    text-align: center;
}}

QPushButton#PrimaryButton:hover {{
    background: {accent_color};
}}

QPushButton#OutlineActionButton,
QPushButton#AssetDeleteButton {{
    background: #ffffff;
    border: 1px solid #c8d4e4;
    border-radius: 8px;
    color: #344054;
    font-weight: 800;
    padding: 10px 13px;
    text-align: center;
}}

QPushButton#ChipButton, QPushButton#ChipButtonActive {{
    border-radius: 999px;
    padding: 7px 11px;
    text-align: center;
}}

QPushButton#ChipButtonActive {{
    background: {soft};
    border-color: #93c5fd;
    color: #1d4ed8;
    font-weight: 800;
}}

QPushButton#IconButton {{
    padding: 7px 0;
    font-size: 18px;
    font-weight: 800;
}}

QFrame#CalendarPanel {{
    background: transparent;
    border: 0;
}}

QPushButton#CalendarDay,
QPushButton#CalendarDayMuted,
QPushButton#CalendarDayLoad1,
QPushButton#CalendarDayLoad2,
QPushButton#CalendarDayLoad3,
QPushButton#CalendarDayLoad4,
QPushButton#CalendarDaySelected {{
    border-radius: 8px;
    padding: 4px;
    text-align: center;
    font-weight: 600;
}}

QPushButton#CalendarDay {{
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    color: #334155;
}}

QPushButton#CalendarDayMuted {{
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    color: #94a3b8;
}}

QPushButton#CalendarDayLoad1 {{
    background: #dcfce7;
    border: 1px solid #86efac;
    color: #166534;
}}

QPushButton#CalendarDayLoad2 {{
    background: #fef3c7;
    border: 1px solid #fcd34d;
    color: #854d0e;
}}

QPushButton#CalendarDayLoad3 {{
    background: #ffedd5;
    border: 1px solid #fdba74;
    color: #9a3412;
}}

QPushButton#CalendarDayLoad4 {{
    background: #fee2e2;
    border: 1px solid #fca5a5;
    color: #991b1b;
}}

QPushButton#CalendarDaySelected {{
    background: #dbeafe;
    border: 3px solid {accent_color};
    color: #1e3a8a;
}}

QFrame#Panel, QFrame#SectionPanel {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 8px;
    padding: {panel_padding};
}}

QFrame#SectionPanel {{
    padding: 10px;
}}

QFrame#PersonalizationPreview {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 16px;
}}

QFrame#AssetRow {{
    background: #fbfdff;
    border: 1px solid {border};
    border-radius: 8px;
}}

QLabel#Muted {{
    color: {muted};
}}

QLabel#CountPill {{
    background: {soft};
    border-radius: 14px;
    color: #1d4ed8;
    font-weight: 900;
    padding: 5px 8px;
}}

QLabel#NextMiniTask {{
    border-top: 1px solid {border};
    padding-top: 7px;
    line-height: 1.4;
}}

QLabel#WarningNote {{
    background: #fff7ed;
    border-left: 3px solid #f59e0b;
    color: #92400e;
    padding: 10px;
}}

QFrame#PreviewRow {{
    border-bottom: 1px solid {border};
    padding: 8px 0;
}}

QScrollArea {{
    background: transparent;
    border: 0;
}}

QTableWidget {{
    background: {surface};
    alternate-background-color: {table_alt};
    border: 1px solid {border};
    border-radius: 8px;
    gridline-color: {border};
    selection-background-color: {accent_color};
    selection-color: white;
}}

QHeaderView::section {{
    background: {table_alt};
    border: 0;
    border-bottom: 1px solid {border};
    color: {muted};
    font-weight: 600;
    padding: 8px;
}}

QLineEdit {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 6px;
    padding: {padding};
}}

QComboBox, QTextEdit {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 6px;
    padding: {padding};
}}

QComboBox:disabled {{
    background: {table_alt};
    border-color: {border};
    color: {muted};
}}

QComboBox:disabled::drop-down {{
    border: 0;
}}

QDialog {{
    background: {window_bg};
}}

QCalendarWidget QWidget {{
    alternate-background-color: {table_alt};
}}
""".strip()
