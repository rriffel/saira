"""
constants.py — Shared styling constants and light/dark theming for all SAIRA GUI modules.

Widgets that need a themed color should NOT bake it into their own inline
setStyleSheet() string. Instead, set a Qt dynamic property (e.g.
``widget.setProperty("role", "mutedLabel")``) and let the app-wide stylesheet
built by build_stylesheet() color it via a ``[role="..."]`` selector. That way,
switching themes only requires re-applying the top-level stylesheet (see
set_theme()) — every widget using a role re-colors automatically.

Other modules should access colors as ``constants.ACCENT`` (via
``from . import constants``) rather than ``from .constants import ACCENT``,
so they see the live value after a theme switch instead of the one captured
at import time.
"""

_LIGHT = dict(
    ACCENT="#0D9488",
    ACCENT_HOVER="#0F766E",
    WINDOW_BG="#FFFFFF",
    CARD_BG="#F8FAFC",
    TEXT_COLOR="#0F172A",
    MUTED="#64748B",
    BORDER_COLOR="#CBD5E1",
    SUCCESS_COLOR="#10B981",
    DANGER_COLOR="#EF4444",
    INPUT_BG="#FFFFFF",
    DISABLED_BG="#F1F5F9",
    DISABLED_TEXT="#94A3B8",
    NAV_HOVER_BG="#F1F5F9",
    NAV_HOVER_TEXT="#1E293B",
    NAV_ACTIVE_BG="#F0FDFA",
    HEADER_BG="#F1F5F9",
    HEADER_TEXT="#475569",
    GRIDLINE="#E2E8F0",
    SECONDARY_BTN_BG="#F8FAFC",
    SECONDARY_BTN_TEXT="#334155",
    MUTED_BTN_BG="#94A3B8",
    PROGRESS_BG="#F1F5F9",
)

_DARK = dict(
    ACCENT="#2DD4BF",
    ACCENT_HOVER="#5EEAD4",
    WINDOW_BG="#0F172A",
    CARD_BG="#1E293B",
    TEXT_COLOR="#E2E8F0",
    MUTED="#94A3B8",
    BORDER_COLOR="#334155",
    SUCCESS_COLOR="#34D399",
    DANGER_COLOR="#F87171",
    INPUT_BG="#1E293B",
    DISABLED_BG="#0F172A",
    DISABLED_TEXT="#64748B",
    NAV_HOVER_BG="#334155",
    NAV_HOVER_TEXT="#F1F5F9",
    NAV_ACTIVE_BG="#134E4A",
    HEADER_BG="#334155",
    HEADER_TEXT="#CBD5E1",
    GRIDLINE="#334155",
    SECONDARY_BTN_BG="#1E293B",
    SECONDARY_BTN_TEXT="#CBD5E1",
    MUTED_BTN_BG="#475569",
    PROGRESS_BG="#334155",
)

# Fixed colors for matplotlib figures (plot_dialog.py). Figures always render
# on a white canvas regardless of the app theme, so their palette stays put.
PLOT_ACCENT = "#0D9488"
PLOT_DANGER = "#EF4444"

_is_dark = True
_colors = dict(_DARK)


def is_dark():
    return _is_dark


def _apply(colors):
    """Publish a palette's colors as module-level attributes (constants.ACCENT, etc.)."""
    globals().update(colors)


