# localization
from translator import Translator

translator = Translator()

def loc(key, **kwargs):
    return translator.localised(key, **kwargs)
