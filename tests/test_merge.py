# tests for src/merge.py's pair_sections: title alignment + section ordering.

# similarity.similarity_matrix is mocked to an exact-title-match stand-in for all
# tests here, since the real embedding model is slow and non-deterministic to pin
# down in a unit test -- that belongs to similarity.py's own tests, not this one.

import torch
import pytest
from src import merge

@pytest.fixture(autouse=True) # applies to all tests in this module
def fake_similarity(monkeypatch):
    # stand-in: two titles "match" only if they're the same text (case-insensitive)
    def fake_similarity_matrix(texts_a, texts_b):
        return torch.tensor([
            [1.0 if a.strip().lower() == b.strip().lower() else 0.0 for b in texts_b]
            for a in texts_a
        ])
    # replace similarity_matrix with fake stand-in
    monkeypatch.setattr(merge.similarity, "similarity_matrix", fake_similarity_matrix) 

def test_lead_is_always_first():
    a1 = {"Lead": [], "History": []}
    a2 = {"Lead": [], "History": []}
    pairs = merge.pair_sections(a1, a2)
    assert pairs[0][0] == "Lead" # the first title in the output is always "Lead"

def test_exact_title_matches_pair_up_across_articles():
    a1 = {"Lead": [], "History": [], "Geography": []}
    a2 = {"Lead": [], "History": [], "Geography": []}
    by_title = {title: (a1_key, a2_key) for title, a1_key, a2_key in merge.pair_sections(a1, a2)}
    assert by_title["History"] == ("History", "History") # exact title matches pair up across articles
    assert by_title["Geography"] == ("Geography", "Geography") # same objective as previous line

def test_unmatched_sections_get_none_on_the_missing_side():
    a1 = {"Lead": [], "Diet": []}
    a2 = {"Lead": [], "Behaviour": []}
    by_title = {title: (a1_key, a2_key) for title, a1_key, a2_key in merge.pair_sections(a1, a2)}
    assert by_title["Diet"] == ("Diet", None) # unmatched sections get None on the missing side
    assert by_title["Behaviour"] == (None, "Behaviour") # same objective as previous line

def test_appendix_sections_are_pinned_last_in_canonical_order():
    # "External links" comes before "See also" in the raw article, but the canonical
    # order (APPENDIX_ORDER) says See also should render first regardless
    a1 = {"Lead": [], "History": [], "External links": [], "See also": []}
    a2 = {"Lead": [], "History": []}
    titles_in_order = [title for title, _, _ in merge.pair_sections(a1, a2)]
    assert titles_in_order.index("History") < titles_in_order.index("See also") # Content section comes before appendix sections
    assert titles_in_order.index("See also") < titles_in_order.index("External links") # Appendix sections are pinned in predetermined order

def test_content_sections_ordered_by_fractional_position():
    # "Diet" sits proportionally earlier in a1 than "Habitat" does in a2, and neither
    # has a same-named counterpart in the other article, so fractional position alone
    # should decide which comes first
    a1 = {"Lead": [], "Diet": [], "Reproduction": [], "Conservation": []}
    a2 = {"Lead": [], "Range": [], "Habitat": []}
    titles_in_order = [title for title, _, _ in merge.pair_sections(a1, a2)]
    assert titles_in_order.index("Diet") < titles_in_order.index("Habitat") # Diet comes before Habitat (because it sits proportionally earlier in a1 than Habitat does in a2)

def test_section_matching_is_mutual_best_not_greedy(monkeypatch):
    # Test for asymmetric similarities that a greedy vs. mutual match would resolve differently
    scores = {
        ("Alpha", "X"): 0.90, ("Alpha", "Y"): 0.95,
        ("Beta", "X"): 0.55, ("Beta", "Y"): 0.40,
    }
    def fake_similarity_matrix(texts_a, texts_b): # per-test override; defaults to 0.0 (so appendix matching sees no appendices)
        return torch.tensor([[scores.get((a, b), 0.0) for b in texts_b] for a in texts_a])
    monkeypatch.setattr(merge.similarity, "similarity_matrix", fake_similarity_matrix)

    a1 = {"Alpha": [], "Beta": []}
    a2 = {"X": [], "Y": []}
    by_title = {title: (a1_key, a2_key) for title, a1_key, a2_key in merge.pair_sections(a1, a2)}
    assert by_title["Alpha"] == ("Alpha", "Y") # mutual best match pairs Alpha with Y (0.95), not greedy's X (0.90)
    assert by_title["X"] == (None, "X") # X is left unmatched, because Alpha (its best) preferred Y
    assert by_title["Beta"] == ("Beta", None) # Beta's only candidate X is not its mutual best, so Beta stays unmatched

def test_translated_appendix_title_is_pinned_last(monkeypatch):
    # Test for non-English article's appendix heading translating inexactly to canonical appendix section headers in English.
    # E.g.: "Einzelnachweise" (German) to "Individual evidence" -> map to English "references".
    # Matching appendices by embedding similarity still recognises it and pins it last, after content sections.
    scores = {
        ("History", "History"): 1.0, # section matching: History aligns across the two articles
        ("Individual evidence", "references"): 0.9, # appendix matching: recognised as an appendix
    }
    def fake_similarity_matrix(texts_a, texts_b): # per-test override; everything else defaults to 0.0
        return torch.tensor([[scores.get((a, b), 0.0) for b in texts_b] for a in texts_a])
    monkeypatch.setattr(merge.similarity, "similarity_matrix", fake_similarity_matrix)

    a1 = {"Lead": [], "History": [], "Individual evidence": []}
    a2 = {"Lead": [], "History": []}
    titles_in_order = [title for title, _, _ in merge.pair_sections(a1, a2)]
    assert titles_in_order[-1] == "Individual evidence" # matched to "references" by similarity, so pinned last
    assert titles_in_order.index("History") < titles_in_order.index("Individual evidence") # after the content section
