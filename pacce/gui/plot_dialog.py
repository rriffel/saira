"""
plot_dialog.py — Scatter-plot dialog for the Results Preview table.

Lets the user plot any column, or an expression combining columns
(e.g. `Mg2 - Fe5270`), against another, and save the resulting figure.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QFileDialog, QMessageBox
)

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from .constants import STYLESHEET, ACCENT, MUTED


class PlotDialog(QDialog):
    """Pick X/Y columns (or expressions) from the results table and plot them."""

    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Results")
        self.resize(780, 660)
        self.setStyleSheet(STYLESHEET)

        self.df = df
        self._build_ui()

    # -----------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Pick an index name, or type an expression combining indices "
            "(e.g. Mg2 - Fe5270, or log10(Hbeta)). For names with dots or "
            "dashes, wrap them in backticks, e.g. `NaI1.14` / Mg2. Error "
            "columns (e_<name>) aren't listed — check \"Error bars\" to plot "
            "them as error bars instead."
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
    def _eval_expr(self, expr):
        expr = expr.strip()
        if not expr:
            raise ValueError("Empty expression")
        if expr in self.df.columns:
            return self.df[expr]
        return self.df.eval(expr)

    def _get_error(self, expr):
        """Return the e_<name> column for a plain index name, or None."""
        expr = expr.strip()
        err_col = f"e_{expr}"
        if expr in self.df.columns and err_col in self.df.columns:
            return self.df[err_col]
        return None

    def _on_plot(self):
        x_expr = self.combo_x.currentText()
        y_expr = self.combo_y.currentText()
        try:
            x = self._eval_expr(x_expr)
            y = self._eval_expr(y_expr)
        except Exception as e:
            QMessageBox.warning(self, "Invalid Expression", f"Could not evaluate: {e}")
            return

        xerr = yerr = None
        if self.chk_error_bars.isChecked():
            xerr = self._get_error(x_expr)
            yerr = self._get_error(y_expr)
            if xerr is None and yerr is None:
                QMessageBox.information(
                    self, "No error columns found",
                    f"No e_{x_expr} or e_{y_expr} column was found, so no error bars can be "
                    "drawn. Error bars only work when X/Y is exactly an index name, not an "
                    "expression — plotting without them."
                )

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if xerr is not None or yerr is not None:
            ax.errorbar(
                x, y, xerr=xerr, yerr=yerr, fmt='o', color=ACCENT, ecolor=ACCENT,
                elinewidth=1, capsize=3, markeredgecolor='black', markeredgewidth=0.5,
                markersize=6,
            )
        else:
            ax.scatter(x, y, color=ACCENT, edgecolor='black', linewidth=0.5, s=40)
        ax.set_xlabel(x_expr)
        ax.set_ylabel(y_expr)
        ax.set_title(f"{y_expr} vs {x_expr}")
        ax.grid(alpha=0.3)
        self.figure.tight_layout()
        self.canvas.draw()

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
