# imports
import os, requests
from dotenv import load_dotenv

# Translator
class DeepLTranslator:
    # initialiser
    def __init__(self):
        load_dotenv() # look for .env in project root
        api_key = os.getenv("DEEPL_API_KEY") # get api key from .env
        if not api_key: # check api_key is not empty
            raise RuntimeError(
                "DEEPL_API_KEY is missing. Add it to your .env file."
            )
        self.api_key = api_key # assign api key to translator
    
    # translate text
    def translate_text(self, text: str, source_lang: str, target_lang: str):
        # check text is not empty
        if text is None:
            raise ValueError("Text to translate cannot be None")
        if not text.strip():
            return ""
        
        # normalise language codes
        source_lang = self.normalise_lang_code(source_lang)
        target_lang = self.normalise_lang_code(target_lang)

        # choose DeepL endpoint (for now it is free)
        endpoint = "https://api-free.deepl.com/v2/translate"

        # build request data
        data = {
            "auth_key": self.api_key,
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }

        # send request
        try:
            response = requests.post(endpoint, data=data)
        except requests.RequestException as e:
            raise RuntimeError("Error connecting to DeepL API: " + str(e))
        
        # error handling
        if response.status_code != 200:
            raise RuntimeError(
                f"DeepL API error {response.status_code}: {response.text}"
            )
        
        # parse response & return translated text as string
        try:
            data = response.json()
            translated_text = data["translations"][0]["text"]
            return translated_text
        except ValueError:
            # JSON decoding error
            raise RuntimeError("Error decoding DeepL API response")

    # translate list of text in batch
    def translate_batch(self, texts: list[str], source_lang: str, target_lang: str):
        # return list of translated strings in the same order
        return
    
    # normalise text code (from wikipediaapi format to DeepLTranslator format)
    def normalise_lang_code(self, lang:str):
        return lang.upper()


# function to translate paragraph (use for testing)
def translate_paragraph(paragraph, src_lang, translator):
    # return translated paragraph as string
    return

# function to translate article
def translate_article(article_dict, src_lang, translator):
    # return translated article as dict[str, list[{"lang": "...", "original": "...", "translated": "..."}]]
    return

# testing
if __name__ == "__main__":
    # test paragraph translation
    try:
        translator = DeepLTranslator()
        original = "Hola mundo"
        translated = translator.translate_text(original, "es", "EN-GB")
        print("Original:", original)
        print("Translated:", translated)
    except Exception as e:
        print("Error:", e)