# tests for src/translate.py. requests.post is always mocked (no real DeepL calls, no
# API key needed) via translate.requests.post; the on-disk translation cache is also
# mocked away so tests never touch the real cache/translations.json.
import pytest
from src import translate

# stand-in for a requests.Response: only the bits translate.py actually reads
class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
    def json(self):
        return self._payload

@pytest.fixture(autouse=True) # applies to all tests in this module
def fake_env_and_cache(monkeypatch):
    # a fake key is enough (real key/network is never touched, requests.post is mocked per test)
    monkeypatch.setenv("DEEPL_API_KEY", "test-key-not-real")
    # cache load/save are no-ops so tests cannot pollute the real cache/translations.json on disk
    monkeypatch.setattr(translate.DeepLTranslator, "_load_cache", lambda self: {}) # return empty cache
    monkeypatch.setattr(translate.DeepLTranslator, "save_cache", lambda self: None) # save_cache does nothing

# -- DeepLTranslator.__init__ ---------------------------------------------------

def test_init_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False) # simulate missing key
    monkeypatch.setattr(translate, "load_dotenv", lambda: None)  # don't let a real .env supply the key
    with pytest.raises(RuntimeError): # DeepLTranslator.__init__ should raise RuntimeError if no key is found
        translate.DeepLTranslator()

# -- translate_text ---------------------------------------------------------------

def test_translate_text_happy_path(monkeypatch):
    def fake_post(endpoint, data, headers): # stands in for requests.post; check args and return a fake response
        assert data["text"] == "Hola mundo"
        assert headers["Authorization"] == "DeepL-Auth-Key test-key-not-real"
        return FakeResponse(200, {"translations": [{"text": "Hello world"}]})
    monkeypatch.setattr(translate.requests, "post", fake_post)
    translator = translate.DeepLTranslator()
    assert translator.translate_text("Hola mundo", "es", "EN-GB") == "Hello world" # the translated text is returned

def test_translate_text_uses_cache_on_second_call(monkeypatch):
    calls = []
    def fake_post(*args, data, **kwargs): # stands in for requests.post; check args and return a fake response
        calls.append(data)
        return FakeResponse(200, {"translations": [{"text": "Hello"}]})
    monkeypatch.setattr(translate.requests, "post", fake_post)

    translator = translate.DeepLTranslator()
    first = translator.translate_text("Hola", "es", "EN-GB")
    second = translator.translate_text("Hola", "es", "EN-GB")
    assert first == second == "Hello" # the translated text is returned both times
    assert len(calls) == 1  # second call was a cache hit, no second HTTP request

def test_translate_text_raises_on_empty_string():
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError): # DeepLTranslator.translate_text should raise ValueError on empty string
        translator.translate_text("", "es", "EN-GB")

def test_translate_text_returns_empty_for_whitespace_only(monkeypatch):
    def fail_if_called(*args, **kwargs): # stands in for requests.post and raises if called (because whitespace-only text should never be sent to DeepL)
        raise AssertionError("should not call DeepL for whitespace-only text")
    monkeypatch.setattr(translate.requests, "post", fail_if_called)

    translator = translate.DeepLTranslator()
    assert translator.translate_text("   ", "es", "EN-GB") == "" # whitespace-only text is translated to empty string, no DeepL call is made

def test_translate_text_raises_when_over_deepl_free_tier_limit():
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError): # DeepLTranslator.translate_text should raise ValueError on text over 5000 chars
        translator.translate_text("a" * 5001, "es", "EN-GB")

def test_translate_text_raises_on_unsupported_language(monkeypatch):
    monkeypatch.setattr(translate.requests, "post", lambda *a, **kw: FakeResponse(400, text="Language pair not supported"))
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError): # DeepLTranslator.translate_text should raise ValueError on unsupported language
        translator.translate_text("Hola", "es", "XX")

def test_translate_text_raises_runtime_error_on_server_error(monkeypatch):
    monkeypatch.setattr(translate.requests, "post", lambda *a, **kw: FakeResponse(500, text="Internal Server Error"))
    translator = translate.DeepLTranslator()
    with pytest.raises(RuntimeError): # DeepLTranslator.translate_text should raise RuntimeError on server error
        translator.translate_text("Hola", "es", "EN-GB")

