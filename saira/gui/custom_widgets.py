"""
custom_widgets.py — Reusable GUI widgets for the SAIRA interface.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QCheckBox, QDoubleSpinBox,
    QSpinBox, QTextEdit, QSizePolicy, QComboBox
)
from PyQt5.QtCore import Qt


class FilePickerRow(QWidget):
    """
    A row widget with Label + QLineEdit + Browse button.
    Used for selecting files or directories.
    """

    def __init__(self, label_text, placeholder="", is_directory=False,
                 file_filter="All Files (*)", parent=None):
        super().__init__(parent)
        self.is_directory = is_directory
        self.file_filter = file_filter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = QLabel(label_text)
        self.label.setFixedWidth(140)
        self.label.setStyleSheet("font-weight: 500;")
        layout.addWidget(self.label)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.line_edit, 1)

        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setFixedWidth(90)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._on_browse)
        layout.addWidget(self.btn_browse)

    def _on_browse(self):
        if self.is_directory:
            path = QFileDialog.getExistingDirectory(
                self, f"Select {self.label.text().strip(':')}", self.line_edit.text()
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, f"Select {self.label.text().strip(':')}", self.line_edit.text(),
                self.file_filter
            )
        if path:
            self.line_edit.setText(path)

    def text(self):
        return self.line_edit.text().strip()

    def set_text(self, value):
        self.line_edit.setText(value)


class ToggleDoubleRow(QWidget):
    """
    A checkbox-controlled row with a QDoubleSpinBox.
    The spin box is disabled when the checkbox is unchecked.
    """

    def __init__(self, label_text, suffix="", min_val=0.0, max_val=999999.0,
                 decimals=2, default_val=0.0, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.checkbox = QCheckBox(label_text)
        self.checkbox.setFixedWidth(160)
        self.checkbox.setChecked(False)
        self.checkbox.toggled.connect(self._on_toggle)
        layout.addWidget(self.checkbox)

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setSuffix(f"  {suffix}" if suffix else "")
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setDecimals(decimals)
        self.spinbox.setValue(default_val)
        self.spinbox.setEnabled(False)
        self.spinbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.spinbox, 1)

    def _on_toggle(self, checked):
        self.spinbox.setEnabled(checked)

    def is_enabled(self):
        return self.checkbox.isChecked()

    def value(self):
        return self.spinbox.value() if self.checkbox.isChecked() else None

    def set_state(self, enabled, value=None):
        self.checkbox.setChecked(enabled)
        if value is not None:
            self.spinbox.setValue(value)


class ToggleValueFileRow(QWidget):
    """
    A checkbox-controlled row that takes either a single number (QDoubleSpinBox)
    or a file (QLineEdit + Browse button), selected with a Value/File combo box.
    Everything is disabled when the checkbox is unchecked.
    """

    MODES = ("Value", "File")

    def __init__(self, label_text, suffix="", min_val=0.0, max_val=999999.0,
                 decimals=2, default_val=0.0, file_tooltip="", parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.checkbox = QCheckBox(label_text)
        self.checkbox.setFixedWidth(160)
        self.checkbox.setChecked(False)
        self.checkbox.toggled.connect(self._update_enabled)
        layout.addWidget(self.checkbox)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(self.MODES)
        self.combo_mode.setFixedWidth(80)
        self.combo_mode.setToolTip(file_tooltip)
        self.combo_mode.currentIndexChanged.connect(self._update_enabled)
        layout.addWidget(self.combo_mode)

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setSuffix(f"  {suffix}" if suffix else "")
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setDecimals(decimals)
        self.spinbox.setValue(default_val)
        self.spinbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.spinbox, 1)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Path to file…")
        self.line_edit.setToolTip(file_tooltip)
        self.line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.line_edit, 1)

        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setFixedWidth(90)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._on_browse)
        layout.addWidget(self.btn_browse)

        self._update_enabled()

    def _update_enabled(self, *_):
        checked = self.checkbox.isChecked()
        file_mode = self.is_file()
        self.combo_mode.setEnabled(checked)
        self.spinbox.setVisible(not file_mode)
        self.line_edit.setVisible(file_mode)
        self.btn_browse.setVisible(file_mode)
        self.spinbox.setEnabled(checked)
        self.line_edit.setEnabled(checked)
        self.btn_browse.setEnabled(checked)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Select {self.checkbox.text().strip()} file", self.line_edit.text(),
            "Data Files (*.dat *.txt *.csv *.tsv);;All Files (*)"
        )
        if path:
            self.line_edit.setText(path)

    def is_enabled(self):
        return self.checkbox.isChecked()

    def is_file(self):
        return self.combo_mode.currentText() == "File"

    def file_path(self):
        return self.line_edit.text().strip()

    def value(self):
        """The number or the file path, or None if the row is unchecked."""
        if not self.checkbox.isChecked():
            return None
        return self.file_path() if self.is_file() else self.spinbox.value()

    def set_state(self, enabled, value=None, mode=None, path=None):
        if mode in self.MODES:
            self.combo_mode.setCurrentText(mode)
        if value is not None:
            self.spinbox.setValue(value)
        if path is not None:
            self.line_edit.setText(path)
        self.checkbox.setChecked(enabled)
        self._update_enabled()


class ToggleIntRow(QWidget):
    """
    A checkbox-controlled row with a QSpinBox.
    The spin box is disabled when the checkbox is unchecked.
    """

    def __init__(self, label_text, suffix="", min_val=1, max_val=100000,
                 default_val=100, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.checkbox = QCheckBox(label_text)
        self.checkbox.setFixedWidth(160)
        self.checkbox.setChecked(False)
        self.checkbox.toggled.connect(self._on_toggle)
        layout.addWidget(self.checkbox)

        self.spinbox = QSpinBox()
        self.spinbox.setSuffix(f"  {suffix}" if suffix else "")
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setValue(default_val)
        self.spinbox.setEnabled(False)
        self.spinbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.spinbox, 1)

    def _on_toggle(self, checked):
        self.spinbox.setEnabled(checked)

    def is_enabled(self):
        return self.checkbox.isChecked()

    def value(self):
        return self.spinbox.value() if self.checkbox.isChecked() else None

    def set_state(self, enabled, value=None):
        self.checkbox.setChecked(enabled)
        if value is not None:
            self.spinbox.setValue(value)


class ToggleTextRow(QWidget):
    """
    A checkbox-controlled row with a QLineEdit.
    The line edit is disabled when the checkbox is unchecked.
    """

    def __init__(self, label_text, placeholder="", parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.checkbox = QCheckBox(label_text)
        self.checkbox.setFixedWidth(160)
        self.checkbox.setChecked(False)
        self.checkbox.toggled.connect(self._on_toggle)
        layout.addWidget(self.checkbox)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setEnabled(False)
        self.line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.line_edit, 1)

    def _on_toggle(self, checked):
        self.line_edit.setEnabled(checked)

    def is_enabled(self):
        return self.checkbox.isChecked()

    def text(self):
        return self.line_edit.text().strip() if self.checkbox.isChecked() else None

    def set_state(self, enabled, value=None):
        self.checkbox.setChecked(enabled)
        if value is not None:
            self.line_edit.setText(value)


class ToggleFilePickerRow(QWidget):
    """
    A checkbox-controlled row with QLineEdit + Browse button.
    Everything is disabled when the checkbox is unchecked.
    """

    def __init__(self, label_text, placeholder="", is_directory=False,
                 file_filter="All Files (*)", parent=None):
        super().__init__(parent)
        self.is_directory = is_directory
        self.file_filter = file_filter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.checkbox = QCheckBox(label_text)
        self.checkbox.setFixedWidth(160)
        self.checkbox.setChecked(False)
        self.checkbox.toggled.connect(self._on_toggle)
        layout.addWidget(self.checkbox)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setEnabled(False)
        self.line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.line_edit, 1)

        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setFixedWidth(90)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setEnabled(False)
        self.btn_browse.clicked.connect(self._on_browse)
        layout.addWidget(self.btn_browse)

    def _on_toggle(self, checked):
        self.line_edit.setEnabled(checked)
        self.btn_browse.setEnabled(checked)

    def _on_browse(self):
        if self.is_directory:
            path = QFileDialog.getExistingDirectory(
                self, f"Select {self.checkbox.text().strip(':')}", self.line_edit.text()
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, f"Select {self.checkbox.text().strip(':')}", self.line_edit.text(),
                self.file_filter
            )
        if path:
            self.line_edit.setText(path)

    def is_enabled(self):
        return self.checkbox.isChecked()

    def text(self):
        return self.line_edit.text().strip() if self.checkbox.isChecked() else None

    def set_state(self, enabled, value=None):
        self.checkbox.setChecked(enabled)
        if value is not None:
            self.line_edit.setText(value)


class LogConsole(QTextEdit):
    """
    A styled, read-only text console for displaying log output.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Log output will appear here…")
        self.setMinimumHeight(120)

    def append_log(self, text):
        """Append text and scroll to bottom."""
        self.append(text)
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        self.clear()
