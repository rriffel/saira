"""
main_gui.py — Main SAIRA GUI window.

A modern, single-page interface for configuring and running SAIRA
(Self-consistent Algorithm for spectral Indices measuRements and Analysis).
"""

import os
import sys
import json
import io
import traceback
import threading

import numpy as np
import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QGroupBox, QCheckBox, QRadioButton,
    QButtonGroup, QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem, QSplitter, QProgressBar,
    QFileDialog, QMessageBox, QSizePolicy, QComboBox, QSpacerItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor

from . import constants
from .custom_widgets import (
    FilePickerRow, ToggleValueFileRow,
    ToggleTextRow, ToggleFilePickerRow, LogConsole
)
from .index_selection_dialog import IndexSelectionDialog
from .plot_dialog import PlotDialog
from .script_io import generate_script, import_script, ScriptImportError


# Tooltips describing the files accepted by the Value/File rows
RES_INI_FILE_TOOLTIP = (
    "File mode accepts either:\n"
    "  • a wavelength-dependent curve: two columns, wavelength (Å) and value,\n"
    "    interpolated onto each spectrum (e.g. suport_files/e-miles_spectral_resolution_fwhm.dat\n"
    "    for FWHM or e-miles_spectral_resolution_sigma.dat for σ);\n"
    "  • one value per spectrum: columns 'file' and 'sigma' / 'FWHM' / 'R'\n"
    "    (e.g. examples/sdss_table_example.dat for σ_ini)."
)
RES_FIN_FILE_TOOLTIP = (
    "File mode accepts a wavelength-dependent curve: two columns,\n"
    "wavelength (Å) and value, interpolated onto each spectrum\n"
    "(e.g. suport_files/e-miles_spectral_resolution_fwhm.dat or _sigma.dat)."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_mask_regions(text):
    """
    Parse wavelength intervals such as "4855-4870, 5570-5585" (or "4855 4870; 5570 5585")
    into a list of (lambda_min, lambda_max) tuples. Raises ValueError if malformed.
    """
    import re
    numbers = [float(x) for x in re.findall(r"\d+(?:\.\d*)?|\.\d+", text or "")]
    if not numbers or len(numbers) % 2:
        raise ValueError(f"Mask regions must be pairs of wavelengths, e.g. 4855-4870, 5570-5585 (got '{text}').")
    return [(min(a, b), max(a, b)) for a, b in zip(numbers[0::2], numbers[1::2])]


def format_mask_regions(regions):
    """Inverse of parse_mask_regions."""
    return ", ".join(f"{lo:g}-{hi:g}" for lo, hi in regions)


def get_logo_path():
    """Return the path to the SAIRA logo, or None if not found."""
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for ext in ("jpg", "jpeg", "png"):
        p = os.path.join(pkg_dir, "assets", f"logo.{ext}")
        if os.path.isfile(p):
            return p
    return None


def get_support_dir():
    """Return the path to the bundled support_files directory."""
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(pkg_dir, "suport_files")


# ---------------------------------------------------------------------------
# Worker Thread — runs saira() in the background
# ---------------------------------------------------------------------------

class SairaWorker(QThread):
    """Run the SAIRA wrapper in a background thread."""

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(object)   # pandas DataFrame or None
    error_signal = pyqtSignal(str)

    def __init__(self, kwargs):
        super().__init__()
        self.kwargs = kwargs

    def run(self):
        # Redirect stdout so print() calls from saira are captured
        old_stdout = sys.stdout
        sys.stdout = _StreamRedirector(self.log_signal)
        try:
            from saira.saira_wapper import saira
            result = saira(**self.kwargs)
            self.finished_signal.emit(result)
        except Exception:
            tb = traceback.format_exc()
            self.error_signal.emit(tb)
            self.finished_signal.emit(None)
        finally:
            sys.stdout = old_stdout


class _StreamRedirector(io.TextIOBase):
    """Redirect write() calls to a Qt signal."""

    def __init__(self, signal):
        super().__init__()
        self._signal = signal

    def write(self, text):
        if text and text.strip():
            self._signal.emit(text)
        return len(text) if text else 0

    def flush(self):
        pass


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """SAIRA — Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SAIRA — Self-consistent Algorithm for spectral Indices measuRements and Analysis")
        self.resize(1200, 860)
        self.setStyleSheet(constants.STYLESHEET)

        self.worker = None
        self.result_df = None
        self.custom_idx_definitions = None  # set when the user customizes via "Select Indices…"

        self._init_ui()

    # -----------------------------------------------------------------
    # UI Construction
    # -----------------------------------------------------------------

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # Content: top panels + bottom log/results
        right_side = QWidget()
        right_layout = QVBoxLayout(right_side)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        splitter = QSplitter(Qt.Vertical)

        # Top: scrollable config panels
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.panels_layout = QVBoxLayout(scroll_content)
        self.panels_layout.setContentsMargins(20, 16, 20, 16)
        self.panels_layout.setSpacing(14)

        self._create_panel_input_files()
        self._create_panel_resolution()
        self._create_panel_options()
        self._create_panel_plots()

        self.panels_layout.addStretch()
        scroll.setWidget(scroll_content)
        splitter.addWidget(scroll)

        # Bottom: log + results
        bottom = self._create_bottom_panel()
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        right_layout.addWidget(splitter)
        main_layout.addWidget(right_side, 1)

        # Status bar
        self.statusBar().showMessage("Ready — Configure parameters and click Run SAIRA.")

    # ----- Sidebar -----

    def _create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setProperty("role", "sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(8)

        # Title
        title = QLabel("SAIRA")
        title.setProperty("role", "appTitle")
        title.setStyleSheet("font-size: 20px; font-weight: 800; margin-bottom: 2px;")
        sub = QLabel("Self-consistent Algorithm for spectral Indices measuRements and Analysis")
        sub.setProperty("role", "mutedLabel")
        sub.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
        sub.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(sub)

        # Logo
        logo_path = get_logo_path()
        if logo_path:
            pix = QPixmap(logo_path)
            if not pix.isNull():
                lbl = QLabel()
                lbl.setPixmap(pix.scaledToWidth(190, Qt.SmoothTransformation))
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet(
                    "background: transparent; border: none; margin-bottom: 12px;"
                )
                layout.addWidget(lbl)

        # Section navigation buttons
        self.nav_buttons = []
        sections = [
            ("1. Input Files", 0),
            ("2. Resolution", 1),
            ("3. Other Settings", 2),
            ("4. Plots & Output", 3),
        ]
        for text, idx in sections:
            btn = QPushButton(text.replace("&", "&&"))  # a single & would become a keyboard mnemonic
            btn.setObjectName("navBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self._scroll_to_section(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addSpacing(16)

        # Run button
        self.btn_run = QPushButton("▶  Run SAIRA")
        self.btn_run.setProperty("role", "runBtn")
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self._on_run)
        layout.addWidget(self.btn_run)

        layout.addSpacing(12)

        # Config state
        lbl_cfg = QLabel("Configuration")
        lbl_cfg.setProperty("role", "accentLabel")
        lbl_cfg.setStyleSheet("font-size: 11px; font-weight: bold; margin-bottom: 2px;")
        layout.addWidget(lbl_cfg)

        btn_load = QPushButton("Load Config")
        btn_load.setProperty("role", "secondaryBtn")
        btn_load.setCursor(Qt.PointingHandCursor)
        btn_load.clicked.connect(self._on_load_config)
        layout.addWidget(btn_load)

        btn_save = QPushButton("Save Config")
        btn_save.setProperty("role", "secondaryBtn")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._on_save_config)
        layout.addWidget(btn_save)

        btn_export_script = QPushButton("Export Script (.py)")
        btn_export_script.setProperty("role", "secondaryBtn")
        btn_export_script.setCursor(Qt.PointingHandCursor)
        btn_export_script.setToolTip("Save the current configuration as a standalone Python script")
        btn_export_script.clicked.connect(self._on_export_script)
        layout.addWidget(btn_export_script)

        btn_load_script = QPushButton("Load Script (.py)")
        btn_load_script.setProperty("role", "secondaryBtn")
        btn_load_script.setCursor(Qt.PointingHandCursor)
        btn_load_script.setToolTip("Fill the GUI from a script that calls saira()")
        btn_load_script.clicked.connect(self._on_load_script)
        layout.addWidget(btn_load_script)

        layout.addSpacing(12)

        # Appearance
        lbl_appearance = QLabel("Appearance")
        lbl_appearance.setProperty("role", "accentLabel")
        lbl_appearance.setStyleSheet("font-size: 11px; font-weight: bold; margin-bottom: 2px;")
        layout.addWidget(lbl_appearance)

        self.chk_dark_mode = QCheckBox("  Dark Mode")
        self.chk_dark_mode.setChecked(constants.is_dark())
        self.chk_dark_mode.toggled.connect(self._on_toggle_theme)
        layout.addWidget(self.chk_dark_mode)

        layout.addStretch()

        # Footer
        footer = QLabel("Rogério Riffel\nJoão P. V. Benedetti\nUFRGS / Depto Astronomia")
        footer.setProperty("role", "mutedLabel")
        footer.setStyleSheet("font-size: 11px; line-height: 1.4;")
        layout.addWidget(footer)

        return sidebar

    def _on_toggle_theme(self, checked):
        """Switch between light and dark mode."""
        constants.set_theme(checked)
        self.setStyleSheet(constants.STYLESHEET)

    # ----- Section Scroll -----

    def _scroll_to_section(self, idx):
        """Scroll the main area to the requested GroupBox."""
        targets = [self.grp_input, self.grp_resolution, self.grp_options, self.grp_plots]
        if 0 <= idx < len(targets):
            targets[idx].ensurePolished()
            # Find the scroll area
            scroll = self.centralWidget().findChild(QScrollArea)
            if scroll:
                scroll.ensureWidgetVisible(targets[idx], 0, 20)

        # Highlight active nav button
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # -----------------------------------------------------------------
    # Panel 1: Input Files
    # -----------------------------------------------------------------

    def _create_panel_input_files(self):
        self.grp_input = QGroupBox("Input Files")
        lay = QVBoxLayout(self.grp_input)
        lay.setSpacing(10)

        # Redshift correction comes first: how z is given depends on the input mode
        # (one z per spectrum from the table, or a single z for a whole directory).
        self.chk_enable_redshift = QCheckBox("  Enable Redshift Correction")
        self.chk_enable_redshift.setProperty("role", "masterToggle")
        self.chk_enable_redshift.setChecked(False)
        self.chk_enable_redshift.toggled.connect(self._update_redshift_widgets)
        lay.addWidget(self.chk_enable_redshift)

        self.lbl_z_table = QLabel(
            "The redshift of each spectrum is read from the Spectrum List, which must be "
            "a CSV file whose header contains the columns file,redshift."
        )
        self.lbl_z_table.setProperty("role", "accentLabel")
        self.lbl_z_table.setStyleSheet("font-size: 12px;")
        self.lbl_z_table.setWordWrap(True)
        lay.addWidget(self.lbl_z_table)

        self.z_row = QWidget()
        z_lay = QHBoxLayout(self.z_row)
        z_lay.setContentsMargins(0, 0, 0, 0)
        z_lay.setSpacing(8)
        z_label = QLabel("Redshift (z):")
        z_label.setFixedWidth(140)
        z_label.setStyleSheet("font-weight: 500;")
        z_lay.addWidget(z_label)
        self.spin_z = QDoubleSpinBox()
        self.spin_z.setRange(0.0, 20.0)
        self.spin_z.setDecimals(8)
        self.spin_z.setSingleStep(0.001)
        self.spin_z.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        z_lay.addWidget(self.spin_z, 1)
        lay.addWidget(self.z_row)

        self.lbl_z_warning = QLabel(
            "⚠  The same redshift will be applied to ALL spectra found in the directory. "
            "To correct each spectrum with its own z, use Table / File List mode."
        )
        self.lbl_z_warning.setProperty("role", "dangerLabel")
        self.lbl_z_warning.setStyleSheet("font-size: 12px;")
        self.lbl_z_warning.setWordWrap(True)
        lay.addWidget(self.lbl_z_warning)

        # Mode Selection
        mode_row = QWidget()
        mode_lay = QHBoxLayout(mode_row)
        mode_lay.setContentsMargins(0, 0, 0, 0)
        mode_lay.setSpacing(16)

        mode_label = QLabel("Input Mode:")
        mode_label.setFixedWidth(140)
        mode_label.setStyleSheet("font-weight: 500;")
        mode_lay.addWidget(mode_label)

        self.radio_table_mode = QRadioButton("Table / File List")
        self.radio_extension_mode = QRadioButton("Auto-discover by Extension")
        self.radio_table_mode.setChecked(True)
        self.radio_table_mode.toggled.connect(self._on_input_mode_changed)

        mode_lay.addWidget(self.radio_table_mode)
        mode_lay.addWidget(self.radio_extension_mode)
        mode_lay.addStretch()
        lay.addWidget(mode_row)

        self.pick_spectrum_list = FilePickerRow(
            "Spectrum List:", placeholder="ASCII table with 'file' column",
            file_filter="Data Files (*.dat *.txt *.csv);;All Files (*)"
        )
        lay.addWidget(self.pick_spectrum_list)

        self.pick_spectra_dir = FilePickerRow(
            "Spectra Directory:", placeholder="Folder containing spectra",
            is_directory=True
        )
        self.pick_spectra_dir.line_edit.textChanged.connect(self._update_discovered_count)
        lay.addWidget(self.pick_spectra_dir)

        # Extension row (visible in auto-discover mode)
        self.ext_row = QWidget()
        ext_lay = QHBoxLayout(self.ext_row)
        ext_lay.setContentsMargins(0, 0, 0, 0)
        ext_lay.setSpacing(8)

        ext_label = QLabel("File Extension:")
        ext_label.setFixedWidth(140)
        ext_label.setStyleSheet("font-weight: 500;")
        ext_lay.addWidget(ext_label)

        self.combo_extension = QComboBox()
        self.combo_extension.setEditable(True)
        self.combo_extension.addItems([".txt", ".dat", ".spec", "*.txt", "*.dat", "*"])
        self.combo_extension.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_extension.currentTextChanged.connect(self._update_discovered_count)
        ext_lay.addWidget(self.combo_extension, 1)

        self.lbl_discovered_count = QLabel("")
        self.lbl_discovered_count.setProperty("role", "accentLabel")
        self.lbl_discovered_count.setStyleSheet("font-size: 12px; font-weight: bold;")
        ext_lay.addWidget(self.lbl_discovered_count)

        lay.addWidget(self.ext_row)
        self.ext_row.setVisible(False)

        # Index Definitions with combo for bundled files
        idx_row = QWidget()
        idx_layout = QHBoxLayout(idx_row)
        idx_layout.setContentsMargins(0, 0, 0, 0)
        idx_layout.setSpacing(8)

        idx_label = QLabel("Index Definitions:")
        idx_label.setFixedWidth(140)
        idx_label.setStyleSheet("font-weight: 500;")
        idx_layout.addWidget(idx_label)

        self.combo_idx_defs = QComboBox()
        self.combo_idx_defs.setEditable(False)
        self.combo_idx_defs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._populate_idx_combo()
        self.combo_idx_defs.currentIndexChanged.connect(self._on_idx_defs_changed)
        idx_layout.addWidget(self.combo_idx_defs, 1)

        btn_custom_idx = QPushButton("Custom…")
        btn_custom_idx.setFixedWidth(90)
        btn_custom_idx.setCursor(Qt.PointingHandCursor)
        btn_custom_idx.clicked.connect(self._on_custom_idx)
        idx_layout.addWidget(btn_custom_idx)

        btn_select_idx = QPushButton("Select Indices…")
        btn_select_idx.setFixedWidth(120)
        btn_select_idx.setCursor(Qt.PointingHandCursor)
        btn_select_idx.clicked.connect(self._on_select_indices)
        idx_layout.addWidget(btn_select_idx)

        lay.addWidget(idx_row)

        self.lbl_idx_selection = QLabel("")
        self.lbl_idx_selection.setProperty("role", "accentLabel")
        self.lbl_idx_selection.setStyleSheet("font-size: 11px;")
        lay.addWidget(self.lbl_idx_selection)

        self.pick_output = FilePickerRow(
            "Output File:", placeholder="measurements.csv (CSV format)",
            file_filter="CSV Files (*.csv);;Text Files (*.txt *.dat);;All Files (*)"
        )
        self.pick_output.set_text("measurements.csv")
        lay.addWidget(self.pick_output)

        self._update_redshift_widgets()
        self.panels_layout.addWidget(self.grp_input)

    def _on_input_mode_changed(self):
        is_table = self.radio_table_mode.isChecked()
        self.pick_spectrum_list.setVisible(is_table)
        self.ext_row.setVisible(not is_table)
        if not is_table:
            self._update_discovered_count()
        self._update_redshift_widgets()

    def _update_redshift_widgets(self, *_):
        """Show only the redshift options that apply to the current input mode."""
        enabled = self.chk_enable_redshift.isChecked()
        is_table = self.radio_table_mode.isChecked()
        self.lbl_z_table.setVisible(enabled and is_table)
        self.z_row.setVisible(enabled and not is_table)
        self.lbl_z_warning.setVisible(enabled and not is_table)
        if enabled and is_table:
            self.pick_spectrum_list.line_edit.setPlaceholderText("CSV file with header: file,redshift")
            self.pick_spectrum_list.file_filter = "CSV Files (*.csv);;All Files (*)"
        else:
            self.pick_spectrum_list.line_edit.setPlaceholderText("ASCII table with 'file' column")
            self.pick_spectrum_list.file_filter = "Data Files (*.dat *.txt *.csv);;All Files (*)"

    def _validate_redshift_table(self, filename):
        """
        With the redshift correction on in Table mode, the spectrum list must be a
        CSV file with 'file' and 'redshift' columns and a valid z for every row.
        Returns None if valid, or an error description string.
        """
        if not filename.lower().endswith(".csv"):
            return (f"With the redshift correction enabled, the Spectrum List must be a CSV "
                    f"file with the header file,redshift.\n\nSelected file: {filename}")
        try:
            table = pd.read_csv(filename, skipinitialspace=True)
        except Exception as e:
            return f"Could not read the Spectrum List as CSV: {e}"
        table.columns = [str(c).strip() for c in table.columns]
        missing = [c for c in ("file", "redshift") if c not in table.columns]
        if missing:
            return (f"The Spectrum List header must contain the columns file,redshift.\n\n"
                    f"Missing: {', '.join(missing)}\nFound: {', '.join(table.columns)}")
        z = pd.to_numeric(table["redshift"], errors="coerce")
        bad = table.loc[z.isna(), "file"].astype(str).tolist()
        if bad:
            return (f"{len(bad)} spectra have no valid redshift in the Spectrum List:\n\n"
                    + "\n".join(bad[:15]) + ("\n…" if len(bad) > 15 else ""))
        if (z < 0).any():
            return "The Spectrum List contains negative redshifts."
        return None

    def _update_discovered_count(self):
        if not hasattr(self, 'radio_extension_mode') or not self.radio_extension_mode.isChecked():
            return
        folder = self.pick_spectra_dir.text()
        ext = self.combo_extension.currentText().strip()
        if not ext:
            ext = ".txt"
        import fnmatch
        pattern = ext if ('*' in ext or '?' in ext) else f"*{ext if ext.startswith('.') else '.' + ext}"
        if folder and os.path.isdir(folder):
            try:
                matched = [
                    f for f in os.listdir(folder)
                    if fnmatch.fnmatch(f, pattern) and os.path.isfile(os.path.join(folder, f))
                ]
                self.lbl_discovered_count.setText(f"({len(matched)} spectra found)")
            except Exception:
                self.lbl_discovered_count.setText("")
        else:
            self.lbl_discovered_count.setText("")

    def _populate_idx_combo(self):
        """Add bundled .ind files from suport_files/ to the combo box."""
        self.combo_idx_defs.clear()
        support_dir = get_support_dir()
        if os.path.isdir(support_dir):
            for f in sorted(os.listdir(support_dir)):
                if f.endswith(".ind"):
                    self.combo_idx_defs.addItem(f, os.path.join(support_dir, f))

    def _on_custom_idx(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Index Definitions File", "",
            "Index Files (*.ind *.txt *.dat);;All Files (*)"
        )
        if path:
            name = os.path.basename(path)
            # Avoid duplicates
            idx = self.combo_idx_defs.findText(name)
            if idx >= 0:
                self.combo_idx_defs.setCurrentIndex(idx)
            else:
                self.combo_idx_defs.addItem(name, path)
                self.combo_idx_defs.setCurrentIndex(self.combo_idx_defs.count() - 1)

    def _on_idx_defs_changed(self):
        # A previously customized selection belonged to a different .ind file.
        self.custom_idx_definitions = None
        self.lbl_idx_selection.setText("")

    def _current_spectra_file_list(self):
        """
        Resolve (files, path_to_files) for the currently configured spectra
        source, or return (None, None) with a warning dialog if invalid.
        """
        from saira.saira_wapper import list_spectrum_files

        is_table_mode = self.radio_table_mode.isChecked()
        filename = self.pick_spectrum_list.text() if is_table_mode else None
        file_ext = self.combo_extension.currentText().strip() if not is_table_mode else None
        path_to_files = self.pick_spectra_dir.text()

        if is_table_mode and not filename:
            QMessageBox.warning(self, "Missing Input", "Spectrum list file is required in Table mode.")
            return None, None
        if not path_to_files or not os.path.isdir(path_to_files):
            QMessageBox.warning(self, "Missing Input", "A valid spectra directory is required.")
            return None, None

        try:
            files = list_spectrum_files(filename, path_to_files, file_ext)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not list spectrum files: {e}")
            return None, None
        if not files:
            QMessageBox.warning(self, "No Spectra Found", "No spectrum files matched the current configuration.")
            return None, None
        return files, path_to_files

    def _on_select_indices(self):
        index_defs = self.combo_idx_defs.currentData()
        if not index_defs:
            QMessageBox.warning(self, "Missing Input", "Select an Index Definitions file first.")
            return

        from saira.saira_wapper import read_idx_defs, get_spectra_wavelength_range

        try:
            idx_definitions = read_idx_defs(index_defs)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read index definitions: {e}")
            return

        wave_min = wave_max = None
        files, path_to_files = self._current_spectra_file_list()
        if files is not None:
            wave_min, wave_max = get_spectra_wavelength_range(path_to_files, files)

        dlg = IndexSelectionDialog(idx_definitions, wave_min, wave_max, parent=self)
        if dlg.exec_() == dlg.Accepted:
            self.custom_idx_definitions = dlg.get_filtered_definitions()
            n_sel = len(self.custom_idx_definitions)
            n_total = len(idx_definitions)
            self.lbl_idx_selection.setText(f"Custom selection: {n_sel}/{n_total} indices active")

    # -----------------------------------------------------------------
    # Panel 2: Redshift & Resolution
    # -----------------------------------------------------------------

    def _create_panel_resolution(self):
        self.grp_resolution = QGroupBox("Resolution")
        lay = QVBoxLayout(self.grp_resolution)
        lay.setSpacing(8)

        info = QLabel(
            "Resolution changes are optional and, when enabled, are applied after "
            "the redshift correction (Input Files). Each value can be a single number or a "
            "file (choose \"File\"): a wavelength-dependent curve (columns: "
            "wavelength, value) or, for the initial resolution, one value per "
            "spectrum (columns: file, value). Values may also come from the input "
            "table (columns: sigma, FWHM, R), which take precedence. Enable only "
            "one initial and one target resolution."
        )
        info.setProperty("role", "mutedLabel")
        info.setStyleSheet("font-size: 12px; margin-top: 8px; margin-bottom: 4px;")
        info.setWordWrap(True)
        lay.addWidget(info)

        self.chk_enable_resolution = QCheckBox("  Enable Resolution Changes")
        self.chk_enable_resolution.setProperty("role", "masterToggle")
        self.chk_enable_resolution.setChecked(False)
        self.chk_enable_resolution.toggled.connect(self._on_resolution_flag_toggled)
        lay.addWidget(self.chk_enable_resolution)

        self.opt_sigma_ini = ToggleValueFileRow(
            "σ_ini", suffix="km/s", max_val=999999, decimals=2,
            file_tooltip=RES_INI_FILE_TOOLTIP
        )
        lay.addWidget(self.opt_sigma_ini)

        self.opt_sigma_fin = ToggleValueFileRow(
            "σ_fin", suffix="km/s", max_val=999999, decimals=2,
            file_tooltip=RES_FIN_FILE_TOOLTIP
        )
        lay.addWidget(self.opt_sigma_fin)

        self.opt_fwhm_ini = ToggleValueFileRow(
            "FWHM_ini", suffix="Å", max_val=999999, decimals=4,
            file_tooltip=RES_INI_FILE_TOOLTIP
        )
        lay.addWidget(self.opt_fwhm_ini)

        self.opt_fwhm_fin = ToggleValueFileRow(
            "FWHM_fin", suffix="Å", max_val=999999, decimals=4,
            file_tooltip=RES_FIN_FILE_TOOLTIP
        )
        lay.addWidget(self.opt_fwhm_fin)

        self.opt_r_ini = ToggleValueFileRow(
            "R_ini", suffix="λ/Δλ", max_val=999999, decimals=1,
            file_tooltip=RES_INI_FILE_TOOLTIP
        )
        lay.addWidget(self.opt_r_ini)

        self.opt_r_fin = ToggleValueFileRow(
            "R_fin", suffix="λ/Δλ", max_val=999999, decimals=1,
            file_tooltip=RES_FIN_FILE_TOOLTIP
        )
        lay.addWidget(self.opt_r_fin)

        self._resolution_rows = (
            self.opt_sigma_ini, self.opt_sigma_fin,
            self.opt_fwhm_ini, self.opt_fwhm_fin,
            self.opt_r_ini, self.opt_r_fin,
        )
        self._on_resolution_flag_toggled(False)

        self.panels_layout.addWidget(self.grp_resolution)

    def _on_resolution_flag_toggled(self, checked):
        for row in self._resolution_rows:
            row.setEnabled(checked)

    # -----------------------------------------------------------------
    # Panel 3: Other Settings
    # -----------------------------------------------------------------

    def _create_panel_options(self):
        self.grp_options = QGroupBox("Other Settings")
        lay = QVBoxLayout(self.grp_options)
        lay.setSpacing(8)

        err_label = QLabel("Error Estimation:")
        err_label.setStyleSheet("font-weight: 500;")
        lay.addWidget(err_label)

        self.err_button_group = QButtonGroup(self)
        self.radio_err_none = QRadioButton("  Don't compute errors")
        self.radio_err_analytical = QRadioButton(
            "  Analytic: Vollmann and Eversberg (2006, DOI 10.1002/asna.2006)"
        )
        self.radio_err_propagation = QRadioButton(
            "  Analytic: first-order propagation of the error spectrum"
        )
        self.radio_err_propagation.setToolTip(
            "Propagates the uncertainty of every pixel through the same operations used to\n"
            "measure the index (continuum bands, pseudo-continuum and integration)."
        )
        self.radio_err_montecarlo = QRadioButton("  Monte Carlo")
        self.radio_err_none.setChecked(True)
        for rb in (self.radio_err_none, self.radio_err_analytical,
                   self.radio_err_propagation, self.radio_err_montecarlo):
            self.err_button_group.addButton(rb)

        lay.addWidget(self.radio_err_none)
        lay.addWidget(self.radio_err_analytical)
        lay.addWidget(self.radio_err_propagation)

        mc_row = QWidget()
        mc_lay = QHBoxLayout(mc_row)
        mc_lay.setContentsMargins(0, 0, 0, 0)
        mc_lay.setSpacing(8)
        mc_lay.addWidget(self.radio_err_montecarlo)
        self.spin_montecarlo_n = QSpinBox()
        self.spin_montecarlo_n.setRange(1, 100000)
        self.spin_montecarlo_n.setValue(100)
        self.spin_montecarlo_n.setSuffix("  iterations")
        self.spin_montecarlo_n.setEnabled(False)
        self.spin_montecarlo_n.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        mc_lay.addWidget(self.spin_montecarlo_n, 1)
        lay.addWidget(mc_row)
        self.radio_err_montecarlo.toggled.connect(self.spin_montecarlo_n.setEnabled)

        bad_label = QLabel("Bad Pixels:")
        bad_label.setStyleSheet("font-weight: 500; margin-top: 6px;")
        lay.addWidget(bad_label)

        self.chk_use_flags = QCheckBox("  Use a 4th column of the spectra as pixel flags (non-zero = bad)")
        self.chk_use_flags.setChecked(True)
        lay.addWidget(self.chk_use_flags)

        self.opt_mask_regions = ToggleTextRow(
            "Mask Regions (Å)", placeholder="Rest-frame intervals, e.g. 4855-4870, 5570-5585"
        )
        self.opt_mask_regions.setToolTip(
            "Wavelength intervals (rest frame, Å) masked in all spectra, e.g. emission lines\n"
            "or sky residuals. Bad pixels are replaced by a linear interpolation of the good ones."
        )
        lay.addWidget(self.opt_mask_regions)

        bpr_row = QWidget()
        bpr_lay = QHBoxLayout(bpr_row)
        bpr_lay.setContentsMargins(0, 0, 0, 0)
        bpr_lay.setSpacing(8)
        bpr_label = QLabel("Max. Bad Pixel Ratio")
        bpr_label.setFixedWidth(160)
        bpr_lay.addWidget(bpr_label)
        self.spin_bpr_thres = QDoubleSpinBox()
        self.spin_bpr_thres.setRange(0.0, 1.0)
        self.spin_bpr_thres.setDecimals(2)
        self.spin_bpr_thres.setSingleStep(0.05)
        self.spin_bpr_thres.setValue(1.0)
        self.spin_bpr_thres.setToolTip(
            "Indices with a larger fraction of bad pixels within their bandpasses are not\n"
            "measured (NaN). 1.0 keeps every index with at least one good pixel in its central band."
        )
        self.spin_bpr_thres.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bpr_lay.addWidget(self.spin_bpr_thres, 1)
        lay.addWidget(bpr_row)

        other_label = QLabel("Other Options:")
        other_label.setStyleSheet("font-weight: 500; margin-top: 6px;")
        lay.addWidget(other_label)

        self.chk_neg_to_zero = QCheckBox("  Set negative EW to zero")
        lay.addWidget(self.chk_neg_to_zero)

        self.opt_a_to_mag = ToggleTextRow(
            "Å → Magnitude", placeholder="Comma-separated index names (e.g. Mg1, Mg2)"
        )
        lay.addWidget(self.opt_a_to_mag)

        self.opt_compute_idx = ToggleFilePickerRow(
            "Composite Indices", placeholder="File with expressions (one per line)",
            file_filter="Text Files (*.txt);;All Files (*)"
        )
        lay.addWidget(self.opt_compute_idx)

        self.panels_layout.addWidget(self.grp_options)

    # -----------------------------------------------------------------
    # Panel 4: Plots & Output
    # -----------------------------------------------------------------

    def _create_panel_plots(self):
        self.grp_plots = QGroupBox("Plots && Output")
        lay = QVBoxLayout(self.grp_plots)
        lay.setSpacing(8)

        self.opt_single_plots = ToggleFilePickerRow(
            "Individual Plots", placeholder="Directory for per-index figures",
            is_directory=True
        )
        lay.addWidget(self.opt_single_plots)

        self.opt_all_plot = ToggleTextRow(
            "All-Indices Plot", placeholder="Filename (e.g. all_indices.png)"
        )
        lay.addWidget(self.opt_all_plot)

        self.opt_all_plot_dir = ToggleFilePickerRow(
            "All-Plots Directory", placeholder="Directory for combined plot",
            is_directory=True
        )
        lay.addWidget(self.opt_all_plot_dir)

        self.opt_log_file = ToggleTextRow(
            "Log File", placeholder="saira_log.txt"
        )
        lay.addWidget(self.opt_log_file)

        self.panels_layout.addWidget(self.grp_plots)

    # -----------------------------------------------------------------
    # Bottom Panel: Progress + Log + Results Table
    # -----------------------------------------------------------------

    def _create_bottom_panel(self):
        bottom = QWidget()
        lay = QVBoxLayout(bottom)
        lay.setContentsMargins(20, 8, 20, 12)
        lay.setSpacing(8)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        # Horizontal split: log + table
        h_split = QSplitter(Qt.Horizontal)

        # Log console
        log_group = QWidget()
        log_lay = QVBoxLayout(log_group)
        log_lay.setContentsMargins(0, 0, 0, 0)
        log_lay.setSpacing(4)
        lbl_log = QLabel("Run Log")
        lbl_log.setProperty("role", "accentLabel")
        lbl_log.setStyleSheet("font-size: 12px; font-weight: bold;")
        log_lay.addWidget(lbl_log)
        self.log_console = LogConsole()
        log_lay.addWidget(self.log_console)
        h_split.addWidget(log_group)

        # Results table
        table_group = QWidget()
        table_lay = QVBoxLayout(table_group)
        table_lay.setContentsMargins(0, 0, 0, 0)
        table_lay.setSpacing(4)

        hdr = QWidget()
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(0, 0, 0, 0)
        lbl_res = QLabel("Results Preview")
        lbl_res.setProperty("role", "accentLabel")
        lbl_res.setStyleSheet("font-size: 12px; font-weight: bold;")
        hdr_lay.addWidget(lbl_res)
        hdr_lay.addStretch()
        self.btn_plot = QPushButton("Plot…")
        self.btn_plot.setFixedHeight(28)
        self.btn_plot.setStyleSheet(
            "font-size: 11px; padding: 4px 10px;"
        )
        self.btn_plot.setCursor(Qt.PointingHandCursor)
        self.btn_plot.setEnabled(False)
        self.btn_plot.clicked.connect(self._on_plot_results)
        hdr_lay.addWidget(self.btn_plot)

        self.btn_export = QPushButton("Export CSV")
        self.btn_export.setFixedHeight(28)
        self.btn_export.setStyleSheet(
            "font-size: 11px; padding: 4px 10px;"
        )
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._on_export_csv)
        hdr_lay.addWidget(self.btn_export)
        table_lay.addWidget(hdr)

        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        table_lay.addWidget(self.results_table)
        h_split.addWidget(table_group)

        h_split.setStretchFactor(0, 2)
        h_split.setStretchFactor(1, 3)
        lay.addWidget(h_split, 1)

        return bottom

    # -----------------------------------------------------------------
    # Resolution Validation & Run SAIRA
    # -----------------------------------------------------------------

    def _validate_resolution_settings(self):
        """
        Validate that the user has not specified unphysical resolution parameters
        (e.g., trying to convolve to a higher spectral resolution).
        Returns None if valid, or an error description string if invalid.
        """
        c_kms = 299792.458
        ref_wave = 5000.0  # reference wavelength in Angstroms for equivalence comparison

        ini_rows = [("σ_ini", self.opt_sigma_ini, "sigma"),
                    ("FWHM_ini", self.opt_fwhm_ini, "fwhm"),
                    ("R_ini", self.opt_r_ini, "r")]
        fin_rows = [("σ_fin", self.opt_sigma_fin, "sigma"),
                    ("FWHM_fin", self.opt_fwhm_fin, "fwhm"),
                    ("R_fin", self.opt_r_fin, "r")]
        ini = [r for r in ini_rows if r[1].is_enabled()]
        fin = [r for r in fin_rows if r[1].is_enabled()]

        # In Table mode the initial resolution may come from the table itself
        # (columns sigma, FWHM or R), which takes precedence over the form.
        table_ini_cols = self._table_resolution_columns()

        # Resolution correction is enabled, so one "ini" and one "fin" value
        # must be provided — otherwise there is nothing to convolve.
        if not ini and not table_ini_cols:
            return (
                "Enable Resolution Correction is checked, but no initial resolution "
                "was set: enable one of σ_ini, FWHM_ini or R_ini, or add a sigma, "
                "FWHM or R column to the Spectrum List."
            )
        if not fin:
            return (
                "Enable Resolution Correction is checked, but no target resolution "
                "was set: enable one of σ_fin, FWHM_fin or R_fin."
            )
        if len(ini) > 1:
            return "Enable only one initial resolution (σ_ini, FWHM_ini or R_ini)."
        if len(fin) > 1:
            return "Enable only one target resolution (σ_fin, FWHM_fin or R_fin)."

        for label, row, _ in ini + fin:
            if row.is_file():
                path = row.file_path()
                if not path:
                    return f"{label} is set to File mode: choose a file."
                if not os.path.isfile(path):
                    return f"{label} file not found: {path}"
            elif row.value() <= 0:
                return f"{label} must be strictly positive (> 0)."

        # Per-spectrum values from the table are checked by saira() for every spectrum.
        if table_ini_cols or not ini:
            return None

        (label_ini, row_ini, kind_ini), (label_fin, row_fin, kind_fin) = ini[0], fin[0]
        # Wavelength-dependent or per-spectrum values are checked by saira()
        # for every spectrum, at every wavelength.
        if row_ini.is_file() or row_fin.is_file():
            return None

        def to_fwhm(kind, val):
            if kind == "fwhm":
                return val
            if kind == "sigma":
                return (val * 2.355 / c_kms) * ref_wave
            return ref_wave / val

        def describe(label, kind, val, fwhm):
            if kind == "fwhm":
                return f"{label} = {val:.2f} Å"
            unit = " km/s" if kind == "sigma" else ""
            return f"{label} = {val:.1f}{unit} (≈ {fwhm:.2f} Å at 5000 Å)"

        val_ini, val_fin = row_ini.value(), row_fin.value()
        fwhm_ini, fwhm_fin = to_fwhm(kind_ini, val_ini), to_fwhm(kind_fin, val_fin)
        if fwhm_fin < fwhm_ini:
            desc_ini = describe(label_ini, kind_ini, val_ini, fwhm_ini)
            desc_fin = describe(label_fin, kind_fin, val_fin, fwhm_fin)
            return (
                f"Invalid resolution configuration:\n\n"
                f"Target resolution ({desc_fin}) is HIGHER than initial resolution ({desc_ini}).\n\n"
                f"Spectral convolution can only degrade resolution to a broader value:\n"
                f"  • σ_fin must be ≥ σ_ini\n"
                f"  • FWHM_fin must be ≥ FWHM_ini\n"
                f"  • R_fin must be ≤ R_ini"
            )

        return None

    def _table_resolution_columns(self):
        """Resolution columns (sigma, FWHM, R) present in the Spectrum List, in Table mode."""
        if not self.radio_table_mode.isChecked():
            return []
        filename = self.pick_spectrum_list.text()
        if not filename or not os.path.isfile(filename):
            return []
        from saira.saira_wapper import read_input_table
        try:
            columns = read_input_table(filename).columns
        except Exception:
            return []
        return [c for c in ("sigma", "FWHM", "R") if c in columns]

    def _validate_inputs(self, check_paths=True):
        """
        Check the GUI state before a run (or a script export). Returns a list of
        (title, message) tuples; empty if everything is fine. With check_paths=False
        (script export) the spectra directory does not need to exist on this machine.
        """
        is_table_mode = self.radio_table_mode.isChecked()
        filename = self.pick_spectrum_list.text() if is_table_mode else None
        path_to_files = self.pick_spectra_dir.text()

        errors = []
        if is_table_mode and not filename:
            errors.append("Spectrum list file is required in Table mode.")
        if not path_to_files:
            errors.append("Spectra directory is required.")
        elif check_paths and not os.path.isdir(path_to_files):
            errors.append(f"Spectra directory not found: {path_to_files}")
        if self.combo_idx_defs.currentIndex() < 0:
            errors.append("Index definitions file is required.")
        if errors:
            return [("Missing Input", "\n".join(errors))]

        # Table mode: one z per spectrum from a CSV with file,redshift columns
        if self.chk_enable_redshift.isChecked() and is_table_mode:
            if check_paths or os.path.isfile(filename):
                z_error = self._validate_redshift_table(filename)
                if z_error:
                    return [("Invalid Spectrum List for Redshift Correction", z_error)]

        if self.chk_enable_resolution.isChecked():
            res_error = self._validate_resolution_settings()
            if res_error:
                return [("Invalid Resolution Parameters", res_error)]

        if self.opt_mask_regions.is_enabled():
            try:
                parse_mask_regions(self.opt_mask_regions.text())
            except ValueError as e:
                return [("Invalid Mask Regions", str(e))]
        return []

    def _build_saira_kwargs(self):
        """
        Keyword arguments for saira() reproducing the current GUI state. IndexDefs
        is the path of the index definitions file (a custom index selection is
        applied by the caller).
        """
        is_table_mode = self.radio_table_mode.isChecked()
        kwargs = {
            "filename": self.pick_spectrum_list.text() if is_table_mode else None,
            "path_to_files": self.pick_spectra_dir.text(),
            "file_extension": None if is_table_mode else self.combo_extension.currentText().strip(),
            "IndexDefs": self.combo_idx_defs.currentData(),
            "output_file": self.pick_output.text() or "measurements.csv",
            "do_resolution": self.chk_enable_resolution.isChecked(),
            "do_redshift": self.chk_enable_redshift.isChecked(),
        }

        # Resolution (only meaningful when "Enable Resolution Correction" is checked)
        if self.chk_enable_resolution.isChecked():
            for key, row in (("sigma_ini", self.opt_sigma_ini), ("sigma_fin", self.opt_sigma_fin),
                             ("FWHM_ini", self.opt_fwhm_ini), ("FWHM_fin", self.opt_fwhm_fin),
                             ("R_ini", self.opt_r_ini), ("R_fin", self.opt_r_fin)):
                if row.is_enabled():
                    kwargs[key] = row.value()

        # Redshift: in Table mode z comes from the 'redshift' column; auto-discover uses one z for all
        if self.chk_enable_redshift.isChecked() and not is_table_mode:
            kwargs["z"] = self.spin_z.value()

        # Error Estimation: mutually exclusive Monte Carlo / analytical / none
        if self.radio_err_montecarlo.isChecked():
            kwargs["simulate"] = self.spin_montecarlo_n.value()
        elif self.radio_err_analytical.isChecked():
            kwargs["error"] = True
        elif self.radio_err_propagation.isChecked():
            kwargs["error"] = True
            kwargs["error_method"] = "propagation"

        # Bad pixels (defaults omitted, so that exported scripts stay short)
        if not self.chk_use_flags.isChecked():
            kwargs["use_flags"] = False
        if self.opt_mask_regions.is_enabled() and self.opt_mask_regions.text():
            kwargs["mask_regions"] = parse_mask_regions(self.opt_mask_regions.text())
        if self.spin_bpr_thres.value() < 1.0:
            kwargs["bpr_thres"] = self.spin_bpr_thres.value()

        if self.chk_neg_to_zero.isChecked():
            kwargs["negative_Ew_to_zero"] = True

        if self.opt_a_to_mag.is_enabled():
            txt = self.opt_a_to_mag.text()
            if txt:
                kwargs["A_to_mag"] = [s.strip() for s in txt.split(",") if s.strip()]
        if self.opt_compute_idx.is_enabled():
            kwargs["compute_idx"] = self.opt_compute_idx.text()

        # Plots
        if self.opt_single_plots.is_enabled():
            kwargs["path_singleind_plots"] = self.opt_single_plots.text()
        if self.opt_all_plot.is_enabled():
            kwargs["AllIndicesPlot"] = self.opt_all_plot.text()
        if self.opt_all_plot_dir.is_enabled():
            kwargs["allindices_plot_path"] = self.opt_all_plot_dir.text() or "./"
        if self.opt_log_file.is_enabled():
            kwargs["print_log"] = self.opt_log_file.text()
        return kwargs

    def _on_run(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Running", "SAIRA is already running.")
            return

        problems = self._validate_inputs()
        if problems:
            title, message = problems[0]
            show = QMessageBox.warning if title == "Missing Input" else QMessageBox.critical
            show(self, title, message)
            return

        kwargs = self._build_saira_kwargs()
        index_defs = kwargs["IndexDefs"]

        # Resolve which indices to run: a manual "Select Indices…" choice takes
        # precedence; otherwise auto-exclude indices whose Line Limits fall
        # outside the batch's wavelength coverage, confirmed once for the run.
        from saira.saira_wapper import read_idx_defs, list_spectrum_files, get_spectra_wavelength_range, filter_idx_by_range

        if self.custom_idx_definitions is not None:
            final_idx_definitions = self.custom_idx_definitions
        else:
            try:
                base_idx_definitions = read_idx_defs(index_defs)
                files = list_spectrum_files(kwargs["filename"], kwargs["path_to_files"], kwargs["file_extension"])
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not read index definitions or spectra: {e}")
                return

            final_idx_definitions = base_idx_definitions
            wave_min, wave_max = get_spectra_wavelength_range(kwargs["path_to_files"], files)
            if wave_min is not None:
                in_range = filter_idx_by_range(base_idx_definitions, wave_min, wave_max)
                if not in_range.all():
                    excluded_names = [str(n) for n in base_idx_definitions['name'][~in_range]]
                    msg = (
                        f"The spectra in this batch cover {wave_min:.1f} - {wave_max:.1f} Å.\n\n"
                        f"{len(excluded_names)} of {len(base_idx_definitions)} indices have Line "
                        f"Limits outside this range and will be EXCLUDED from this run:\n\n"
                        + ", ".join(excluded_names) +
                        "\n\nUse \"Select Indices…\" beforehand if you want to override this."
                    )
                    reply = QMessageBox.question(
                        self, "Indices Out of Range", msg,
                        QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok
                    )
                    if reply != QMessageBox.Ok:
                        return
                    final_idx_definitions = base_idx_definitions[in_range]

        kwargs["IndexDefs"] = final_idx_definitions

        # Clear previous run
        self.log_console.clear_log()
        self.results_table.clear()
        self.results_table.setRowCount(0)
        self.results_table.setColumnCount(0)
        self.btn_export.setEnabled(False)
        self.btn_plot.setEnabled(False)
        self.result_df = None

        # Start worker
        self.progress.setVisible(True)
        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳  Running…")
        self.statusBar().showMessage("Running SAIRA…")

        self.worker = SairaWorker(kwargs)
        self.worker.log_signal.connect(self.log_console.append_log)
        self.worker.error_signal.connect(self._on_worker_error)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_error(self, tb):
        self.log_console.append_log(f"\n❌ ERROR:\n{tb}")

    def _on_worker_finished(self, result):
        self.progress.setVisible(False)
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶  Run SAIRA")

        if result is not None and isinstance(result, pd.DataFrame):
            self.result_df = result
            self._populate_table(result)
            self.btn_export.setEnabled(True)
            self.btn_plot.setEnabled(True)
            self.log_console.append_log("\n✅ SAIRA finished successfully.")
            self.statusBar().showMessage("Done — Results available in the preview table.")
        else:
            self.statusBar().showMessage("Run finished with errors. Check the log.")

    def _populate_table(self, df):
        """Fill QTableWidget from a pandas DataFrame."""
        self.results_table.clear()
        cols = list(df.columns)
        self.results_table.setColumnCount(len(cols))
        self.results_table.setHorizontalHeaderLabels(cols)
        self.results_table.setRowCount(len(df))

        for r, (_, row) in enumerate(df.iterrows()):
            for c, col in enumerate(cols):
                val = row[col]
                if isinstance(val, float):
                    text = f"{val:.6f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.results_table.setItem(r, c, item)

        self.results_table.resizeColumnsToContents()

    def _on_export_csv(self):
        if self.result_df is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results as CSV", "saira_results.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            self.result_df.to_csv(path, index=False)
            self.statusBar().showMessage(f"Results exported to {path}")

    def _on_plot_results(self):
        if self.result_df is None:
            return
        label = os.path.basename(self.pick_output.text()) or "Main"
        dlg = PlotDialog(self.result_df, parent=self, label=label)
        dlg.exec_()

    # -----------------------------------------------------------------
    # Save / Load Config
    # -----------------------------------------------------------------

    def _gather_config(self):
        """Collect all GUI settings into a dict."""
        cfg = {}
        cfg["input_mode"] = "table" if self.radio_table_mode.isChecked() else "extension"
        cfg["file_extension"] = self.combo_extension.currentText()
        cfg["spectrum_list"] = self.pick_spectrum_list.text()
        cfg["spectra_dir"] = self.pick_spectra_dir.text()
        cfg["idx_defs_index"] = self.combo_idx_defs.currentIndex()
        cfg["idx_defs_text"] = self.combo_idx_defs.currentText()
        cfg["idx_defs_path"] = self.combo_idx_defs.currentData()
        cfg["output_file"] = self.pick_output.text()

        # Resolution toggles
        cfg["enable_resolution"] = self.chk_enable_resolution.isChecked()
        for name in ("sigma_ini", "sigma_fin", "fwhm_ini", "fwhm_fin", "r_ini", "r_fin"):
            w = getattr(self, f"opt_{name}")
            cfg[name] = {"enabled": w.is_enabled(), "value": w.spinbox.value(),
                         "mode": w.combo_mode.currentText(), "file": w.file_path()}

        # Options
        cfg["enable_redshift"] = self.chk_enable_redshift.isChecked()
        cfg["z"] = {"value": self.spin_z.value()}

        if self.radio_err_montecarlo.isChecked():
            cfg["error_method"] = "montecarlo"
        elif self.radio_err_analytical.isChecked():
            cfg["error_method"] = "analytical"
        elif self.radio_err_propagation.isChecked():
            cfg["error_method"] = "propagation"
        else:
            cfg["error_method"] = "none"
        cfg["montecarlo_n"] = self.spin_montecarlo_n.value()

        cfg["use_flags"] = self.chk_use_flags.isChecked()
        cfg["mask_regions"] = {"enabled": self.opt_mask_regions.is_enabled(),
                               "value": self.opt_mask_regions.line_edit.text()}
        cfg["bpr_thres"] = self.spin_bpr_thres.value()

        cfg["neg_to_zero"] = self.chk_neg_to_zero.isChecked()

        cfg["a_to_mag"] = {"enabled": self.opt_a_to_mag.is_enabled(), "value": self.opt_a_to_mag.line_edit.text()}
        cfg["compute_idx"] = {"enabled": self.opt_compute_idx.is_enabled(), "value": self.opt_compute_idx.line_edit.text()}

        # Plots
        cfg["single_plots"] = {"enabled": self.opt_single_plots.is_enabled(), "value": self.opt_single_plots.line_edit.text()}
        cfg["all_plot"] = {"enabled": self.opt_all_plot.is_enabled(), "value": self.opt_all_plot.line_edit.text()}
        cfg["all_plot_dir"] = {"enabled": self.opt_all_plot_dir.is_enabled(), "value": self.opt_all_plot_dir.line_edit.text()}
        cfg["log_file"] = {"enabled": self.opt_log_file.is_enabled(), "value": self.opt_log_file.line_edit.text()}

        return cfg

    def _apply_config(self, cfg):
        """Restore GUI settings from a dict."""
        mode = cfg.get("input_mode", "table")
        if mode == "extension":
            self.radio_extension_mode.setChecked(True)
        else:
            self.radio_table_mode.setChecked(True)

        self.combo_extension.setCurrentText(cfg.get("file_extension", ".txt"))
        self.pick_spectrum_list.set_text(cfg.get("spectrum_list", ""))
        self.pick_spectra_dir.set_text(cfg.get("spectra_dir", ""))
        self.pick_output.set_text(cfg.get("output_file", "measurements.csv"))

        # Restore idx defs combo
        idx_path = cfg.get("idx_defs_path")
        if idx_path:
            found = False
            for i in range(self.combo_idx_defs.count()):
                if self.combo_idx_defs.itemData(i) == idx_path:
                    self.combo_idx_defs.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                name = cfg.get("idx_defs_text", os.path.basename(idx_path))
                self.combo_idx_defs.addItem(name, idx_path)
                self.combo_idx_defs.setCurrentIndex(self.combo_idx_defs.count() - 1)

        # Resolution
        self.chk_enable_resolution.setChecked(cfg.get("enable_resolution", False))
        for name in ("sigma_ini", "sigma_fin", "fwhm_ini", "fwhm_fin", "r_ini", "r_fin"):
            w = getattr(self, f"opt_{name}")
            d = cfg.get(name, {})
            w.set_state(d.get("enabled", False), d.get("value"), d.get("mode"), d.get("file"))

        # Options
        self.chk_enable_redshift.setChecked(cfg.get("enable_redshift", False))
        d = cfg.get("z", {})
        if d.get("value") is not None:
            self.spin_z.setValue(d["value"])

        if "error_method" in cfg:
            method = cfg.get("error_method", "none")
            montecarlo_n = cfg.get("montecarlo_n", 100)
        else:
            # Backward-compat with configs saved before the error-method radio buttons.
            old_simulate = cfg.get("simulate", {})
            if old_simulate.get("enabled"):
                method = "montecarlo"
            elif cfg.get("error", False):
                method = "analytical"
            else:
                method = "none"
            montecarlo_n = old_simulate.get("value", 100)
        self.radio_err_montecarlo.setChecked(method == "montecarlo")
        self.radio_err_analytical.setChecked(method == "analytical")
        self.radio_err_propagation.setChecked(method == "propagation")
        self.radio_err_none.setChecked(method == "none")
        self.spin_montecarlo_n.setValue(montecarlo_n)
        self.spin_montecarlo_n.setEnabled(method == "montecarlo")

        self.chk_use_flags.setChecked(cfg.get("use_flags", True))
        d = cfg.get("mask_regions", {})
        self.opt_mask_regions.set_state(d.get("enabled", False), d.get("value"))
        self.spin_bpr_thres.setValue(cfg.get("bpr_thres", 1.0))

        self.chk_neg_to_zero.setChecked(cfg.get("neg_to_zero", False))

        d = cfg.get("a_to_mag", {})
        self.opt_a_to_mag.set_state(d.get("enabled", False), d.get("value"))
        d = cfg.get("compute_idx", {})
        self.opt_compute_idx.set_state(d.get("enabled", False), d.get("value"))

        # Plots
        d = cfg.get("single_plots", {})
        self.opt_single_plots.set_state(d.get("enabled", False), d.get("value"))
        d = cfg.get("all_plot", {})
        self.opt_all_plot.set_state(d.get("enabled", False), d.get("value"))
        d = cfg.get("all_plot_dir", {})
        self.opt_all_plot_dir.set_state(d.get("enabled", False), d.get("value"))
        d = cfg.get("log_file", {})
        self.opt_log_file.set_state(d.get("enabled", False), d.get("value"))

    def _on_save_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save SAIRA Configuration", "saira_config.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if path:
            cfg = self._gather_config()
            with open(path, "w") as f:
                json.dump(cfg, f, indent=2, default=str)
            self.statusBar().showMessage(f"Configuration saved to {path}")

    def _on_load_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load SAIRA Configuration", "",
            "JSON Files (*.json);;All Files (*)"
        )
        if path:
            with open(path) as f:
                cfg = json.load(f)
            self._apply_config(cfg)
            self.statusBar().showMessage(f"Configuration loaded from {path}")

    # -----------------------------------------------------------------
    # Export / Load Script (.py)
    # -----------------------------------------------------------------

    def _on_export_script(self):
        """
        Write the current configuration as a standalone .py script that calls
        saira() with the same arguments as "Run SAIRA" — meant to be run by hand
        (e.g. on a cluster with no display) or loaded back with "Load Script".
        """
        # Local paths need not exist: the script may run on another machine.
        problems = self._validate_inputs(check_paths=False)
        if problems:
            title, message = problems[0]
            QMessageBox.warning(self, title, message)
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export SAIRA Script", "run_saira.py", "Python Files (*.py);;All Files (*)"
        )
        if not path:
            return

        kwargs = self._build_saira_kwargs()
        selected = None
        if self.custom_idx_definitions is not None:
            selected = [str(n) for n in self.custom_idx_definitions["name"]]
        try:
            with open(path, "w") as f:
                f.write(generate_script(kwargs, selected))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not write script: {e}")
            return

        self.statusBar().showMessage(f"Script exported to {path}")
        QMessageBox.information(
            self, "Script Exported",
            f"Saved to:\n{path}\n\nRun it with:\n    python {os.path.basename(path)}"
        )

    def _on_load_script(self):
        """
        Fill the GUI from a script that calls saira() (the inverse of "Export
        Script"). The script is executed with a recording saira() that only
        stores its arguments — same trust level as running the script yourself.
        """
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Running", "Wait for the current run to finish first.")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Load SAIRA Script", "", "Python Files (*.py);;All Files (*)"
        )
        if not path:
            return

        reply = QMessageBox.question(
            self, "Load Script",
            "This runs the script's own code to read its configuration (saira() itself is "
            "not executed) — the same as running it yourself. Only continue if you trust "
            f"'{os.path.basename(path)}'.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            kwargs, index_defs_path, selected, warnings = import_script(path)
        except ScriptImportError as e:
            QMessageBox.critical(self, "Could Not Load Script", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Could Not Load Script", f"Unexpected error: {e}")
            return

        cfg, map_warnings = self._kwargs_to_config(kwargs, index_defs_path)
        self._apply_config(cfg)
        warnings += map_warnings

        self.custom_idx_definitions = None
        self.lbl_idx_selection.setText("")
        if selected is not None and index_defs_path:
            from saira.saira_wapper import read_idx_defs
            try:
                all_defs = read_idx_defs(index_defs_path)
                self.custom_idx_definitions = all_defs[np.isin(all_defs["name"], selected)]
                self.lbl_idx_selection.setText(
                    f"Custom selection: {len(self.custom_idx_definitions)}/{len(all_defs)} indices active"
                )
            except Exception as e:
                warnings.append(f"Could not apply the index selection: {e}")

        self.statusBar().showMessage(f"Configuration imported from {path}")
        if warnings:
            QMessageBox.warning(
                self, "Imported With Warnings",
                "The script's configuration was imported, but:\n\n" + "\n\n".join(f"• {w}" for w in warnings)
            )
        else:
            QMessageBox.information(self, "Script Loaded", f"Configuration imported from:\n{path}")

    def _kwargs_to_config(self, kwargs, index_defs_path):
        """
        Translate the arguments of a saira() call into the GUI configuration
        dict used by _apply_config(). Returns (cfg, warnings).
        """
        warnings = []
        cfg = self._gather_config()   # start from the current state for anything not given
        known = set(_SCRIPT_ARGS)
        unknown = sorted(set(kwargs) - known)
        if unknown:
            warnings.append("Arguments not supported by the GUI were ignored: " + ", ".join(unknown))

        filename = kwargs.get("filename")
        cfg["input_mode"] = "table" if filename else "extension"
        cfg["spectrum_list"] = filename or ""
        if not filename:
            cfg["file_extension"] = kwargs.get("file_extension") or ".txt"
        cfg["spectra_dir"] = kwargs.get("path_to_files", "./")
        cfg["output_file"] = kwargs.get("output_file", "demo.txt")
        if index_defs_path:
            cfg["idx_defs_path"] = index_defs_path
            cfg["idx_defs_text"] = os.path.basename(index_defs_path)

        # Resolution
        cfg["enable_resolution"] = bool(kwargs.get("do_resolution", False))
        for key, name in (("sigma_ini", "sigma_ini"), ("sigma_fin", "sigma_fin"),
                          ("FWHM_ini", "fwhm_ini"), ("FWHM_fin", "fwhm_fin"),
                          ("R_ini", "r_ini"), ("R_fin", "r_fin")):
            value = kwargs.get(key)
            row = dict(cfg.get(name, {}), enabled=False)
            if value is None:
                pass
            elif isinstance(value, str):
                row.update(enabled=True, mode="File", file=value)
            elif np.ndim(value) == 0:
                row.update(enabled=True, mode="Value", value=float(value))
            else:
                warnings.append(f"{key} is given as an array in the script; save it to a "
                                f"file (wavelength, value) to use it in the GUI.")
            cfg[name] = row

        # Redshift
        cfg["enable_redshift"] = bool(kwargs.get("do_redshift", False))
        z = kwargs.get("z")
        if cfg["enable_redshift"]:
            if filename:
                if z is not None:
                    warnings.append("In Table mode the redshift of each spectrum is read from the "
                                    "'redshift' column of the Spectrum List; the z given in the script "
                                    "was ignored.")
            elif z is None or isinstance(z, str) or np.ndim(z) != 0:
                warnings.append("In Auto-discover mode a single z is applied to all spectra; the z of "
                                "the script is not a single number, so it was not imported.")
            else:
                cfg["z"] = {"value": float(z)}

        # Errors and other options
        if kwargs.get("simulate"):
            cfg["error_method"] = "montecarlo"
            cfg["montecarlo_n"] = int(kwargs["simulate"])
        elif kwargs.get("error_method") == "propagation":
            cfg["error_method"] = "propagation"
        elif kwargs.get("error"):
            cfg["error_method"] = "analytical"
        else:
            cfg["error_method"] = "none"
        cfg["neg_to_zero"] = bool(kwargs.get("negative_Ew_to_zero", False))
        cfg["use_flags"] = bool(kwargs.get("use_flags", True))
        regions = kwargs.get("mask_regions")
        try:
            cfg["mask_regions"] = {"enabled": bool(regions),
                                   "value": format_mask_regions(np.atleast_2d(regions)) if regions else ""}
        except Exception:
            cfg["mask_regions"] = {"enabled": False, "value": ""}
            warnings.append("mask_regions of the script could not be read; set them by hand.")
        cfg["bpr_thres"] = float(kwargs.get("bpr_thres", 1.0))
        a_to_mag = kwargs.get("A_to_mag")
        cfg["a_to_mag"] = {"enabled": bool(a_to_mag),
                           "value": ", ".join(a_to_mag) if a_to_mag else ""}
        compute_idx = kwargs.get("compute_idx")
        cfg["compute_idx"] = {"enabled": bool(compute_idx), "value": compute_idx or ""}

        # Plots and log
        for key, name in (("path_singleind_plots", "single_plots"), ("AllIndicesPlot", "all_plot"),
                          ("allindices_plot_path", "all_plot_dir"), ("print_log", "log_file")):
            value = kwargs.get(key)
            cfg[name] = {"enabled": value is not None, "value": value or ""}
        return cfg, warnings


# Arguments of saira() that the GUI can represent
_SCRIPT_ARGS = (
    "filename", "path_to_files", "file_extension", "IndexDefs", "output_file",
    "do_redshift", "z", "do_resolution", "sigma_ini", "FWHM_ini", "R_ini",
    "sigma_fin", "FWHM_fin", "R_fin", "simulate", "error", "negative_Ew_to_zero",
    "A_to_mag", "compute_idx", "path_singleind_plots", "AllIndicesPlot",
    "allindices_plot_path", "print_log", "use_flags", "mask_regions", "bpr_thres",
    "error_method",
)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("SAIRA")

    # Configure global font
    font = QFont("Inter", 10)
    app.setFont(font)

    # Set application icon
    logo_path = get_logo_path()
    if logo_path:
        app.setWindowIcon(QIcon(logo_path))

    # Splash screen
    splash = None
    if logo_path:
        pix = QPixmap(logo_path)
        if not pix.isNull():
            from PyQt5.QtWidgets import QSplashScreen
            splash_pix = pix.scaledToWidth(480, Qt.SmoothTransformation)
            splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
            splash.showMessage(
                "  SAIRA — Initializing…",
                Qt.AlignBottom | Qt.AlignLeft,
                QColor("#FFFFFF"),
            )
            splash.show()
            app.processEvents()

    window = MainWindow()
    if splash:
        splash.finish(window)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
