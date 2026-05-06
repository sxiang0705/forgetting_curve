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
    else:
        window_bg = "#f3f6fb"
        surface = "#ffffff"
        panel = "#ffffff"
        text = "#111827"
        muted = "#6b7280"
        border = "#d9e2ef"
        hover = "#eef4ff"
        table_alt = "#f8fafc"

    return f"""
QMainWindow {{
    background: {window_bg};
}}

QWidget {{
    color: {text};
    font-family: "Segoe UI", "Noto Sans TC", sans-serif;
    font-size: 14px;
}}

#Sidebar {{
    background: {surface};
    border-right: 1px solid {border};
}}

QPushButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: {padding};
    text-align: left;
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

QFrame#Panel {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 8px;
    padding: {panel_padding};
}}

QLabel#Muted {{
    color: {muted};
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

QCalendarWidget QWidget {{
    alternate-background-color: {table_alt};
}}
""".strip()
