# tests for src/article.py's pure URL-parsing functions (no network calls needed)
import pytest
from src.article import url_check, url_to_title, url_to_lang

# -- url_check ----------------------------------------------------------------

def test_url_check_accepts_a_normal_wikipedia_url():
    # should not raise
    url_check("https://es.wikipedia.org/wiki/Boina")

def test_url_check_rejects_non_string():
    with pytest.raises(ValueError):
        url_check(12345)

def test_url_check_rejects_missing_scheme():
    with pytest.raises(ValueError):
        url_check("es.wikipedia.org/wiki/Boina")

def test_url_check_rejects_non_http_scheme():
    with pytest.raises(ValueError):
        url_check("ftp://es.wikipedia.org/wiki/Boina")

def test_url_check_rejects_non_wikipedia_host():
    with pytest.raises(ValueError):
        url_check("https://example.com/wiki/Boina")

def test_url_check_rejects_wrong_path():
    with pytest.raises(ValueError):
        url_check("https://es.wikipedia.org/notwiki/Boina")

# -- url_to_title ---------------------------------------------------------------

def test_url_to_title_extracts_and_cleans_title():
    assert url_to_title("https://es.wikipedia.org/wiki/Boina") == "Boina"

def test_url_to_title_unquotes_and_replaces_underscores_with_spaces():
    assert url_to_title("https://fr.wikipedia.org/wiki/B%C3%A9ret_basque") == "Béret basque"

def test_url_to_title_handles_trailing_slash():
    assert url_to_title("https://es.wikipedia.org/wiki/Boina/") == "Boina"

def test_url_to_title_raises_when_title_segment_missing():
    with pytest.raises(ValueError):
        url_to_title("https://es.wikipedia.org/wiki/")

# -- url_to_lang ----------------------------------------------------------------

def test_url_to_lang_extracts_subdomain_lowercased():
    assert url_to_lang("https://ES.wikipedia.org/wiki/Boina") == "es"

def test_url_to_lang_rejects_www_prefix():
    with pytest.raises(ValueError):
        url_to_lang("https://www.wikipedia.org/wiki/Boina")

def test_url_to_lang_rejects_missing_subdomain():
    with pytest.raises(ValueError):
        url_to_lang("https://wikipedia.org/wiki/Boina")
