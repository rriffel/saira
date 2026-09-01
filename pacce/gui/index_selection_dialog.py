"""
index_selection_dialog.py — Dialog to check/uncheck individual indices from an
index-definitions file before a run.

Indices whose Line Limits fall outside the spectra wavelength range that was
scanned for the current run start unchecked; trying to check one back on
shows a warning explaining why.
"""

import numpy as np

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QFileDialog, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from .constants import STYLESHEET, ACCENT, MUTED, DANGER_COLOR


class IndexSelectionDialog(QDialog):
    """Let the user pick which indices (rows of an .ind file) to include in a run."""

    def __init__(self, idx_definitions, wave_min=None, wave_max=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Indices")
        self.resize(640, 560)
        self.setStyleSheet(STYLESHEET)

        self.idx_definitions = idx_definitions
        self.wave_min = wave_min
        self.wave_max = wave_max

        if wave_min is not None and wave_max is not None:
            from pacce.pacce_wapper import filter_idx_by_range
            self.in_range_mask = filter_idx_by_range(idx_definitions, wave_min, wave_max)
        else:
            self.in_range_mask = np.ones(len(idx_definitions), dtype=bool)

        self._build_ui()
        self._populate_table()

    # -----------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)

        if self.wave_min is not None:
            info = QLabel(
                f"Spectra wavelength coverage: {self.wave_min:.1f} - {self.wave_max:.1f} Å. "
                f"Indices whose Line Limits fall outside this range are unchecked by default."
            )
        else:
            info = QLabel("Check or uncheck the indices you want to include in this run.")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", "Name", "Line Limits (Å)", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        self.lbl_summary = QLabel()
        self.lbl_summary.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.lbl_summary)

        btn_row = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none = QPushButton("Deselect All")
        btn_none.clicked.connect(lambda: self._set_all(False))
        btn_save = QPushButton("Save Selection As…")
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        btn_row.addWidget(btn_save)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        ok_row = QHBoxLayout()
        ok_row.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #94A3B8;")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Apply")
        btn_ok.clicked.connect(self.accept)
        ok_row.addWidget(btn_cancel)
        ok_row.addWidget(btn_ok)
        layout.addLayout(ok_row)

    def _populate_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.idx_definitions))
        for row, line in enumerate(self.idx_definitions):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checked = bool(self.in_range_mask[row])
            chk_item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            self.table.setItem(row, 0, chk_item)

            name_item = QTableWidgetItem(str(line['name']))
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 1, name_item)

            limits = f"{line['defs'][0]:.2f} - {line['defs'][1]:.2f}"
            limits_item = QTableWidgetItem(limits)
            limits_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 2, limits_item)

            status = "In range" if self.in_range_mask[row] else "Out of range"
            status_item = QTableWidgetItem(status)
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if not self.in_range_mask[row]:
                status_item.setForeground(QColor(DANGER_COLOR))
            self.table.setItem(row, 3, status_item)
        self.table.blockSignals(False)
        self.table.setColumnWidth(0, 28)
        self.table.resizeColumnsToContents()
        self._update_summary()

    # -----------------------------------------------------------------
    def _on_item_changed(self, item):
        if item.column() != 0:
            return
        row = item.row()
        if item.checkState() == Qt.Checked and not self.in_range_mask[row]:
            name = self.idx_definitions[row]['name']
            limits = self.idx_definitions[row]['defs']
            QMessageBox.warning(
                self, "Index out of range",
                f"'{name}' (Line Limits {limits[0]:.2f}-{limits[1]:.2f} Å) falls outside "
                f"the spectra wavelength coverage ({self.wave_min:.1f}-{self.wave_max:.1f} Å).\n\n"
                "It has been kept checked at your request, but it will likely fail or "
                "produce unreliable measurements."
            )
        self._update_summary()

    def _set_all(self, checked):
        self.table.blockSignals(True)
        state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(state)
        self.table.blockSignals(False)
        self._update_summary()
        if checked:
            out_names = [
                str(self.idx_definitions[i]['name'])
                for i in range(len(self.in_range_mask)) if not self.in_range_mask[i]
            ]
            if out_names:
                QMessageBox.warning(
                    self, "Indices out of range",
                    "The following indices are outside the spectra wavelength range and "
                    "were included anyway because you selected all:\n\n" + ", ".join(out_names)
                )

    def _update_summary(self):
        mask = self.get_selected_mask()
        n_sel = int(mask.sum())
        n_total = len(mask)
        n_excluded_range = int((~self.in_range_mask).sum())
        self.lbl_summary.setText(
            f"{n_sel} of {n_total} indices selected ({n_excluded_range} out of spectra range)"
        )

    # -----------------------------------------------------------------
    def get_selected_mask(self):
        mask = np.zeros(self.table.rowCount(), dtype=bool)
        for row in range(self.table.rowCount()):
            mask[row] = self.table.item(row, 0).checkState() == Qt.Checked
        return mask

    def get_filtered_definitions(self):
        return self.idx_definitions[self.get_selected_mask()]

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Index Selection", "custom_defs.ind",
            "Index Files (*.ind);;All Files (*)"
        )
        if path:
            from pacce.pacce_wapper import write_idx_defs
            write_idx_defs(self.idx_definitions, path, self.get_selected_mask())
            QMessageBox.information(self, "Saved", f"Selection saved to {path}")
