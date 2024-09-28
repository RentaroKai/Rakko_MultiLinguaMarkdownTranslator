import json

class Settings:
    def __init__(self):
        self.remove_comments = False
        self.add_newlines = False
        self.add_newlines_subheadings = False
        self.add_final_newline = False
        self.ai_model = "gpt-4o-2024-08-06"
        self.max_tokens = 12000
        self.temperature = 0.1

    def save(self):
        with open('settings.json', 'w') as f:
            json.dump(self.__dict__, f)

    def load(self):
        try:
            with open('settings.json', 'r') as f:
                data = json.load(f)
                self.__dict__.update(data)
        except FileNotFoundError:
            pass  # ファイルが存在しない場合は、デフォルト設定を使用

    def __str__(self):
        return json.dumps(self.__dict__, indent=2)