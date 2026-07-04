# imports
from sentence_transformers import SentenceTransformer, util
from src.merge import _best_section_match

EMBED_MODEL = "all-MiniLM-L6-v2" # embedding model for symmetric semantic similarity (for now: small, fast, CPU-friendly)
AGREE_THRESHOLD = 0.5 # cosine threshold above which two paragraphs are treated as the same point ("agree" candidate)

# lazy method so model is loaded once and reused (loading takes a few seconds)
_model = None
def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model

# pair sections across the two articles by title similarity (reuses matcher from merge.py)
def _pair_sections(a1, a2):
    """
    Pair up sections across two articles.
    Input:
        a1, a2 (dict): translated articles (section -> list of paragraph records)
    Output:
        list of (title, a1_key, a2_key): section pairing in output order, where
        a1_key / a2_key is the section name in each article (or None if absent)
    """
    # non-Lead section titles for each article (Lead is handled separately)
    a1_sections = [s for s in a1 if s != "Lead"]
    a2_sections = [s for s in a2 if s != "Lead"]

    # match each a2 section to its most similar a1 section (each a1 used at most once)
    a2_to_a1 = {}
    claimed = set()
    for a2_sec in a2_sections:
        match = _best_section_match(a2_sec, a1_sections, claimed)
        a2_to_a1[a2_sec] = match
        if match is not None:
            claimed.add(match)

    # build ordered pairing: Lead, then a1 sections (with their match), then unmatched a2 sections
    pairs = []
    if "Lead" in a1 or "Lead" in a2:
        pairs.append(("Lead", "Lead" if "Lead" in a1 else None, "Lead" if "Lead" in a2 else None))
    for a1_sec in a1_sections:
        matched_a2 = None
        for a2_sec, target in a2_to_a1.items():
            if target == a1_sec:
                matched_a2 = a2_sec
                break
        pairs.append((a1_sec, a1_sec, matched_a2))
    for a2_sec in a2_sections:
        if a2_to_a1[a2_sec] is None:
            pairs.append((a2_sec, None, a2_sec))
    return pairs

# analyse a single (aligned) section: which paragraphs agree, which are unique to each article
def _analyse_section(list1, list2):
    """
    Input:
        list1, list2 (list[dict]): paragraph records from the two articles' matched section
    Output:
        dict: {"agree": [{"a1", "a2", "score"}], "unique_a1": [...], "unique_a2": [...]}
    """
    # section present in only one article -> everything there is unique
    if not list1:
        return {"agree": [], "unique_a1": [], "unique_a2": list(list2)}
    if not list2:
        return {"agree": [], "unique_a1": list(list1), "unique_a2": []}

    # embed the english (translated) text of each paragraph
    model = _get_model()
    emb1 = model.encode([r["translated"] for r in list1])
    emb2 = model.encode([r["translated"] for r in list2])

    # cross-article cosine similarity matrix
    sim = util.cos_sim(emb1, emb2)

    # best counterpart in each direction
    best_j_for_i = sim.argmax(dim=1) # for each a1 paragraph, index of its best a2 paragraph
    best_i_for_j = sim.argmax(dim=0) # for each a2 paragraph, index of its best a1 paragraph

    # keep only mutual best matches above the threshold -> agree; everything else -> unique
    agree = []
    matched_i = set()
    matched_j = set()
    for i in range(len(list1)):
        j = int(best_j_for_i[i])
        if int(best_i_for_j[j]) == i and float(sim[i][j]) >= AGREE_THRESHOLD:
            agree.append({"a1": list1[i], "a2": list2[j], "score": round(float(sim[i][j]), 3)})
            matched_i.add(i)
            matched_j.add(j)

    # paragraphs that didn't get a mutual match are unique to their article
    unique_a1 = [list1[i] for i in range(len(list1)) if i not in matched_i]
    unique_a2 = [list2[j] for j in range(len(list2)) if j not in matched_j]
    return {"agree": agree, "unique_a1": unique_a1, "unique_a2": unique_a2}

# main: per-section agree / unique-per-language analysis of two translated articles
def analyze_articles(a1, a2):
    """
    Input:
        a1, a2 (dict): translated articles (section -> list of paragraph records),
                       as produced by translate_article (BEFORE merging, so dedup
                       hasn't removed the overlapping paragraphs we want to find)
    Output:
        dict: section title -> {"agree": [...], "unique_a1": [...], "unique_a2": [...]}
    """
    analysis = {}
    for title, a1_key, a2_key in _pair_sections(a1, a2):
        list1 = a1.get(a1_key, []) if a1_key else []
        list2 = a2.get(a2_key, []) if a2_key else []
        analysis[title] = _analyse_section(list1, list2)
    return analysis

# testing (run from project root: python -m src.analysis)
if __name__ == "__main__":
    # small demo: a paraphrase pair that SHOULD match (different words, same meaning),
    # plus content unique to each article, plus sections that only one article has
    a1 = {
        "Lead": [
            {"lang": "ES", "translated": "The domestic cat is a small carnivorous mammal.", "idx": 0},
            {"lang": "ES", "translated": "Cats were first domesticated in the Near East.", "idx": 1}
        ],
        "Diet": [
            {"lang": "ES", "translated": "Cats are obligate carnivores and must eat meat.", "idx": 0}
        ]
    }
    a2 = {
        "Lead": [
            {"lang": "FR", "translated": "Cats are little meat-eating animals often kept as pets.", "idx": 0},
            {"lang": "FR", "translated": "The species is extremely popular all over the world.", "idx": 1}
        ],
        "Behaviour": [
            {"lang": "FR", "translated": "Cats sleep for many hours every day.", "idx": 0}
        ]
    }

    result = analyze_articles(a1, a2)
    for section, r in result.items():
        print("== " + section + " ==")
        for pair in r["agree"]:
            print("  AGREE (score %.3f):" % pair["score"])
            print("    [" + pair["a1"]["lang"] + "] " + pair["a1"]["translated"])
            print("    [" + pair["a2"]["lang"] + "] " + pair["a2"]["translated"])
        for rec in r["unique_a1"]:
            print("  ONLY [" + rec["lang"] + "] " + rec["translated"])
        for rec in r["unique_a2"]:
            print("  ONLY [" + rec["lang"] + "] " + rec["translated"])
