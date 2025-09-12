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
        if text is None or text == "":
            raise ValueError("Text to translate cannot be empty")
        if not text.strip():
            return ""
        
        # check length of text (DeepL free tier limit is 5000 characters)
        if len(text) > 5000:
            raise ValueError("Text to translate exceeds 5000 character limit")
        
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
            raise RuntimeError("DeepL API error " + str(response.status_code) + ": " + response.text)
        
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
        # check texts is not empty
        if texts is None or len(texts) == 0:
            raise ValueError("List of texts to translate cannot be empty")
        if all(not text.strip() for text in texts):
            raise ValueError("All texts in the list are empty or whitespace")
        
        # convert None to empty string and ensure all are strings
        texts = [("" if t is None else str(t)) for t in texts]
        
        # normalise language codes
        source_lang = self.normalise_lang_code(source_lang)
        target_lang = self.normalise_lang_code(target_lang)

        # choose DeepL endpoint (for now it is free)
        endpoint = "https://api-free.deepl.com/v2/translate"

        # build request data
        data = {
            "auth_key": self.api_key,
            "text": texts,
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
            raise RuntimeError("DeepL API error " + str(response.status_code) + ": " + response.text)
        
        # parse response
        try:
            data = response.json()
            translated_texts = [t["text"] for t in data["translations"]]
        except ValueError:
            # JSON decoding error
            raise RuntimeError("Error decoding DeepL API response")
        
        # return list of translated strings in the same order
        return translated_texts
    
    # normalise text code (from wikipediaapi format to DeepLTranslator format)
    def normalise_lang_code(self, lang:str):
        return lang.upper()


# function to translate paragraph (use for testing)
def translate_paragraph(paragraph, src_lang, translator):
    # return translated paragraph as string
    return translator.translate_text(paragraph, src_lang, "EN-GB")

# function to translate article
def translate_article(article_dict, src_lang, translator):
    # prepare output with same section keys
    out = {}
    for section in article_dict.keys():
        out[section] = []
    
    # build flat list
    flat_list = [] # {"section": "...", "idx": ..., "text": "..."}
    for section, paragraphs in article_dict.items():
        for i, txt in enumerate(paragraphs):
            flat_list.append({"section": section, "idx": i, "text": ("" if txt is None else str(txt))})
    
    # if flat_list is empty, return empty output
    if not flat_list:
        return out
    
    # chunk flat list into batches of 50 (DeepL free tier limit is 50 texts per request)
    max_batch_size = 50
    n = len(flat_list)
    pos = 0

    # loop through batches
    while pos < n:
        # define batch and extract texts
        batch = flat_list[pos:pos+max_batch_size]
        texts = [item["text"] for item in batch]

        # one HTTP call for this batch
        translated_texts = translator.translate_batch(texts, src_lang, "EN-GB")
        
        # zip translated texts with original items and append to correct section
        for item, translated in zip(batch, translated_texts):
            # create record
            record = {
                "lang": "EN-GB",
                "original": item["text"],
                "translated": translated,
                "idx": item["idx"]
            }
            # append to correct section
            out[item["section"]].append(record)
        
        # move on to next batch
        pos += max_batch_size

    # return translated article as dict[str, list[{"lang": "...", "original": "...", "translated": "..."}]]
    return out

# testing
"""
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
"""
if __name__ == "__main__":
    # test article translation
    try:
        translator = DeepLTranslator()
        article = {
            "Introduction": [
                "Hola mundo",
                "Este es un artículo de prueba."
            ],
            "Content": [
                "La inteligencia artificial es un campo de estudio.",
                "Que permite traducción automática que puede mejorar la comunicación."
            ]
        }
        translated_article = translate_article(article, "es", translator)
        for section, records in translated_article.items():
            print("Section: " + section)
            for record in records:
                print("  Original: " + record["original"])
                print("  Translated: " + record["translated"])
    except Exception as e:
        print("Error:", e)