def test_translate_text_raises_runtime_error_on_connection_failure(monkeypatch):
    def raise_connection_error(*args, **kwargs): # stands in for requests.post and simulates a network failure
        raise translate.requests.RequestException("network down")
    monkeypatch.setattr(translate.requests, "post", raise_connection_error)

    translator = translate.DeepLTranslator()
    with pytest.raises(RuntimeError): # DeepLTranslator.translate_text should raise RuntimeError on connection failure
        translator.translate_text("Hola", "es", "EN-GB")

# -- translate_batch --------------------------------------------------------------

def test_translate_batch_only_requests_uncached_texts(monkeypatch):
    calls = []
    def fake_post(*args, data, **kwargs): # stands in for requests.post; check args and return a fake response
        calls.append(data["text"])
        return FakeResponse(200, {"translations": [{"text": "World"}]})
    monkeypatch.setattr(translate.requests, "post", fake_post)

    translator = translate.DeepLTranslator()
    # prime the cache directly, as if "Hola" was already translated in an earlier run
    key = translator._cache_key("Hola", "ES", "EN-GB")
    translator.cache[key] = {"original": "Hola", "translated": "Hello"}

    results = translator.translate_batch(["Hola", "Mundo"], "es", "EN-GB")
    assert results == ["Hello", "World"] # the returned list has the correct translations
    assert calls == [["Mundo"]]  # only the uncached text was actually sent to DeepL

def test_translate_batch_raises_on_empty_list():
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError): # DeepLTranslator.translate_batch should raise ValueError on empty list
        translator.translate_batch([], "es", "EN-GB")

def test_translate_batch_raises_when_all_whitespace():
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError): # DeepLTranslator.translate_batch should raise ValueError when all texts are whitespace-only
        translator.translate_batch(["  ", ""], "es", "EN-GB")

def test_translate_batch_raises_when_response_shorter_than_request(monkeypatch):
    # DeepL returns only one translation for two requested texts (a short/mismatched response)
    def fake_post(*args, **kwargs): # stands in for requests.post; return a fake response with only one translation
        return FakeResponse(200, {"translations": [{"text": "Hello"}]})
    monkeypatch.setattr(translate.requests, "post", fake_post)
    translator = translate.DeepLTranslator()
    with pytest.raises(RuntimeError): # a response-length mismatch should raise, not silently leave a None translation
        translator.translate_batch(["Hola", "Mundo"], "es", "EN-GB")

# -- normalise_lang_code + _cache_key ---------------------------------------------

def test_normalise_lang_code_uppercases():
    translator = translate.DeepLTranslator()
    assert translator.normalise_lang_code("es") == "ES" # lower-case codes are uppercased

def test_normalise_lang_code_maps_simple_to_english():
    translator = translate.DeepLTranslator()
    assert translator.normalise_lang_code("simple") == "EN" # "simple" and "Simple" are mapped to "EN" (Simple English is in English)
    assert translator.normalise_lang_code("Simple") == "EN" # same objective as previous line

def test_cache_key_differs_by_language_pair():
    translator = translate.DeepLTranslator()
    key1 = translator._cache_key("Hola", "ES", "EN-GB")
    key2 = translator._cache_key("Hola", "ES", "FR")
    assert key1 != key2 # the cache key differs by language pair, so the same text in different target languages is cached separately

# -- translate_paragraph + translate_article ---------------------------------------

def test_translate_paragraph_delegates_to_translate_text(monkeypatch):
    called = {}
    def fake_translate_text(self, paragraph, src, tgt): # stands in for DeepLTranslator.translate_text; record args and return a fake translation
        called["args"] = (paragraph, src, tgt)
        return "translated!"
    monkeypatch.setattr(translate.DeepLTranslator, "translate_text", fake_translate_text)

    translator = translate.DeepLTranslator()
    assert translate.translate_paragraph("hola", "es", translator) == "translated!" # the translated text is returned correctly
    assert called["args"] == ("hola", "es", "EN-GB") # translate_paragraph always uses "EN-GB" as the target language for DeepLTranslator.translate_text

