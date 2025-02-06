import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel,
    QCheckBox, QListWidget, QListWidgetItem, QTextEdit, QHBoxLayout
)
from PyQt5.QtCore import Qt
import json

class TranslatorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Translation Script GUI")
        self.setGeometry(100, 100, 600, 400)

        self.initUI()

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
        try:
            with open("LanguagesInfo_b42.json", "r", encoding="utf-8") as f:
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
        """Runs the translation script with the selected options."""
        directory = self.dir_path.text()
        if directory == "No directory selected":
            self.output_log.append("Error: No directory selected.")
            return

        no41_flag = "-no41" if self.b41_checkbox.isChecked() else ""
        selected_languages = [
            self.lang_list.item(i).text() for i in range(self.lang_list.count())
            if self.lang_list.item(i).checkState() == Qt.Checked
        ]
        lang_args = [f"-{lang}" for lang in selected_languages]

        command = [sys.executable, "translate.py", directory, no41_flag] + lang_args
        command = [arg for arg in command if arg]  # Remove empty arguments

        self.output_log.append(f"Running command: {' '.join(command)}\n")

        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        for line in iter(process.stdout.readline, ""):
            self.output_log.append(line.strip())
            QApplication.processEvents()

        for line in iter(process.stderr.readline, ""):
            self.output_log.append(f"Error: {line.strip()}")
            QApplication.processEvents()

        process.stdout.close()
        process.stderr.close()
        process.wait()
        self.output_log.append("\nTranslation Complete.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TranslatorGUI()
    window.show()
    sys.exit(app.exec_())