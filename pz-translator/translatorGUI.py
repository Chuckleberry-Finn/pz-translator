import sys
import os
import subprocess
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel,
    QCheckBox, QListWidget, QListWidgetItem, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

SETTINGS_FILE = "translator_settings.json"

class TranslationThread(QThread):
    output_signal = pyqtSignal(str)  # Signal to send output logs to the GUI
    finished_signal = pyqtSignal()  # Signal to indicate process completion

    def __init__(self, base_dir, directory, no41_flag, selected_languages):
        super().__init__()
        self.base_dir = base_dir
        self.directory = directory
        self.no41_flag = no41_flag
        self.selected_languages = selected_languages

    def run(self):
        """Runs the translation script in a separate thread."""
        lang_args = [f"-{lang}" for lang in self.selected_languages]

        # Determine correct Python executable
        if getattr(sys, 'frozen', False):
            python_exec = "python"  # Use system-installed Python
        else:
            python_exec = sys.executable  # Normal Python script execution

        command = [python_exec, os.path.join(self.base_dir, "translate.py"), self.directory, self.no41_flag] + lang_args
        command = [arg for arg in command if arg]  # Remove empty arguments

        self.output_signal.emit(f"Running command: {' '.join(command)}\n")

        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            bufsize=1, universal_newlines=True
        )

        # Read output in real-time
        for line in iter(process.stdout.readline, ""):
            self.output_signal.emit(line.strip())
            self.msleep(50)  # Prevent UI lockups

        # Capture errors
        stderr_output = process.stderr.read()
        if stderr_output:
            self.output_signal.emit(f"Error: {stderr_output.strip()}")

        process.stdout.close()
        process.stderr.close()
        process.wait()

        self.output_signal.emit("\nTranslation Complete.")
        self.finished_signal.emit()

class TranslatorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Translation Script GUI")
        self.setGeometry(100, 100, 600, 400)

        # Determine base directory dynamically
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Check if "pz-translator" exists next to the executable
        if exe_dir and os.path.exists(os.path.join(exe_dir, "pz-translator")):
            self.base_dir = os.path.join(exe_dir, "pz-translator")
        # Fallback to script directory
        elif os.path.exists(os.path.join(script_dir, "pz-translator")):
            self.base_dir = os.path.join(script_dir, "pz-translator")
        else:
            self.base_dir = script_dir  # Last fallback

        self.initUI()
        self.load_settings()

    def initUI(self):
        layout = QVBoxLayout()

        # Directory Selection
        self.dir_label = QLabel("Select Translation Directory:")
        self.dir_path = QLabel("No directory selected")
        self.dir_path.setWordWrap(True)
        self.select_dir_btn = QPushButton("Browse")
        self.select_dir_btn.clicked.connect(self.select_directory)

        layout.addWidget(self.dir_label)
        layout.addWidget(self.dir_path)
        layout.addWidget(self.select_dir_btn)

        # B41 Checkbox
        self.b41_checkbox = QCheckBox("Disable B41 Translations (-no41)")
        layout.addWidget(self.b41_checkbox)

        # Language Selection
        self.lang_label = QLabel("Select Languages:")
        self.lang_list = QListWidget()
        self.lang_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.lang_label)
        layout.addWidget(self.lang_list)

        # Load Languages
        self.load_languages()

        # Start Button
        self.start_btn = QPushButton("Start Translation")
        self.start_btn.clicked.connect(self.run_translation)
        layout.addWidget(self.start_btn)

        # Output Log
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.output_log)

        # Quit Button
        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.close)
        layout.addWidget(self.quit_btn)

        self.setLayout(layout)

    def load_languages(self):
        """Loads available languages from the language info files."""
        lang_info_path = os.path.join(self.base_dir, "LanguagesInfo_b42.json")
        try:
            with open(lang_info_path, "r", encoding="utf-8") as f:
                lang_data = json.load(f)
                for lang in lang_data:
                    if lang != "EN":
                        item = QListWidgetItem(lang)
                        item.setCheckState(Qt.Unchecked)
                        self.lang_list.addItem(item)
        except Exception as e:
            self.output_log.append(f"Error loading languages: {e}")

    def select_directory(self):
        """Opens a file dialog to select the translation directory."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            self.dir_path.setText(dir_path)

    def run_translation(self):
        """Starts the translation process asynchronously using QThread."""
        directory = self.dir_path.text()
        if directory == "No directory selected":
            self.output_log.append("Error: No directory selected.")
            return

        no41_flag = "-no41" if self.b41_checkbox.isChecked() else ""
        selected_languages = [
            self.lang_list.item(i).text() for i in range(self.lang_list.count())
            if self.lang_list.item(i).checkState() == Qt.Checked
        ]

        # Disable Start Button during translation
        self.start_btn.setEnabled(False)
        self.start_btn.setText("Translating...")

        # Start the translation process in a separate thread
        self.translation_thread = TranslationThread(self.base_dir, directory, no41_flag, selected_languages)
        self.translation_thread.output_signal.connect(self.output_log.append)  # Send output to GUI
        self.translation_thread.finished_signal.connect(self.translation_finished)  # Re-enable button when done
        self.translation_thread.start()

    def translation_finished(self):
        """Re-enables the Start Button after translation completes."""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("Start Translation")

    def load_settings(self):
        """Loads saved settings from a JSON file."""
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                self.dir_path.setText(settings.get("directory", "No directory selected"))
                self.b41_checkbox.setChecked(settings.get("b41_disabled", False))
                selected_languages = settings.get("selected_languages", [])
                for i in range(self.lang_list.count()):
                    item = self.lang_list.item(i)
                    if item.text() in selected_languages:
                        item.setCheckState(Qt.Checked)

    def save_settings(self):
        """Saves user settings to a JSON file."""
        selected_languages = [
            self.lang_list.item(i).text() for i in range(self.lang_list.count())
            if self.lang_list.item(i).checkState() == Qt.Checked
        ]
        settings = {
            "directory": self.dir_path.text(),
            "b41_disabled": self.b41_checkbox.isChecked(),
            "selected_languages": selected_languages
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)

    def select_directory(self):
        """Opens a file dialog to select the translation directory."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            self.dir_path.setText(dir_path)
            self.save_settings()

    def closeEvent(self, event):
        """Saves settings when the GUI is closed."""
        self.save_settings()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TranslatorGUI()
    window.show()
    sys.exit(app.exec_())
