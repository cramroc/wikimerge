# tests for src/merge.py's pair_sections: title alignment + section ordering.
# similarity.similarity_matrix is mocked to an exact-title-match stand-in for all
# tests here, since the real embedding model is slow and non-deterministic to pin
# down in a unit test -- that belongs to similarity.py's own tests, not this one.
import torch
import pytest
from src import merge

@pytest.fixture(autouse=True)
def fake_similarity(monkeypatch):
    # stand-in: two titles "match" only if they're the same text (case-insensitive)
    def fake_similarity_matrix(texts_a, texts_b):
        return torch.tensor([
            [1.0 if a.strip().lower() == b.strip().lower() else 0.0 for b in texts_b]
            for a in texts_a
        ])
    monkeypatch.setattr(merge.similarity, "similarity_matrix", fake_similarity_matrix)

def test_lead_is_always_first():
    a1 = {"Lead": [], "History": []}
    a2 = {"Lead": [], "History": []}
    pairs = merge.pair_sections(a1, a2)
    assert pairs[0][0] == "Lead"

def test_exact_title_matches_pair_up_across_articles():
    a1 = {"Lead": [], "History": [], "Geography": []}
    a2 = {"Lead": [], "History": [], "Geography": []}
    by_title = {title: (a1_key, a2_key) for title, a1_key, a2_key in merge.pair_sections(a1, a2)}
    assert by_title["History"] == ("History", "History")
    assert by_title["Geography"] == ("Geography", "Geography")

def test_unmatched_sections_get_none_on_the_missing_side():
    a1 = {"Lead": [], "Diet": []}
    a2 = {"Lead": [], "Behaviour": []}
    by_title = {title: (a1_key, a2_key) for title, a1_key, a2_key in merge.pair_sections(a1, a2)}
    assert by_title["Diet"] == ("Diet", None)
    assert by_title["Behaviour"] == (None, "Behaviour")

def test_appendix_sections_are_pinned_last_in_canonical_order():
    # "External links" comes before "See also" in the raw article, but the canonical
    # order (APPENDIX_ORDER) says See also should render first regardless
    a1 = {"Lead": [], "History": [], "External links": [], "See also": []}
    a2 = {"Lead": [], "History": []}
    titles_in_order = [title for title, _, _ in merge.pair_sections(a1, a2)]
    assert titles_in_order.index("History") < titles_in_order.index("See also")
    assert titles_in_order.index("See also") < titles_in_order.index("External links")

def test_content_sections_ordered_by_fractional_position():
    # "Diet" sits proportionally earlier in a1 than "Habitat" does in a2, and neither
    # has a same-named counterpart in the other article, so fractional position alone
    # should decide which comes first
    a1 = {"Lead": [], "Diet": [], "Reproduction": [], "Conservation": []}
    a2 = {"Lead": [], "Range": [], "Habitat": []}
    titles_in_order = [title for title, _, _ in merge.pair_sections(a1, a2)]
    assert titles_in_order.index("Diet") < titles_in_order.index("Habitat")
