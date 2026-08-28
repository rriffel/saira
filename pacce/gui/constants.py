"""
constants.py — Shared styling constants for all PACCE GUI modules.
"""

# Styling constants
ACCENT = "#0D9488"
ACCENT_HOVER = "#0F766E"
DARK_BG = "#FFFFFF"
CARD_BG = "#F8FAFC"
TEXT_COLOR = "#0F172A"
MUTED = "#64748B"
BORDER_COLOR = "#CBD5E1"
SUCCESS_COLOR = "#10B981"
DANGER_COLOR = "#EF4444"

STYLESHEET = f"""
QMainWindow {{
    background: {DARK_BG};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}}

QGroupBox {{
    background: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    margin-top: 18px;
    padding: 16px 12px 12px 12px;
    color: {TEXT_COLOR};
    font-weight: 600;
    font-size: 13px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 2px;
    color: {ACCENT};
    padding: 0 4px;
}}

QLabel {{
    color: {TEXT_COLOR};
    font-size: 13px;
}}

QPushButton {{
    background-color: {ACCENT};
    color: white;
    font-weight: 600;
    font-size: 13px;
    border-radius: 6px;
    padding: 8px 16px;
    border: none;
}}
QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton:disabled {{
    background-color: #94A3B8;
    color: #F1F5F9;
}}

QPushButton#navBtn {{
    background-color: transparent;
    color: #64748B;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}}
QPushButton#navBtn:hover {{
    background-color: #F1F5F9;
    color: #1E293B;
}}
QPushButton#navBtn[active="true"] {{
    background-color: #F0FDFA;
    color: {ACCENT};
    border-left: 3px solid {ACCENT};
}}

QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_COLOR};
    font-size: 13px;
    min-height: 20px;
}}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1px solid {ACCENT};
}}

QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {{
    background-color: #F1F5F9;
    color: #94A3B8;
}}

QCheckBox, QRadioButton {{
    color: {TEXT_COLOR};
    font-size: 13px;
    spacing: 6px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid {BORDER_COLOR};
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

QTableWidget {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER_COLOR};
    gridline-color: #E2E8F0;
    border-radius: 6px;
    color: {TEXT_COLOR};
}}
QHeaderView::section {{
    background-color: #F1F5F9;
    padding: 6px;
    border: 1px solid {BORDER_COLOR};
    font-weight: 600;
    color: #475569;
}}

QTextEdit {{
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
    padding: 8px;
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QProgressBar {{
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    background-color: #F1F5F9;
    text-align: center;
    color: {TEXT_COLOR};
    font-size: 12px;
    min-height: 20px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 5px;
}}

QSplitter::handle {{
    background-color: {BORDER_COLOR};
    height: 3px;
}}
"""
