import openai
import os
import time

class OpenAIWrapper:
    def __init__(self, api_key=None):
        if api_key:
            openai.api_key = api_key
        else:
            self.get_client()

    def get_client(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is not set in environment variables.")
        openai.api_key = api_key

    def translate_text(self, system_prompt, user_content, max_tokens=52000, temperature=0.1, model_name="gpt-4o", retries=3):
        client = openai
        for attempt in range(retries):
            try:
                params = {
                    "model": model_name,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ]
                }
                if isinstance(max_tokens, int) and max_tokens > 0:
                    params["max_tokens"] = max_tokens

                response = client.chat.completions.create(**params)
                return response.choices[0].message.content
            except Exception as e:
                print(f"試行 {attempt + 1} でエラーが発生しました: {e}")
                if attempt < retries - 1:
                    time.sleep(10)
                else:
                    raise e

