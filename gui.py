from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QCheckBox, QTextEdit, QProgressBar, QLineEdit, QScrollArea,
    QGroupBox, QHBoxLayout, QListWidget, QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QSpinBox,
    QToolButton, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QDropEvent, QDragEnterEvent
import os
import json
from translator import Translator
from settings import Settings

# Add the CollapsibleBox class
class CollapsibleBox(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)

        self.toggle_button = QToolButton(text=title, checkable=True)
        self.toggle_button.setStyleSheet("QToolButton { background-color: transparent; border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.clicked.connect(self.on_toggle)

        self.content_area = QWidget()
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.content_area_layout = QVBoxLayout()
        self.content_area.setLayout(self.content_area_layout)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_area)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.content_area.setVisible(False)

    def on_toggle(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.content_area.setVisible(checked)
        if checked:
            self.content_area.setMaximumHeight(16777215)  # Effectively no limit
        else:
            self.content_area.setMaximumHeight(0)

    def setContentLayout(self, layout):
        # Clear existing layout items
        while self.content_area_layout.count():
            item = self.content_area_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.content_area_layout.addLayout(layout)

class AISettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI環境設定")
        self.layout = QFormLayout(self)
        self.settings = settings

        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-4o-2024-08-06", "gpt-4o", "gpt-4o-mini"])
        self.model_combo.setCurrentText(self.settings.ai_model)
        self.layout.addRow("モデル名:", self.model_combo)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 100000)
        self.max_tokens_spin.setValue(self.settings.max_tokens)
        self.layout.addRow("Max Tokens:", self.max_tokens_spin)

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 1.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(self.settings.temperature)
        self.layout.addRow("Temperature:", self.temperature_spin)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.accept)
        self.layout.addRow(self.save_button)

    def get_settings(self):
        return {
            "model": self.model_combo.currentText(),
            "max_tokens": self.max_tokens_spin.value(),
            "temperature": self.temperature_spin.value()
        }

class TranslationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("技術書マークダウン翻訳")

        self.thread_pool = QThreadPool()
        self.selected_files = []
        self.api_key = ""
        self.save_api_key = False
        self.languages = {}
        self.settings = Settings()
        self.settings.load()
        self.init_ui()
        self.load_languages()
        self.load_api_key()

        self.progress_bar.setMaximum(100)
        
        # ドラッグアンドドロップを有効にする
        self.setAcceptDrops(True)

    def init_ui(self):
        layout = QVBoxLayout()

        # --------------------
        # File selection area
        # --------------------
        file_label = QLabel("ファイル選択またはドラッグandドロップ")
        layout.addWidget(file_label)

        self.file_list = QListWidget()
        self.file_list.setAcceptDrops(True)
        self.file_list.setDragDropMode(QListWidget.InternalMove)
        layout.addWidget(self.file_list)

        file_button = QPushButton("ファイル選択")
        file_button.clicked.connect(self.select_files)
        layout.addWidget(file_button)

        # --------------------
        # Language selection area
        # --------------------
        language_label = QLabel("言語選択")
        layout.addWidget(language_label)

        self.language_layout = QGridLayout()  # QVBoxLayout から QGridLayout に変更
        self.language_checks = {}
        language_widget = QWidget()
        language_widget.setLayout(self.language_layout)
        language_scroll = QScrollArea()
        language_scroll.setWidgetResizable(True)
        language_scroll.setWidget(language_widget)
        layout.addWidget(language_scroll)

        # --------------------
        # Collapsible API Key area
        # --------------------
        api_collapsible = CollapsibleBox("APIキー設定")
        api_layout = QVBoxLayout()

        api_label = QLabel("APIキー(環境変数に入れてる場合は空欄でOK)")
        api_layout.addWidget(api_label)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.api_key_edit)

        # APIキー保存チェックボックス
        self.save_api_checkbox = QCheckBox("APIキー保存")
        api_layout.addWidget(self.save_api_checkbox)

        api_collapsible.setContentLayout(api_layout)
        layout.addWidget(api_collapsible)

        # --------------------
        # Collapsible settings area
        # --------------------
        settings_collapsible = CollapsibleBox("予備/後処理の追加オプション")
        settings_layout = QVBoxLayout()

        self.remove_comments_checkbox = QCheckBox("翻訳前にHTMLコメントを削除")
        self.remove_comments_checkbox.setChecked(self.settings.remove_comments)
        settings_layout.addWidget(self.remove_comments_checkbox)

        self.add_newlines_checkbox = QCheckBox("大見出しの前後に改行を追加")
        self.add_newlines_checkbox.setChecked(self.settings.add_newlines)
        settings_layout.addWidget(self.add_newlines_checkbox)

        self.add_newlines_subheadings_checkbox = QCheckBox("中見出しの前後に空行を入れる")
        self.add_newlines_subheadings_checkbox.setChecked(self.settings.add_newlines_subheadings)
        settings_layout.addWidget(self.add_newlines_subheadings_checkbox)

        self.add_final_newline_checkbox = QCheckBox("ファイルの末尾に改行を追加")
        self.add_final_newline_checkbox.setChecked(self.settings.add_final_newline)
        settings_layout.addWidget(self.add_final_newline_checkbox)

        settings_collapsible.setContentLayout(settings_layout)
        layout.addWidget(settings_collapsible)

        # --------------------
        # Collapsible AI Settings area
        # --------------------
        ai_collapsible = CollapsibleBox("AI環境設定")
        ai_layout = QVBoxLayout()

        ai_settings_button = QPushButton("AI環境設定")
        ai_settings_button.clicked.connect(self.open_ai_settings)
        ai_layout.addWidget(ai_settings_button)

        ai_collapsible.setContentLayout(ai_layout)
        layout.addWidget(ai_collapsible)

        # --------------------
        # Translate button
        # --------------------
        translate_button = QPushButton("翻訳実行")
        translate_button.clicked.connect(self.start_translation)
        layout.addWidget(translate_button)

        # --------------------
        # Progress bar
        # --------------------
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # --------------------
        # Log area
        # --------------------
        log_label = QLabel("ログ")
        layout.addWidget(log_label)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

        self.setLayout(layout)

        # 各チェックボックスに状態変化時のシグナルを接続
        self.remove_comments_checkbox.stateChanged.connect(self.save_settings)
        self.add_newlines_checkbox.stateChanged.connect(self.save_settings)
        self.add_newlines_subheadings_checkbox.stateChanged.connect(self.save_settings)
        self.add_final_newline_checkbox.stateChanged.connect(self.save_settings)

    def open_ai_settings(self):
        dialog = AISettingsDialog(self.settings, self)
        if dialog.exec():
            ai_settings = dialog.get_settings()
            self.settings.ai_model = ai_settings["model"]
            self.settings.max_tokens = ai_settings["max_tokens"]
            self.settings.temperature = ai_settings["temperature"]
            self.settings.save()
            self.log_edit.append("AI環境設定を更新しました。")

    def load_languages(self):
        with open('languages.json', 'r', encoding='utf-8') as f:
            self.languages = json.load(f)

        cols = 2  # 列数を2に設定
        row = 0
        col = 0
        for index, lang in enumerate(self.languages.keys()):
            checkbox = QCheckBox(lang)
            self.language_layout.addWidget(checkbox, row, col)
            self.language_checks[lang] = checkbox
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def load_api_key(self):
        if os.path.exists('api_key.txt'):
            with open('api_key.txt', 'r') as f:
                self.api_key = f.read().strip()
                self.api_key_edit.setText(self.api_key)
                self.save_api_checkbox.setChecked(True)

    def save_api_key_to_file(self):
        if self.save_api_checkbox.isChecked():
            with open('api_key.txt', 'w') as f:
                f.write(self.api_key)
        else:
            if os.path.exists('api_key.txt'):
                os.remove('api_key.txt')

    def select_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "ファイルを選択", "", "Markdown Files (*.md *.markdown);;Text Files (*.txt);;All Files (*)")
        if file_paths:
            self.add_files(file_paths)

    def add_files(self, file_paths):
        for file_path in file_paths:
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
                self.file_list.addItem(file_path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        file_paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self.add_files(file_paths)

    def start_translation(self):
        self.selected_languages = [lang for lang, checkbox in self.language_checks.items() if checkbox.isChecked()]
        if not self.selected_files:
            self.log_edit.append("ファイルを選択してください。")
            return
        if not self.selected_languages:
            self.log_edit.append("少なくとも一つの言語を選択してください。")
            return
        self.api_key = self.api_key_edit.text().strip()
        if not self.api_key:
            self.api_key = os.getenv('OPENAI_API_KEY', '').strip()
            if not self.api_key:
                self.log_edit.append("APIキーを入力するか、環境変数OPENAI_API_KEYを設定してください。")
                return

        self.settings.remove_comments = self.remove_comments_checkbox.isChecked()
        self.settings.add_newlines = self.add_newlines_checkbox.isChecked()
        self.settings.add_newlines_subheadings = self.add_newlines_subheadings_checkbox.isChecked()
        self.settings.add_final_newline = self.add_final_newline_checkbox.isChecked()
        self.settings.save()

        self.save_api_key_to_file()

        self.progress_bar.setValue(0)
        total_files = len(self.selected_files)
        for index, file_path in enumerate(self.selected_files):
            translator = Translator(
                file_path=file_path,
                selected_languages=self.selected_languages,
                languages=self.languages,
                api_key=self.api_key,
                settings=self.settings
            )
            translator.signals.progress.connect(lambda value, idx=index, total=total_files: self.update_progress(value, idx, total))
            translator.signals.log.connect(self.update_log)
            translator.signals.finished.connect(self.translation_finished)

            self.thread_pool.start(translator)
        self.log_edit.append("翻訳を開始しました。")

    def update_progress(self, value, file_index, total_files):
        overall_progress = int((file_index * 100 + value) / total_files)
        self.progress_bar.setValue(overall_progress)
        if overall_progress >= 100:
            self.log_edit.append("すべての翻訳が完了しました。")

    def update_log(self, message):
        self.log_edit.append(message)

    def translation_finished(self):
        self.progress_bar.setValue(100)  # 翻訳が完了したら進捗バーを100%に設定
        self.log_edit.append("翻訳が完了しました。")

    def save_settings(self):
        self.settings.remove_comments = self.remove_comments_checkbox.isChecked()
        self.settings.add_newlines = self.add_newlines_checkbox.isChecked()
        self.settings.add_newlines_subheadings = self.add_newlines_subheadings_checkbox.isChecked()
        self.settings.add_final_newline = self.add_final_newline_checkbox.isChecked()
        self.settings.save()
        self.log_edit.append("設定を保存しました。")