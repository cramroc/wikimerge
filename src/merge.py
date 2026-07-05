# import re  # PARKED: only used by the parked _jaccard below
from src import similarity

# DUPLICATE_THRESHOLD = 0.8  # PARKED: only used by the parked paragraph dedup below
SECTION_MATCH_THRESHOLD = 0.5 # cosine threshold for treating two section titles as the same section (embedding similarity; tune on real runs)

# trailing "appendix" sections (already translated to English) in canonical Wikipedia order;
# these are pulled out of the fractional ordering and always placed last, in this order
APPENDIX_ORDER = [
    "see also",
    "notes",
    "footnotes",
    "explanatory notes",
    "references",
    "citations",
    "sources",
    "notes and references",
    "bibliography",
    "works cited",
    "further reading",
    "external links",
    "related articles",
]
APPENDIX_SECTIONS = set(APPENDIX_ORDER) # for fast membership checks

# ---- PARKED: unused since the merge was replaced by analysis-driven rendering ----
# ---- (kept as an inert string in case the flat-merge path is ever restored) ----
'''
def _jaccard(a, b):
    """
    Compute the Jaccard similarity between two strings.
    Input:
        a (str): first string
        b (str): second string
    Output:
        float: Jaccard similarity (0.0 to 1.0)
    """

    # separate text into tokens
    tokens_a = set(re.findall(r"[a-z0-9]+", a.lower()))
    tokens_b = set(re.findall(r"[a-z0-9]+", b.lower()))

    # get union of tokens
    union = tokens_a.union(tokens_b)

    # check if both sets are empty -> return 0.0 to avoid division by zero
    if len(union) == 0:
        return 0.0

    # compute intersection of tokens
    intersection = tokens_a.intersection(tokens_b)

    # compute and return Jaccard similarity
    return len(intersection) / len(union)
'''

def _best_section_match(title, candidate_titles, used):
    """
    Find the candidate section title most similar to `title` (by embedding cosine).
    Input:
        title (str): the section title we want to match
        candidate_titles (list[str]): possible section titles to match against
        used (set): candidate titles already matched (skipped, each used once)
    Output:
        str or None: best-matching title if it clears SECTION_MATCH_THRESHOLD, else None
    """

    # only consider candidates not already matched (each a1 section used once)
    available = [c for c in candidate_titles if c not in used]
    if not available:
        return None

    # cosine similarity of this title against each available candidate title
    scores = similarity.similarity_matrix([title], available)[0]

    # pick the best-scoring candidate; only count it if it clears the threshold
    best = int(scores.argmax())
    if float(scores[best]) >= SECTION_MATCH_THRESHOLD:
        return available[best]
    return None

# ---- PARKED: paragraph dedup, unused since we now keep both editions and group them ----
'''
def _merge_paragraph_lists(list1, list2, section_label):
    """
    Merge two lists of paragraph records from the same (aligned) section:
    keep all of list1, then add list2 paragraphs that are not near-duplicates.
    Input:
        list1 (list[dict]): paragraph records from article 1
        list2 (list[dict]): paragraph records from article 2
        section_label (str): section name (used only in error messages)
    Output:
        list[dict]: combined paragraph records
    """

    # ensure both are lists
    if not isinstance(list1, list):
        raise ValueError("Section " + section_label + " in first argument is not a list")
    if not isinstance(list2, list):
        raise ValueError("Section " + section_label + " in second argument is not a list")

    # keep all of article 1's paragraphs (shallow-copied so inputs are not mutated)
    combined = []
    for p in list1:
        if isinstance(p, dict):
            combined.append(dict(p))
        else:
            raise ValueError("Paragraph in section " + section_label + " in first argument is not a dictionary")

    # add article 2's paragraphs only if not a near-duplicate of one already kept
    for p in list2:
        if not isinstance(p, dict):
            raise ValueError("Paragraph in section " + section_label + " in second argument is not a dictionary")
        # skip article 2 paragraphs that near-duplicate one already kept
        p_candidate = p["translated"]
        is_duplicate = False
        for kept in combined:
            if _jaccard(p_candidate, kept["translated"]) >= DUPLICATE_THRESHOLD:
                is_duplicate = True
                break
        if not is_duplicate:
            combined.append(dict(p))

    # return merged paragraph list
    return combined
'''

def _is_appendix(title):
    # is this a trailing "appendix" section (see also, references, external links, ...)?
    return title.strip().lower() in APPENDIX_SECTIONS

def _appendix_rank(title):
    # position of an appendix title in the canonical order (unknown ones sort after known)
    t = title.strip().lower()
    return APPENDIX_ORDER.index(t) if t in APPENDIX_SECTIONS else len(APPENDIX_ORDER)

