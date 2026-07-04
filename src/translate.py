# imports
import os, json, hashlib, requests
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

        # set up translation cache (avoids re-calling DeepL for text already translated)
        self.cache_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "cache", "translations.json"
        ) # project_root/cache/translations.json
        self.cache = self._load_cache() # load existing cache (empty dict if none)

    # build a unique cache key for a piece of text + its language pair
    def _cache_key(self, text, source_lang, target_lang):
        raw = source_lang + "|" + target_lang + "|" + text # combine so same text in different langs differ
        return hashlib.sha256(raw.encode("utf-8")).hexdigest() # short, stable key

    # load the translation cache from disk (json file of key -> {original, translated})
    def _load_cache(self):
        if not os.path.exists(self.cache_path): # no cache file yet
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f) # read json text back into a python dict
        except (ValueError, OSError):
            return {} # corrupt or unreadable -> start fresh, don't crash

    # save the translation cache to disk as json
    def save_cache(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True) # make sure cache/ folder exists
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2) # write dict out as readable json

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

        # check cache first (skip the API if we already translated this exact text)
        key = self._cache_key(text, source_lang, target_lang)
        if key in self.cache:
            return self.cache[key]["translated"] # cache hit -> return saved translation

        # choose DeepL endpoint (for now it is free)
        endpoint = "https://api-free.deepl.com/v2/translate"

        # build request data
        data = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }

        # authenticate via header (DeepL no longer accepts auth_key in the body)
        headers = {"Authorization": "DeepL-Auth-Key " + self.api_key}

        # send request
        try:
            response = requests.post(endpoint, data=data, headers=headers)
        except requests.RequestException as e:
            raise RuntimeError("Error connecting to DeepL API: " + str(e))

        # error handling
        if response.status_code == 400 and "not supported" in response.text.lower():
            raise ValueError("DeepL API error: Unsupported language code(s) " + source_lang + " or " + target_lang)
        if response.status_code != 200:
            raise RuntimeError("DeepL API error " + str(response.status_code) + ": " + response.text)

        # parse response & return translated text as string
        try:
            data = response.json()
            translated_text = data["translations"][0]["text"]
            self.cache[key] = {"original": text, "translated": translated_text} # save to cache for next time
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

        # split texts into cache hits (already translated) and misses (need the API)
        keys = [self._cache_key(t, source_lang, target_lang) for t in texts] # one key per text
        results = [None] * len(texts) # final translations, filled by position
        missing_indices = [] # positions whose text is not cached yet
        missing_texts = [] # the actual texts we still need to send to DeepL
        for i, key in enumerate(keys):
            if key in self.cache:
                results[i] = self.cache[key]["translated"] # cache hit -> reuse saved translation
            else:
                missing_indices.append(i) # remember where this text belongs
                missing_texts.append(texts[i])

        # only call DeepL if at least one text is uncached
        if missing_texts:
            # choose DeepL endpoint (for now it is free)
            endpoint = "https://api-free.deepl.com/v2/translate"

            # build request data (only the uncached texts)
            data = {
                "text": missing_texts,
                "source_lang": source_lang,
                "target_lang": target_lang,
            }

            # authenticate via header (DeepL no longer accepts auth_key in the body)
            headers = {"Authorization": "DeepL-Auth-Key " + self.api_key}

            # send request
            try:
                response = requests.post(endpoint, data=data, headers=headers)
            except requests.RequestException as e:
                raise RuntimeError("Error connecting to DeepL API: " + str(e))

            # error handling
            if response.status_code == 400 and "not supported" in response.text.lower():
                raise ValueError("DeepL API error: Unsupported language code(s) " + source_lang + " or " + target_lang)
            if response.status_code != 200:
                raise RuntimeError("DeepL API error " + str(response.status_code) + ": " + response.text)

            # parse response
            try:
                data = response.json()
                translated_texts = [t["text"] for t in data["translations"]]
            except ValueError:
                # JSON decoding error
                raise RuntimeError("Error decoding DeepL API response")

            # slot each new translation back into its original position + save to cache
            for idx, translated in zip(missing_indices, translated_texts):
                results[idx] = translated
                self.cache[keys[idx]] = {"original": texts[idx], "translated": translated}

        # return list of translated strings in the same order
        return results
    
    # normalise text code (from wikipediaapi format to DeepLTranslator format)
    def normalise_lang_code(self, lang:str):
        code = lang.strip().upper() # strip whitespace and uppercase
        if code == "SIMPLE": # simple english wikipedia -> treat as english for DeepL
            return "EN"
        return code


# function to translate paragraph (use for testing)
def translate_paragraph(paragraph, src_lang, translator):
    # return translated paragraph as string
    return translator.translate_text(paragraph, src_lang, "EN-GB")

# function to translate article
def translate_article(article_dict, src_lang, translator):
    # check inputs are valid types
    if not isinstance(article_dict, dict):
        raise ValueError("Article must be a dictionary of section -> list of paragraphs")

    # translate section titles & make a mapping of old to new titles
    section_names = list(article_dict.keys())
    translated_section_names = translator.translate_batch(section_names, src_lang, "EN-GB")
    section_map = dict(zip(section_names, translated_section_names)) # mapping original -> translated section names

    # prepare output with translated section keys (from section_map, so keys match the append loop below)
    out = {translated: [] for translated in section_map.values()}
    
    # build flat list
    flat_list = [] # {"section": "...", "idx": ..., "text": "..."}
    for section, paragraphs in article_dict.items():
        for i, txt in enumerate(paragraphs):
            flat_list.append({"section": section, "idx": i, "text": ("" if txt is None else str(txt))})
    
    # if flat_list is empty, return empty output
    if not flat_list:
        translator.save_cache() # persist any section-title translations done above
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
                "lang": src_lang.upper(), # source language code
                "original": item["text"], # original text
                "translated": translated, # translated text
                "idx": item["idx"] # original index in section
            }
            # append to correct section (need to use section map to get translated section name!)
            out[section_map[item["section"]]].append(record)
        
        # move on to next batch
        pos += max_batch_size

    # persist cache so future runs can reuse these translations
    translator.save_cache()

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

