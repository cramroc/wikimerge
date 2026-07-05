# tests for src/analysis.py: the agree/contradict/neutral/unique bucketing logic.
# similarity.similarity_matrix is mocked the same way as in test_merge.py (exact-text
# match = candidate pair), and nli.classify_bidirectional is mocked per test to control
# which label a candidate pair gets -- neither the real embedding nor NLI model loads here.
import torch
import pytest
from src import analysis

@pytest.fixture(autouse=True)
def fake_similarity(monkeypatch):
    # stand-in: two texts are a "candidate" pair only if they're identical (case-insensitive)
    def fake_similarity_matrix(texts_a, texts_b):
        return torch.tensor([
            [1.0 if a.strip().lower() == b.strip().lower() else 0.0 for b in texts_b]
            for a in texts_a
        ])
    monkeypatch.setattr(analysis.similarity, "similarity_matrix", fake_similarity_matrix)

# -- _analyse_section ----------------------------------------------------------

def test_empty_list1_everything_is_unique_to_a2():
    list2 = [{"translated": "Only in a2", "lang": "FR"}]
    result = analysis._analyse_section([], list2)
    assert result["unique_a1"] == []
    assert result["unique_a2"] == list2
    assert result["agree"] == [] and result["contradict"] == [] and result["neutral"] == []

def test_empty_list2_everything_is_unique_to_a1():
    list1 = [{"translated": "Only in a1", "lang": "ES"}]
    result = analysis._analyse_section(list1, [])
    assert result["unique_a1"] == list1
    assert result["unique_a2"] == []

def test_candidate_pair_labeled_agree_when_nli_says_entailment(monkeypatch):
    monkeypatch.setattr(analysis.nli, "classify_bidirectional", lambda a, b: "entailment")
    list1 = [{"translated": "Cats are mammals.", "lang": "ES"}]
    list2 = [{"translated": "Cats are mammals.", "lang": "FR"}]
    result = analysis._analyse_section(list1, list2)
    assert len(result["agree"]) == 1
    assert result["agree"][0]["a1"] == list1[0]
    assert result["agree"][0]["a2"] == list2[0]
    assert result["contradict"] == [] and result["neutral"] == []
    assert result["unique_a1"] == [] and result["unique_a2"] == []

def test_candidate_pair_labeled_contradict_when_nli_says_contradiction(monkeypatch):
    monkeypatch.setattr(analysis.nli, "classify_bidirectional", lambda a, b: "contradiction")
    list1 = [{"translated": "Built in 1932.", "lang": "ES"}]
    list2 = [{"translated": "Built in 1932.", "lang": "FR"}]
    result = analysis._analyse_section(list1, list2)
    assert len(result["contradict"]) == 1
    assert result["agree"] == [] and result["neutral"] == []

def test_candidate_pair_labeled_neutral_when_nli_says_neutral(monkeypatch):
    monkeypatch.setattr(analysis.nli, "classify_bidirectional", lambda a, b: "neutral")
    list1 = [{"translated": "Same topic sentence.", "lang": "ES"}]
    list2 = [{"translated": "Same topic sentence.", "lang": "FR"}]
    result = analysis._analyse_section(list1, list2)
    assert len(result["neutral"]) == 1
    assert result["agree"] == [] and result["contradict"] == []

def test_non_matching_paragraphs_stay_unique_and_skip_nli(monkeypatch):
    # nli shouldn't even be asked about pairs that never cleared the similarity threshold
    calls = []
    monkeypatch.setattr(analysis.nli, "classify_bidirectional", lambda a, b: calls.append((a, b)) or "entailment")
    list1 = [{"translated": "A", "lang": "ES"}]
    list2 = [{"translated": "B", "lang": "FR"}]
    result = analysis._analyse_section(list1, list2)
    assert result["unique_a1"] == list1
    assert result["unique_a2"] == list2
    assert result["agree"] == [] and result["contradict"] == [] and result["neutral"] == []
    assert calls == []

def test_mixed_section_splits_matches_from_uniques(monkeypatch):
    monkeypatch.setattr(analysis.nli, "classify_bidirectional", lambda a, b: "entailment")
    list1 = [{"translated": "Same text", "lang": "ES"}, {"translated": "Only in ES", "lang": "ES"}]
    list2 = [{"translated": "Same text", "lang": "FR"}, {"translated": "Only in FR", "lang": "FR"}]
    result = analysis._analyse_section(list1, list2)
    assert len(result["agree"]) == 1
    assert result["agree"][0]["a1"]["translated"] == "Same text"
    assert result["unique_a1"] == [list1[1]]
    assert result["unique_a2"] == [list2[1]]

# -- analyze_articles (wires pair_sections + _analyse_section together) -----------

def test_analyze_articles_keys_output_by_section_title(monkeypatch):
    monkeypatch.setattr(analysis.nli, "classify_bidirectional", lambda a, b: "entailment")
    a1 = {"Lead": [{"translated": "Cats are mammals.", "lang": "ES"}]}
    a2 = {"Lead": [{"translated": "Cats are mammals.", "lang": "FR"}]}
    result = analysis.analyze_articles(a1, a2)
    assert "Lead" in result
    assert len(result["Lead"]["agree"]) == 1
    assert result["Lead"]["agree"][0]["a1"]["lang"] == "ES"
    assert result["Lead"]["agree"][0]["a2"]["lang"] == "FR"