def pair_sections(a1, a2):
    """
    Pair up sections across two articles by title similarity (shared by merge and analysis).
    Input:
        a1, a2 (dict): articles (section -> list of paragraph records)
    Output:
        list of (title, a1_key, a2_key): content sections ordered by their average
        fractional position in the source articles, then appendix sections (See also,
        References, External links, ...) always last in canonical order; a1_key / a2_key
        is the section name in that article, or None if only one article has it
    """
    # non-Lead section titles for each article (Lead is handled on its own)
    a1_sections = [s for s in a1.keys() if s != "Lead"]
    a2_sections = [s for s in a2.keys() if s != "Lead"]

    # match each article-2 section to its most similar article-1 section (each a1 used once)
    a2_to_a1 = {} # maps an a2 section title -> the a1 section it pairs with (or None)
    claimed_a1 = set()
    for a2_sec in a2_sections:
        match = _best_section_match(a2_sec, a1_sections, claimed_a1)
        a2_to_a1[a2_sec] = match
        if match is not None:
            claimed_a1.add(match)

    # build the pairing (Lead, a1 sections with their match, then unmatched a2 sections)
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

    # order sections by their average FRACTIONAL position in the source articles, so
    # appendices (See also / References / etc.) sort last. Normalising each index by the
    # article's section count makes position comparable across articles of different
    # lengths (0.0 = start, 1.0 = end) — which raw absolute indices don't.
    a1_index = {title: i for i, title in enumerate(a1.keys())}
    a2_index = {title: i for i, title in enumerate(a2.keys())}
    def position(pair):
        _, a1_key, a2_key = pair
        fracs = []
        if a1_key is not None:
            fracs.append(a1_index[a1_key] / max(len(a1) - 1, 1)) # 0.0 = first, 1.0 = last
        if a2_key is not None:
            fracs.append(a2_index[a2_key] / max(len(a2) - 1, 1))
        return sum(fracs) / len(fracs) # average across the editions that have this section

    # split appendix sections out: content is ordered by fractional position, then the
    # appendices always follow, in canonical Wikipedia order (regardless of position)
    content = [p for p in pairs if not _is_appendix(p[0])]
    appendix = [p for p in pairs if _is_appendix(p[0])]
    content.sort(key=position)
    appendix.sort(key=lambda p: _appendix_rank(p[0]))

    return content + appendix

# ---- PARKED: flat merge + its __main__ test, replaced by analysis-driven rendering ----
'''
def merge_articles(a1: dict, a2: dict):
    """
    Merge two translated Wikipedia articles.
    Input:
        a1 (dict): translated_article from language 1
        a2 (dict): translated_article from language 2
    Output:
        dict: merged sections -> list of paragraph records
              (order: Lead first, then article 1's sections (each enriched with the
               article 2 section that matched it by title similarity), then any
               article 2 sections that matched nothing;
               within a section: paragraphs from a1 first, then a2's non-duplicates)
    """

    # ensure both input are not empty
    if a1 is None: raise ValueError("First argument is None")
    if a2 is None: raise ValueError("Second argument is None")
    # ensure both input are dicts
    if not isinstance(a1, dict):
        raise ValueError("First argument is not a dictionary")
    if not isinstance(a2, dict):
        raise ValueError("Second argument is not a dictionary")

    # pair sections across the two articles, then merge each pair's paragraph lists
    merged = {}
    for title, a1_key, a2_key in pair_sections(a1, a2):
        list1 = a1.get(a1_key, []) if a1_key else []
        list2 = a2.get(a2_key, []) if a2_key else []
        merged[title] = _merge_paragraph_lists(list1, list2, title)

    # return merged dict: dict[str, list[dict[str, str]]]
    return merged

if __name__ == "__main__":
    # test data (section titles already translated to English, as in the real pipeline)
    a1 = {
        "Lead": [
            {"lang": "ES", "original": "París es la capital de Francia.", "translated": "Paris is the capital of France.", "idx": 0}
        ],
        "History": [
            {"lang": "ES", "original": "Fue fundada en la antigüedad.", "translated": "The city was founded in ancient times.", "idx": 0}
        ]
    }

    a2 = {
        "Lead": [
            # near-duplicate of a1's Lead -> should be deduped away
            {"lang": "FR", "original": "Paris est la capitale de la France.", "translated": "Paris is the capital of France.", "idx": 0}
        ],
        "Early history": [
            # different title, should align with a1's "History"
            {"lang": "FR", "original": "Elle possède de nombreux musées.", "translated": "It also has many museums.", "idx": 0}
        ],
        "Geography": [
            # no matching a1 section -> kept on its own
            {"lang": "FR", "original": "Paris est sur la Seine.", "translated": "Paris sits on the Seine river.", "idx": 0}
        ]
    }

    # test merge_articles
    merged = merge_articles(a1, a2)

    print("Merged article sections and paragraphs:")
    for section, paragraphs in merged.items():
        print("Section: " + section)
        for record in paragraphs:
            print(" -", record["translated"])
'''
