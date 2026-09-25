"""
plot_dialog.py — Scatter-plot dialog for the Results Preview table.

Lets the user plot any column, or an expression combining columns
(e.g. `Mg2 - Fe5270`), against another, save the resulting figure, and
overplot a second results file (e.g. another SAIRA run or a model grid)
generated the same way — which may or may not include error columns.
"""

import os

import pandas as pd

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QFileDialog, QMessageBox
)

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from .constants import STYLESHEET, ACCENT, MUTED, DANGER_COLOR


class PlotDialog(QDialog):
    """Pick X/Y columns (or expressions) from the results table and plot them."""

    def __init__(self, df, parent=None, label="Main"):
        super().__init__(parent)
        self.setWindowTitle("Plot Results")
        self.resize(780, 700)
        self.setStyleSheet(STYLESHEET)

        self.df = df
        self.label = label
        self.df2 = None
        self.df2_label = None
        self._build_ui()

    # -----------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Pick an index name, or type an expression combining indices "
            "(e.g. Mg2 - Fe5270, or log10(Hbeta)). For names with dots or "
            "dashes, wrap them in backticks, e.g. `NaI1.14` / Mg2. Error "
            "columns (e_<name>) aren't listed — check \"Error bars\" to plot "
            "them as error bars instead. Use \"Overplot File…\" to compare "
            "against another results CSV generated the same way; pick its "
            "own X/Y below — it doesn't need error columns, and SAIRA "
            "detects whether it has any."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        layout.addWidget(info)

        # Only plot-able index columns are offered — the e_<name> error
        # columns are for error bars, not variables to plot on their own.
        cols = [c for c in self.df.columns if c.lower() != 'file' and not c.startswith('e_')]

        form = QHBoxLayout()
        form.addWidget(QLabel("X:"))
        self.combo_x = QComboBox()
        self.combo_x.setEditable(True)
        self.combo_x.addItems(cols)
        form.addWidget(self.combo_x, 1)

        form.addWidget(QLabel("Y:"))
        self.combo_y = QComboBox()
        self.combo_y.setEditable(True)
        self.combo_y.addItems(cols)
        form.addWidget(self.combo_y, 1)

        self.chk_error_bars = QCheckBox("Error bars")
        self.chk_error_bars.setToolTip(
            "Uses the e_<name> column as the error for X/Y, when X or Y is "
            "exactly an index name (not an expression)."
        )
        self.chk_error_bars.toggled.connect(lambda _: self._on_plot())
        form.addWidget(self.chk_error_bars)

        btn_plot = QPushButton("Plot")
        btn_plot.clicked.connect(self._on_plot)
        form.addWidget(btn_plot)

        layout.addLayout(form)

        overlay_row = QHBoxLayout()
        btn_overlay = QPushButton("Overplot File…")
        btn_overlay.setToolTip(
            "Load another results CSV (generated the same way) and overplot it. "
            "It doesn't need to have the e_<name> error columns."
        )
        btn_overlay.clicked.connect(self._on_load_overlay)
        overlay_row.addWidget(btn_overlay)

        self.btn_clear_overlay = QPushButton("Clear Overlay")
        self.btn_clear_overlay.setEnabled(False)
        self.btn_clear_overlay.clicked.connect(self._on_clear_overlay)
        overlay_row.addWidget(self.btn_clear_overlay)

        self.lbl_overlay = QLabel("")
        self.lbl_overlay.setStyleSheet(f"color: {DANGER_COLOR}; font-size: 12px;")
        overlay_row.addWidget(self.lbl_overlay)
        overlay_row.addStretch()
        layout.addLayout(overlay_row)

        overlay_cols_row = QHBoxLayout()
        overlay_cols_row.addWidget(QLabel("Overlay X:"))
        self.combo_x2 = QComboBox()
        self.combo_x2.setEditable(True)
        self.combo_x2.setEnabled(False)
        overlay_cols_row.addWidget(self.combo_x2, 1)

        overlay_cols_row.addWidget(QLabel("Overlay Y:"))
        self.combo_y2 = QComboBox()
        self.combo_y2.setEditable(True)
        self.combo_y2.setEnabled(False)
        overlay_cols_row.addWidget(self.combo_y2, 1)
        layout.addLayout(overlay_cols_row)

        self.figure = Figure(figsize=(6, 5))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton("Save Plot As…")
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)
        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("background-color: #94A3B8;")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        # Plot something on open, if there are at least two indices available.
        if len(cols) >= 2:
            self.combo_x.setCurrentText(cols[0])
            self.combo_y.setCurrentText(cols[1])
            self._on_plot()

    # -----------------------------------------------------------------
    def _eval_expr(self, expr, df):
        expr = expr.strip()
        if not expr:
            raise ValueError("Empty expression")
        if expr in df.columns:
            return df[expr]
        return df.eval(expr)

    def _get_error(self, expr, df):
        """Return the e_<name> column for a plain index name, or None if absent."""
        expr = expr.strip()
        err_col = f"e_{expr}"
        if expr in df.columns and err_col in df.columns:
            return df[err_col]
        return None

    def _has_error_columns(self, df):
        """True if a dataset provides any e_<name> error column at all."""
        return any(c.startswith('e_') for c in df.columns)

    def _plot_dataset(self, ax, df, x_expr, y_expr, color, marker, label):
        """Evaluate X/Y (and errors, if requested) for one dataset and draw it."""
        x = self._eval_expr(x_expr, df)
        y = self._eval_expr(y_expr, df)

        xerr = yerr = None
        if self.chk_error_bars.isChecked():
            xerr = self._get_error(x_expr, df)
            yerr = self._get_error(y_expr, df)

        if xerr is not None or yerr is not None:
            ax.errorbar(
                x, y, xerr=xerr, yerr=yerr, fmt=marker, color=color, ecolor=color,
                elinewidth=1, capsize=3, markeredgecolor='black', markeredgewidth=0.5,
                markersize=6, label=label,
            )
        else:
            ax.scatter(x, y, color=color, marker=marker, edgecolor='black',
                       linewidth=0.5, s=40, label=label)
        return xerr, yerr

    def _on_plot(self):
        x_expr = self.combo_x.currentText()
        y_expr = self.combo_y.currentText()

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        try:
            main_label = self.label if self.df2 is not None else None
            xerr, yerr = self._plot_dataset(
                ax, self.df, x_expr, y_expr, ACCENT, 'o', main_label
            )
        except Exception as e:
            QMessageBox.warning(self, "Invalid Expression", f"Could not evaluate: {e}")
            return

        overlay_xerr = overlay_yerr = None
        if self.df2 is not None:
            x2_expr = self.combo_x2.currentText()
            y2_expr = self.combo_y2.currentText()
            overlay_label = self.df2_label
            if x2_expr != x_expr or y2_expr != y_expr:
                overlay_label = f"{self.df2_label} ({x2_expr} vs {y2_expr})"
            try:
                overlay_xerr, overlay_yerr = self._plot_dataset(
                    ax, self.df2, x2_expr, y2_expr, DANGER_COLOR, 's', overlay_label
                )
            except Exception as e:
                QMessageBox.warning(
                    self, "Invalid Expression",
                    f"Could not evaluate on the overlay file ({self.df2_label}): {e}\n\n"
                    "Showing the main dataset only."
                )

        if self.chk_error_bars.isChecked():
            found_any = any(v is not None for v in (xerr, yerr, overlay_xerr, overlay_yerr))
            if not found_any:
                QMessageBox.information(
                    self, "No error columns found",
                    f"No e_{x_expr} or e_{y_expr} column was found in any dataset, so no "
                    "error bars can be drawn. Error bars only work when X/Y is exactly an "
                    "index name, not an expression — plotting without them."
                )

        ax.set_xlabel(x_expr)
        ax.set_ylabel(y_expr)
        ax.set_title(f"{y_expr} vs {x_expr}")
        ax.grid(alpha=0.3)
        if self.df2 is not None:
            ax.legend()
        self.figure.tight_layout()
        self.canvas.draw()

    def _on_load_overlay(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Results File to Overplot", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        try:
            df2 = pd.read_csv(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read {path}: {e}")
            return

        self.df2 = df2
        self.df2_label = os.path.basename(path)
        self.btn_clear_overlay.setEnabled(True)

        # Same-style column picker as the main file, restricted to this file's own columns.
        overlay_cols = [c for c in df2.columns if c.lower() != 'file' and not c.startswith('e_')]
        self.combo_x2.clear()
        self.combo_y2.clear()
        self.combo_x2.addItems(overlay_cols)
        self.combo_y2.addItems(overlay_cols)
        self.combo_x2.setEnabled(bool(overlay_cols))
        self.combo_y2.setEnabled(bool(overlay_cols))

        # Default to the same columns as the main plot when the overlay has them too.
        x_default = self.combo_x.currentText()
        y_default = self.combo_y.currentText()
        if x_default not in overlay_cols and overlay_cols:
            x_default = overlay_cols[0]
        if y_default not in overlay_cols and overlay_cols:
            y_default = overlay_cols[1] if len(overlay_cols) > 1 else overlay_cols[0]
        self.combo_x2.setCurrentText(x_default)
        self.combo_y2.setCurrentText(y_default)

        # Auto-detect whether this file has any e_<name> error columns at all.
        err_note = "error columns detected" if self._has_error_columns(df2) else "no error columns"
        self.lbl_overlay.setText(f"Overlaying: {self.df2_label} ({err_note})")
        self._on_plot()

    def _on_clear_overlay(self):
        self.df2 = None
        self.df2_label = None
        self.btn_clear_overlay.setEnabled(False)
        self.lbl_overlay.setText("")
        self.combo_x2.clear()
        self.combo_y2.clear()
        self.combo_x2.setEnabled(False)
        self.combo_y2.setEnabled(False)
        self._on_plot()

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "plot.png",
            "PNG Image (*.png);;PDF (*.pdf);;SVG (*.svg);;All Files (*)"
        )
        if path:
            try:
                self.figure.savefig(path, dpi=150)
                QMessageBox.information(self, "Saved", f"Plot saved to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save plot: {e}")
