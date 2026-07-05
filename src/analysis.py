# imports
from src import similarity
from src import nli
from src.merge import pair_sections

AGREE_THRESHOLD = 0.5 # cosine threshold above which two paragraphs are treated as the same point ("candidate" pair, before NLI relabels it)

# analyse a single (aligned) section: which paragraphs agree, contradict, are merely
# related (neutral), or are unique to each article
def _analyse_section(list1, list2):
    """
    Input:
        list1, list2 (list[dict]): paragraph records from the two articles' matched section
    Output:
        dict: {"agree": [...], "contradict": [...], "neutral": [...],
               "unique_a1": [...], "unique_a2": [...]}
               each pair record in agree/contradict/neutral is {"a1", "a2", "score"}
    """
    # section present in only one article -> everything there is unique
    if not list1:
        return {"agree": [], "contradict": [], "neutral": [], "unique_a1": [], "unique_a2": list(list2)}
    if not list2:
        return {"agree": [], "contradict": [], "neutral": [], "unique_a1": list(list1), "unique_a2": []}

    # cross-article cosine similarity matrix (embeds each side's translated text)
    sim = similarity.similarity_matrix(
        [r["translated"] for r in list1],
        [r["translated"] for r in list2]
    )

    # best counterpart in each direction
    best_j_for_i = sim.argmax(dim=1) # for each a1 paragraph, index of its best a2 paragraph
    best_i_for_j = sim.argmax(dim=0) # for each a2 paragraph, index of its best a1 paragraph

    # mutual best matches above the threshold are "candidate" pairs -> NLI relabels each
    # one as agree (entailment), contradict, or neutral (related but not a shared claim);
    # everything else stays unique to its article
    agree = []
    contradict = []
    neutral = []
    matched_i = set()
    matched_j = set()
    for i in range(len(list1)):
        j = int(best_j_for_i[i])
        if int(best_i_for_j[j]) == i and float(sim[i][j]) >= AGREE_THRESHOLD:
            matched_i.add(i)
            matched_j.add(j)
            pair = {"a1": list1[i], "a2": list2[j], "score": round(float(sim[i][j]), 3)}
            label = nli.classify_bidirectional(list1[i]["translated"], list2[j]["translated"])
            if label == "contradiction":
                contradict.append(pair)
            elif label == "entailment":
                agree.append(pair)
            else:
                neutral.append(pair)

    # paragraphs that didn't get a mutual match are unique to their article
    unique_a1 = [list1[i] for i in range(len(list1)) if i not in matched_i]
    unique_a2 = [list2[j] for j in range(len(list2)) if j not in matched_j]
    return {"agree": agree, "contradict": contradict, "neutral": neutral,
            "unique_a1": unique_a1, "unique_a2": unique_a2}

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
    for title, a1_key, a2_key in pair_sections(a1, a2):
        list1 = a1.get(a1_key, []) if a1_key else []
        list2 = a2.get(a2_key, []) if a2_key else []
        analysis[title] = _analyse_section(list1, list2)
    return analysis

# testing (run from project root: python -m src.analysis)
if __name__ == "__main__":
    # small demo: a paraphrase pair that SHOULD match (different words, same meaning),
    # a pair that contradicts (same claim, conflicting fact), content unique to each
    # article, and a section that only one article has
    a1 = {
        "Lead": [
            {"lang": "ES", "translated": "The domestic cat is a small carnivorous mammal.", "idx": 0},
            {"lang": "ES", "translated": "Cats were first domesticated in the Near East.", "idx": 1}
        ],
        "Diet": [
            {"lang": "ES", "translated": "Cats are obligate carnivores and must eat meat.", "idx": 0}
        ],
        "History": [
            {"lang": "ES", "translated": "The breed was first recognised in 1932.", "idx": 0}
        ]
    }
    a2 = {
        "Lead": [
            {"lang": "FR", "translated": "Cats are little meat-eating animals often kept as pets.", "idx": 0},
            {"lang": "FR", "translated": "The species is extremely popular all over the world.", "idx": 1}
        ],
        "Behaviour": [
            {"lang": "FR", "translated": "Cats sleep for many hours every day.", "idx": 0}
        ],
        "History": [
            {"lang": "FR", "translated": "The breed was first recognised in 1965.", "idx": 0}
        ]
    }

    result = analyze_articles(a1, a2)
    for section, r in result.items():
        print("== " + section + " ==")
        for pair in r["agree"]:
            print("  AGREE (score %.3f):" % pair["score"])
            print("    [" + pair["a1"]["lang"] + "] " + pair["a1"]["translated"])
            print("    [" + pair["a2"]["lang"] + "] " + pair["a2"]["translated"])
        for pair in r["contradict"]:
            print("  CONTRADICT (score %.3f):" % pair["score"])
            print("    [" + pair["a1"]["lang"] + "] " + pair["a1"]["translated"])
            print("    [" + pair["a2"]["lang"] + "] " + pair["a2"]["translated"])
        for pair in r["neutral"]:
            print("  NEUTRAL (score %.3f):" % pair["score"])
            print("    [" + pair["a1"]["lang"] + "] " + pair["a1"]["translated"])
            print("    [" + pair["a2"]["lang"] + "] " + pair["a2"]["translated"])
        for rec in r["unique_a1"]:
            print("  ONLY [" + rec["lang"] + "] " + rec["translated"])
        for rec in r["unique_a2"]:
            print("  ONLY [" + rec["lang"] + "] " + rec["translated"])
