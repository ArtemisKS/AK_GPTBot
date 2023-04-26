import json
import os

# Constants
default_lang = 'ru'

class Translator:
    def __init__(self, language_code=default_lang):
        self.language_code = language_code
        self.translations = self.load_translations()

    def load_translations(self):
        file_name = f"{self.language_code}.json"
        file_path = os.path.join("loc", file_name)

        with open(file_path, "r", encoding="utf-8") as f:
            translations = json.load(f)

        return translations

    def localised(self, key, **kwargs):
        translated_string = self.translations.get(key, key)
        return translated_string.format(**kwargs)

    def change_language(self, language_code):
        if self.language_code == language_code:
            return
        
        self.language_code = language_code
        self.translations = self.load_translations()
        
    def is_current_lang(self, language_code) -> bool:
        return self.language_code == language_code
