import os
import json
import time
import re
import openai
from PySide6.QtCore import QRunnable, Signal, QObject
from openai_wrapper import OpenAIWrapper

class TranslatorSignals(QObject):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal()

class Translator(QRunnable):
    def __init__(self, file_path, selected_languages, languages, api_key, settings):
        super().__init__()
        self.file_path = file_path
        self.selected_languages = selected_languages
        self.languages = languages
        self.api_key = api_key
        self.settings = settings
        self.signals = TranslatorSignals()
        self.openai_wrapper = OpenAIWrapper(self.api_key)

    def run(self):
        try:
            total_steps = 6 * len(self.selected_languages)
            current_step = 0

            for lang in self.selected_languages:
                lang_settings = self.languages[lang]
                base_name, ext = os.path.splitext(self.file_path)
                output_file = f"{base_name}{lang_settings['suffix']}{ext}"

                self.signals.log.emit(f"{lang} の翻訳を開始します。")

                # 1. ファイル準備
                self.prepare_file(self.file_path, output_file)
                current_step += 1
                self.update_progress(current_step, total_steps)

                # 2. 翻訳処理
                self.translate_file(output_file, lang_settings)
                current_step += 1
                self.update_progress(current_step, total_steps)

                # 3. フォーマット調整
                self.adjust_format(output_file)
                current_step += 1
                self.update_progress(current_step, total_steps)

                # 4. フォント設定の適用
                # self.apply_font_settings(output_file, lang_settings)
                current_step += 1
                self.update_progress(current_step, total_steps)

                # 5. 日本語混入チェック
                self.check_japanese_text(output_file, lang)
                current_step += 1
                self.update_progress(current_step, total_steps)

                self.signals.log.emit(f"{lang} の翻訳が完了しました。")

            self.signals.finished.emit()
        except Exception as e:
            self.signals.log.emit(f"エラーが発生しました: {str(e)}")

    def update_progress(self, step, total_steps):
        progress_percentage = int((step / total_steps) * 100)
        self.signals.progress.emit(progress_percentage)

    def prepare_file(self, input_file, output_file):
        with open(input_file, 'r', encoding='utf-8') as f_in, open(output_file, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                if self.settings.remove_comments and re.match(r'^\s*<!--.*-->\s*$', line):
                    continue
                f_out.write(line)

    def translate_file(self, file_path, lang_settings):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        prompt = lang_settings["prompt"]
        translated_content = self.openai_wrapper.translate_text(
            system_prompt=prompt,
            user_content=content,
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
            model_name=self.settings.ai_model,
            retries=3
        )

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(translated_content)

    def adjust_format(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for i, line in enumerate(lines):
            if self.settings.add_newlines and line.startswith('#'):
                if i > 0 and lines[i - 1].strip() != '':
                    new_lines.append('\n')
                new_lines.append(line)
                if i + 1 < len(lines) and lines[i + 1].strip() != '':
                    new_lines.append('\n')
            elif self.settings.add_newlines_subheadings and line.startswith('##'):
                if i > 0 and lines[i - 1].strip() != '':
                    new_lines.append('\n')
                new_lines.append(line)
                if i + 1 < len(lines) and lines[i + 1].strip() != '':
                    new_lines.append('\n')
            else:
                new_lines.append(line)

        if self.settings.add_final_newline and new_lines[-1].strip() != '':
            new_lines.append('\n')

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    # def apply_font_settings(self, file_path, lang_settings):
    #     css_content = f"""
    # <style>
    # @import url('{lang_settings['fontImportUrl']}');
    # body {{
    #     font-family: {lang_settings['fontFamily']};
    #     font-weight: {lang_settings['bodyFontWeight']};
    #     font-size: {lang_settings['fontSize']};
    #     line-height: {lang_settings['lineHeight']};
    # }}
    # h1, h2, h3, h4, h5, h6 {{
    #     font-weight: {lang_settings['headingFontWeight']};
    # }}
    # </style>
    # """
    #     with open(file_path, 'r', encoding='utf-8') as f:
    #         content = f.read()

    #     content = css_content + content

    #     with open(file_path, 'w', encoding='utf-8') as f:
    #         f.write(content)

    def check_japanese_text(self, file_path, lang):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        japanese_pattern = re.compile("[一-龯ぁ-んァ-ン]")

        issues = []

        for line_num, line in enumerate(lines, 1):
            if japanese_pattern.search(line):
                issues.append((line_num, line.strip()))

        if issues:
            result_file = f"japanese_check_{lang}.txt"
            with open(result_file, 'w', encoding='utf-8') as f:
                for line_num, text in issues:
                    f.write(f"ファイル名: {file_path}, 行番号: {line_num}, 検出された文字列: {text}\n")
            self.signals.log.emit(f"日本語混入チェック結果を {result_file} に出力しました。")
        else:
            self.signals.log.emit("日本語混入は検出されませんでした。")