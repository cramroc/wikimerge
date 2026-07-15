from src import similarity

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