def test_translate_article_rejects_non_dict_input():
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError): # translate_article should raise ValueError on non-dict input
        translate.translate_article(["not", "a", "dict"], "es", translator)

def test_translate_article_tags_paragraphs_with_translated_headings(monkeypatch):
    # bypass real translate_batch entirely; just prefix each text so we can verify translate_article wires section titles, headings and paragraphs correctly
    def fake_batch(self, texts, *args, **kwargs): # stands in for DeepLTranslator.translate_batch; prefix each text with "EN:"
        return ["EN:" + t for t in texts]
    monkeypatch.setattr(translate.DeepLTranslator, "translate_batch", fake_batch)

    translator = translate.DeepLTranslator()
    article = {
        "Introduccion": [
            {"heading": None, "text": "Hola"}
        ],
        "Contenido": [
            {"heading": None, "text": "Texto principal"},
            {"heading": "Subseccion", "text": "Texto de la subseccion"}
        ]
    }
    result = translate.translate_article(article, "es", translator)

    # for Introduccion
    assert result["EN:Introduccion"][0]["translated"] == "EN:Hola" # the paragraph text is translated and prefixed with "EN:"
    assert result["EN:Introduccion"][0]["heading"] is None # the heading is None, so it remains None after translation
    
    # for subsection in Contenido
    tagged = result["EN:Contenido"][1] # the subsection in the "Contenido" section
    assert tagged["translated"] == "EN:Texto de la subseccion" # the paragraph text is translated and prefixed with "EN:"
    assert tagged["heading"] == "EN:Subseccion" # the heading is translated and prefixed with "EN:"

def test_translate_article_returns_empty_for_empty_article(monkeypatch):
    def fail_if_called(*args, **kwargs): # translate API must never be called for an empty article
        raise AssertionError("translate_batch should not be called for an empty article")
    monkeypatch.setattr(translate.DeepLTranslator, "translate_batch", fail_if_called)

    translator = translate.DeepLTranslator()
    assert translate.translate_article({}, "es", translator) == {} # empty article translates to empty output, no API call

def test_translate_article_exempts_lead_from_translation(monkeypatch):
    seen_texts = [] # record every text passed to translate_batch, to prove "Lead" is never sent
    def fake_batch(self, texts, *args, **kwargs): # stands in for translate_batch; prefix each text with "EN:"
        seen_texts.extend(texts)
        return ["EN:" + t for t in texts]
    monkeypatch.setattr(translate.DeepLTranslator, "translate_batch", fake_batch)

    translator = translate.DeepLTranslator()
    article = {
        "Lead": [{"heading": None, "text": "Resumen"}],
        "Historia": [{"heading": None, "text": "Texto"}]
    }
    result = translate.translate_article(article, "es", translator)

    assert "Lead" not in seen_texts # "Lead" must never be sent to DeepL
    assert "Lead" in result # the Lead section survives under its literal, untranslated key
    assert result["Lead"][0]["translated"] == "EN:Resumen" # its paragraphs are still translated normally
    assert result["EN:Historia"][0]["translated"] == "EN:Texto" # a real section title is still translated

def test_translate_article_keeps_colliding_translated_titles_distinct(monkeypatch):
    # two different source titles that translate to the same English string must not merge
    def fake_batch(self, texts, *args, **kwargs): # stands in for translate_batch; map both section titles to "Notes"
        mapping = {"Notas": "Notes", "Apuntes": "Notes"}
        return [mapping.get(t, t) for t in texts]
    monkeypatch.setattr(translate.DeepLTranslator, "translate_batch", fake_batch)

    translator = translate.DeepLTranslator()
    article = {
        "Notas": [{"heading": None, "text": "primera"}],
        "Apuntes": [{"heading": None, "text": "segunda"}]
    }
    result = translate.translate_article(article, "es", translator)

    assert "Notes" in result and "Notes (2)" in result # colliding titles get a numeric suffix instead of merging
    assert len(result) == 2 # both sections survive as distinct keys
    assert result["Notes"][0]["translated"] == "primera" # first section keeps its own paragraph
    assert result["Notes (2)"][0]["translated"] == "segunda" # second section keeps its own paragraph
