import re
import sys
import os
import json
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QCheckBox, QListWidget, QListWidgetItem,
    QTextEdit, QGroupBox, QComboBox, QSizePolicy, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor

SETTINGS_FILE = "translator_settings.json"

LANG_LINE_RE = re.compile(r'^\s{2}[A-Z]{2,6}\s')


def count_translate_dirs(directory: str) -> int:
    base = Path(directory).resolve()
    count = 0
    for d in base.rglob("Translate"):
        if not d.is_dir():
            continue
        current = d
        is_b41 = False
        while current != current.parent:
            if current.name.lower() == "mods":
                is_b41 = len(d.relative_to(current).parts) == 5
                break
            current = current.parent
        if not is_b41:
            count += 1
    return count


class TranslationThread(QThread):
    output_signal   = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()

    def __init__(self, base_dir, directory, source_lang, selected_languages, overwrite):
        super().__init__()
        self.base_dir           = base_dir
        self.directory          = directory
        self.source_lang        = source_lang
        self.selected_languages = selected_languages
        self.overwrite          = overwrite

    def run(self):
        python_exec = "python" if getattr(sys, 'frozen', False) else sys.executable
        translate   = os.path.join(self.base_dir, "translate.py")

        command = [python_exec, translate, self.directory]
        if self.source_lang and self.source_lang != "EN":
            command += ["-source", self.source_lang]
        if self.overwrite:
            command.append("-overwrite")
        if self.selected_languages:
            command += ["-languages"] + self.selected_languages

        completed = 0
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW,
                bufsize=1,
                universal_newlines=True,
            )

            for line in iter(process.stdout.readline, ""):
                stripped = line.rstrip()
                self.output_signal.emit(stripped)
                if LANG_LINE_RE.match(stripped):
                    completed += 1
                    self.progress_signal.emit(completed)

            stderr_out = process.stderr.read()
            if stderr_out:
                self.output_signal.emit(f"[!] {stderr_out.strip()}")

            process.stdout.close()
            process.stderr.close()
            process.wait()
        finally:
            self.finished_signal.emit()


class TranslatorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PZ Translation Tool")
        self.setMinimumSize(600, 640)

        self.base_dir  = self._resolve_base_dir()
        self.lang_info = self._load_lang_info()
        self._thread   = None
        self._progress_total = 0

        self._build_ui()
        self._load_settings()

    def _resolve_base_dir(self) -> str:
        exe_dir    = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for candidate in [
            exe_dir    and os.path.join(exe_dir,    "pz-translator"),
            os.path.join(script_dir, "pz-translator"),
            script_dir,
        ]:
            if candidate and os.path.exists(candidate):
                return candidate
        return script_dir

    def _load_lang_info(self) -> dict:
        path = os.path.join(self.base_dir, "LanguagesInfo_b42.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        dir_group  = QGroupBox("Target Directory")
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("No directory selected")
        self.dir_label.setWordWrap(True)
        self.dir_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse)
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(browse_btn)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        opts_group  = QGroupBox("Options")
        opts_layout = QVBoxLayout()

        self.overwrite_check = QCheckBox("Overwrite existing translated keys (default: skip existing)")
        opts_layout.addWidget(self.overwrite_check)

        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Source language:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(sorted(self.lang_info.keys()))
        self.source_combo.setCurrentText("EN")
        self.source_combo.setFixedWidth(80)
        src_row.addWidget(self.source_combo)
        src_row.addStretch()
        opts_layout.addLayout(src_row)

        opts_group.setLayout(opts_layout)
        layout.addWidget(opts_group)

        lang_group  = QGroupBox("Target Languages  (none selected = all languages)")
        lang_layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        select_all_btn   = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn.clicked.connect(self._deselect_all)
        btn_row.addWidget(select_all_btn)
        btn_row.addWidget(deselect_all_btn)
        btn_row.addStretch()
        lang_layout.addLayout(btn_row)

        self.lang_list = QListWidget()
        self.lang_list.setSelectionMode(QListWidget.NoSelection)
        for code, info in sorted(self.lang_info.items()):
            if code == "EN":
                continue
            item = QListWidgetItem(f"{code}  –  {info.get('text', '')}")
            item.setData(Qt.UserRole, code)
            item.setCheckState(Qt.Unchecked)
            self.lang_list.addItem(item)

        lang_layout.addWidget(self.lang_list)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group, stretch=1)

        self.start_btn = QPushButton("▶  Start Translation")
        self.start_btn.setFixedHeight(36)
        self.start_btn.clicked.connect(self._run)
        layout.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        log_group  = QGroupBox("Output Log")
        log_layout = QVBoxLayout()
        clear_btn  = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Courier New", 9))
        self.log.setLineWrapMode(QTextEdit.NoWrap)
        clear_btn.clicked.connect(self.log.clear)
        log_layout.addWidget(clear_btn)
        log_layout.addWidget(self.log)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group, stretch=1)

        quit_btn = QPushButton("Quit")
        quit_btn.setFixedHeight(30)
        quit_btn.clicked.connect(self.close)
        layout.addWidget(quit_btn)

        self.setLayout(layout)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.dir_label.setText(path)
            self._save_settings()

    def _select_all(self):
        for i in range(self.lang_list.count()):
            self.lang_list.item(i).setCheckState(Qt.Checked)

    def _deselect_all(self):
        for i in range(self.lang_list.count()):
            self.lang_list.item(i).setCheckState(Qt.Unchecked)

    def _append_log(self, text: str):
        cursor = self.log.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + "\n")
        self.log.setTextCursor(cursor)
        self.log.ensureCursorVisible()

    def _run(self):
        directory = self.dir_label.text()
        if directory == "No directory selected":
            self._append_log("[!] No directory selected.")
            return

        selected = [
            self.lang_list.item(i).data(Qt.UserRole)
            for i in range(self.lang_list.count())
            if self.lang_list.item(i).checkState() == Qt.Checked
        ]

        lang_count = len(selected) if selected else len([
            k for k in self.lang_info if k != self.source_combo.currentText()
        ])
        folder_count       = count_translate_dirs(directory)
        self._progress_total = lang_count * folder_count

        self.start_btn.setEnabled(False)
        self.start_btn.setText("Translating…")

        self.progress_bar.setRange(0, max(self._progress_total, 1))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"0 / {self._progress_total} languages")
        self.progress_bar.setVisible(True)

        self._thread = TranslationThread(
            base_dir           = self.base_dir,
            directory          = directory,
            source_lang        = self.source_combo.currentText(),
            selected_languages = selected,
            overwrite          = self.overwrite_check.isChecked(),
        )
        self._thread.output_signal.connect(self._append_log)
        self._thread.progress_signal.connect(self._on_progress)
        self._thread.finished_signal.connect(self._done)
        self._thread.start()

    def _on_progress(self, completed: int):
        self.progress_bar.setValue(completed)
        self.progress_bar.setFormat(f"{completed} / {self._progress_total} languages")

    def _done(self):
        self.progress_bar.setValue(self._progress_total)
        self.progress_bar.setFormat(f"Done — {self._progress_total} languages")
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶  Start Translation")

    def _load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
            self.dir_label.setText(s.get("directory", "No directory selected"))
            self.overwrite_check.setChecked(s.get("overwrite", False))
            idx = self.source_combo.findText(s.get("source_lang", "EN"))
            if idx >= 0:
                self.source_combo.setCurrentIndex(idx)
            selected = set(s.get("selected_languages", []))
            for i in range(self.lang_list.count()):
                item = self.lang_list.item(i)
                item.setCheckState(Qt.Checked if item.data(Qt.UserRole) in selected else Qt.Unchecked)
        except Exception as e:
            self._append_log(f"[!] Could not load settings: {e}")

    def _save_settings(self):
        selected = [
            self.lang_list.item(i).data(Qt.UserRole)
            for i in range(self.lang_list.count())
            if self.lang_list.item(i).checkState() == Qt.Checked
        ]
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "directory":          self.dir_label.text(),
                    "overwrite":          self.overwrite_check.isChecked(),
                    "source_lang":        self.source_combo.currentText(),
                    "selected_languages": selected,
                }, f, indent=4)
        except Exception as e:
            self._append_log(f"[!] Could not save settings: {e}")

    def closeEvent(self, event):
        self._save_settings()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TranslatorGUI()
    window.show()
    sys.exit(app.exec_())