def build_stylesheet():
    """Build the full app stylesheet from the current palette."""
    c = _colors
    return f"""
QMainWindow {{
    background: {c['WINDOW_BG']};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}}

QDialog {{
    background: {c['WINDOW_BG']};
}}

QWidget {{
    background-color: {c['WINDOW_BG']};
}}

QStatusBar {{
    background-color: {c['WINDOW_BG']};
    color: {c['TEXT_COLOR']};
}}

QWidget[role="sidebar"] {{
    background-color: {c['CARD_BG']};
    border-right: 1px solid {c['BORDER_COLOR']};
}}

QGroupBox {{
    background: {c['CARD_BG']};
    border: 1px solid {c['BORDER_COLOR']};
    border-radius: 8px;
    margin-top: 18px;
    padding: 16px 12px 12px 12px;
    color: {c['TEXT_COLOR']};
    font-weight: 600;
    font-size: 13px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 2px;
    color: {c['ACCENT']};
    padding: 0 4px;
}}

QLabel {{
    color: {c['TEXT_COLOR']};
    font-size: 13px;
}}
QLabel[role="appTitle"] {{
    color: {c['ACCENT']};
}}
QLabel[role="accentLabel"] {{
    color: {c['ACCENT']};
}}
QLabel[role="mutedLabel"] {{
    color: {c['MUTED']};
}}
QLabel[role="dangerLabel"] {{
    color: {c['DANGER_COLOR']};
}}

QPushButton {{
    background-color: {c['ACCENT']};
    color: white;
    font-weight: 600;
    font-size: 13px;
    border-radius: 6px;
    padding: 8px 16px;
    border: none;
}}
QPushButton:hover {{
    background-color: {c['ACCENT_HOVER']};
}}
QPushButton:disabled {{
    background-color: {c['DISABLED_BG']};
    color: {c['DISABLED_TEXT']};
}}

QPushButton[role="runBtn"] {{
    background-color: {c['SUCCESS_COLOR']};
    color: white;
    font-weight: bold;
    font-size: 14px;
    padding: 10px 16px;
    border-radius: 8px;
}}

QPushButton[role="secondaryBtn"] {{
    background-color: {c['SECONDARY_BTN_BG']};
    border: 1px solid {c['BORDER_COLOR']};
    border-radius: 6px;
    padding: 6px;
    color: {c['SECONDARY_BTN_TEXT']};
    font-weight: 600;
}}
QPushButton[role="secondaryBtn"]:hover {{
    background-color: {c['CARD_BG']};
}}

QPushButton[role="mutedBtn"] {{
    background-color: {c['MUTED_BTN_BG']};
}}

QPushButton#navBtn {{
    background-color: transparent;
    color: {c['MUTED']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}}
QPushButton#navBtn:hover {{
    background-color: {c['NAV_HOVER_BG']};
    color: {c['NAV_HOVER_TEXT']};
}}
QPushButton#navBtn[active="true"] {{
    background-color: {c['NAV_ACTIVE_BG']};
    color: {c['ACCENT']};
    border-left: 3px solid {c['ACCENT']};
}}

QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{
    background-color: {c['INPUT_BG']};
    border: 1px solid {c['BORDER_COLOR']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {c['TEXT_COLOR']};
    font-size: 13px;
    min-height: 20px;
}}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1px solid {c['ACCENT']};
}}

QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {{
    background-color: {c['DISABLED_BG']};
    color: {c['DISABLED_TEXT']};
}}

QCheckBox, QRadioButton {{
    color: {c['TEXT_COLOR']};
    font-size: 13px;
    spacing: 6px;
}}
QCheckBox[role="masterToggle"] {{
    color: {c['ACCENT']};
    font-weight: bold;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid {c['BORDER_COLOR']};
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {c['ACCENT']};
    border-color: {c['ACCENT']};
}}

QTableWidget {{
    background-color: {c['INPUT_BG']};
    border: 1px solid {c['BORDER_COLOR']};
    gridline-color: {c['GRIDLINE']};
    border-radius: 6px;
    color: {c['TEXT_COLOR']};
}}
QHeaderView::section {{
    background-color: {c['HEADER_BG']};
    padding: 6px;
    border: 1px solid {c['BORDER_COLOR']};
    font-weight: 600;
    color: {c['HEADER_TEXT']};
}}

QTextEdit {{
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid {c['BORDER_COLOR']};
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
    border: 1px solid {c['BORDER_COLOR']};
    border-radius: 6px;
    background-color: {c['PROGRESS_BG']};
    text-align: center;
    color: {c['TEXT_COLOR']};
    font-size: 12px;
    min-height: 20px;
}}
QProgressBar::chunk {{
    background-color: {c['ACCENT']};
    border-radius: 5px;
}}

QSplitter::handle {{
    background-color: {c['BORDER_COLOR']};
    height: 3px;
}}
"""


def set_theme(dark):
    """Switch the active palette and return the freshly built stylesheet."""
    global _is_dark, _colors
    _is_dark = bool(dark)
    _colors = dict(_DARK if _is_dark else _LIGHT)
    _apply(_colors)
    globals()["STYLESHEET"] = build_stylesheet()
    return STYLESHEET


_apply(_colors)
STYLESHEET = build_stylesheet()
