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
def fake_env_and_cache(monkeypatch): # monkeypatch the environment and DeepLTranslator cache load/save
    # a fake key is enough (real key/network is never touched, requests.post is
    # mocked per test); cache load/save are no-ops so tests can't pollute the real
    # cache/translations.json on disk
    monkeypatch.setenv("DEEPL_API_KEY", "test-key-not-real")
    monkeypatch.setattr(translate.DeepLTranslator, "_load_cache", lambda self: {}) # return an empty cache
    monkeypatch.setattr(translate.DeepLTranslator, "save_cache", lambda self: None) # save is not an actual file write

# -- DeepLTranslator.__init__ ---------------------------------------------------

def test_init_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    monkeypatch.setattr(translate, "load_dotenv", lambda: None)  # don't let a real .env supply the key
    with pytest.raises(RuntimeError):
        translate.DeepLTranslator()

# -- translate_text ---------------------------------------------------------------

def test_translate_text_happy_path(monkeypatch):
    def fake_post(endpoint, data, headers): # stands in for requests.post; check args and return a fake response
        assert data["text"] == "Hola mundo"
        assert headers["Authorization"] == "DeepL-Auth-Key test-key-not-real"
        return FakeResponse(200, {"translations": [{"text": "Hello world"}]})
    monkeypatch.setattr(translate.requests, "post", fake_post)
    translator = translate.DeepLTranslator()
    assert translator.translate_text("Hola mundo", "es", "EN-GB") == "Hello world"

def test_translate_text_uses_cache_on_second_call(monkeypatch):
    calls = []
    def fake_post(endpoint, data, headers): # stands in for requests.post; check args and return a fake response
        calls.append(data)
        return FakeResponse(200, {"translations": [{"text": "Hello"}]})
    monkeypatch.setattr(translate.requests, "post", fake_post)

    translator = translate.DeepLTranslator()
    first = translator.translate_text("Hola", "es", "EN-GB")
    second = translator.translate_text("Hola", "es", "EN-GB")
    assert first == second == "Hello"
    assert len(calls) == 1  # second call was a cache hit, no second HTTP request

def test_translate_text_raises_on_empty_string():
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError):
        translator.translate_text("", "es", "EN-GB")

def test_translate_text_returns_empty_for_whitespace_only(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not call DeepL for whitespace-only text")
    monkeypatch.setattr(translate.requests, "post", fail_if_called)

    translator = translate.DeepLTranslator()
    assert translator.translate_text("   ", "es", "EN-GB") == ""

def test_translate_text_raises_when_over_deepl_free_tier_limit():
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError):
        translator.translate_text("a" * 5001, "es", "EN-GB")

def test_translate_text_raises_on_unsupported_language(monkeypatch):
    monkeypatch.setattr(translate.requests, "post",
                         lambda *a, **kw: FakeResponse(400, text="Language pair not supported"))
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError):
        translator.translate_text("Hola", "es", "XX")

def test_translate_text_raises_runtime_error_on_server_error(monkeypatch):
    monkeypatch.setattr(translate.requests, "post",
                         lambda *a, **kw: FakeResponse(500, text="Internal Server Error"))
    translator = translate.DeepLTranslator()
    with pytest.raises(RuntimeError):
        translator.translate_text("Hola", "es", "EN-GB")

def test_translate_text_raises_runtime_error_on_connection_failure(monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise translate.requests.RequestException("network down")
    monkeypatch.setattr(translate.requests, "post", raise_connection_error)

    translator = translate.DeepLTranslator()
    with pytest.raises(RuntimeError):
        translator.translate_text("Hola", "es", "EN-GB")

# -- translate_batch --------------------------------------------------------------

def test_translate_batch_only_requests_uncached_texts(monkeypatch):
    calls = []
    def fake_post(endpoint, data, headers):
        calls.append(data["text"])
        return FakeResponse(200, {"translations": [{"text": "World"}]})
    monkeypatch.setattr(translate.requests, "post", fake_post)

    translator = translate.DeepLTranslator()
    # prime the cache directly, as if "Hola" was already translated in an earlier run
    key = translator._cache_key("Hola", "ES", "EN-GB")
    translator.cache[key] = {"original": "Hola", "translated": "Hello"}

    results = translator.translate_batch(["Hola", "Mundo"], "es", "EN-GB")
    assert results == ["Hello", "World"]
    assert calls == [["Mundo"]]  # only the uncached text was actually sent to DeepL

def test_translate_batch_raises_on_empty_list():
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError):
        translator.translate_batch([], "es", "EN-GB")

def test_translate_batch_raises_when_all_whitespace():
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError):
        translator.translate_batch(["  ", ""], "es", "EN-GB")

# -- normalise_lang_code + _cache_key ---------------------------------------------

def test_normalise_lang_code_uppercases():
    translator = translate.DeepLTranslator()
    assert translator.normalise_lang_code("es") == "ES"

def test_normalise_lang_code_maps_simple_to_english():
    translator = translate.DeepLTranslator()
    assert translator.normalise_lang_code("simple") == "EN"
    assert translator.normalise_lang_code("Simple") == "EN"

def test_cache_key_differs_by_language_pair():
    translator = translate.DeepLTranslator()
    key1 = translator._cache_key("Hola", "ES", "EN-GB")
    key2 = translator._cache_key("Hola", "ES", "FR")
    assert key1 != key2

# -- translate_paragraph + translate_article ---------------------------------------

def test_translate_paragraph_delegates_to_translate_text(monkeypatch):
    called = {}
    def fake_translate_text(self, paragraph, src, tgt):
        called["args"] = (paragraph, src, tgt)
        return "translated!"
    monkeypatch.setattr(translate.DeepLTranslator, "translate_text", fake_translate_text)

    translator = translate.DeepLTranslator()
    assert translate.translate_paragraph("hola", "es", translator) == "translated!"
    assert called["args"] == ("hola", "es", "EN-GB")

def test_translate_article_rejects_non_dict_input():
    translator = translate.DeepLTranslator()
    with pytest.raises(ValueError):
        translate.translate_article(["not", "a", "dict"], "es", translator)

def test_translate_article_tags_paragraphs_with_translated_headings(monkeypatch):
    # bypass real translate_batch entirely; just prefix each text so we can verify
    # translate_article wires section titles, headings and paragraphs correctly
    def fake_batch(self, texts, source_lang, target_lang):
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

    assert result["EN:Introduccion"][0]["translated"] == "EN:Hola"
    assert result["EN:Introduccion"][0]["heading"] is None
    tagged = result["EN:Contenido"][1]
    assert tagged["translated"] == "EN:Texto de la subseccion"
    assert tagged["heading"] == "EN:Subseccion"
