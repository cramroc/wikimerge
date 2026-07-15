from src import similarity

SECTION_MATCH_THRESHOLD = 0.5 # cosine threshold for treating two section titles as the same section (embedding similarity; tune on real runs)

# trailing "appendix" sections (in English) in canonical Wikipedia order;
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

# decide, for each section title, if it is an "appendix" section.
# if so -> decide where it ranks in the canonical order by matching against APPENDIX_ORDER.
# Match by embedding similarity against APPENDIX_ORDER (so inexact translated variants are still recognised as appendix sections).
#   Input:  titles (list[str]) -- the section titles to classify
#   Output: dict title -> index into APPENDIX_ORDER of its closest canonical appendix name
#           (that index doubles as the sort rank), or None if nothing clears the threshold
#           (meaning "this is a normal content section, not an appendix")
def _appendix_matches(titles):
    # nothing to classify -> empty map (also avoids calling the model with an empty list)
    if not titles:
        return {}

    # sim[i][k] = cosine similarity between titles[i] and APPENDIX_ORDER[k].
    sim = similarity.similarity_matrix(titles, APPENDIX_ORDER)

    # for each title (row i), find the column of its single most-similar appendix name
    best_idx = sim.argmax(dim=1) # best_idx[i] = index k of the best appendix match for titles[i]

    # keep that appendix index only if the match is strong enough; otherwise map to None (title is not an appendix)
    return {
        title: (
            int(best_idx[i])
            if float(sim[i][int(best_idx[i])]) >= SECTION_MATCH_THRESHOLD
            else None
        )
        for i, title in enumerate(titles)
    }

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
    # non-Lead section titles for each article (Lead is handled on its own, always first)
    a1_sections = [s for s in a1.keys() if s != "Lead"]
    a2_sections = [s for s in a2.keys() if s != "Lead"]

    # --- match sections across the two articles by title similarity using MUTUAL best match

    a2_to_a1 = {a2_sec: None for a2_sec in a2_sections} # a2 section title -> the a1 title it pairs with (None = unmatched)
    if a1_sections and a2_sections: # similarity_matrix needs both sides non-empty
        sim = similarity.similarity_matrix(a1_sections, a2_sections)
        best_j_for_i = sim.argmax(dim=1) # best_j_for_i[i] = index of the a2 section most similar to a1 section i
        best_i_for_j = sim.argmax(dim=0) # best_i_for_j[j] = index of the a1 section most similar to a2 section j
        for i in range(len(a1_sections)):
            j = int(best_j_for_i[i]) # a1 section i's favourite a2 section is j
            # pair them only if a2 section j's favourite is also a1 section i (mutual)
            # AND if the similarity is high enough
            if int(best_i_for_j[j]) == i and float(sim[i][j]) >= SECTION_MATCH_THRESHOLD:
                a2_to_a1[a2_sections[j]] = a1_sections[i]

    # invert the mapping so we can look up "which a2 section did this a1 section pair with?" directly
    a1_to_a2 = {a1_sec: a2_sec for a2_sec, a1_sec in a2_to_a1.items() if a1_sec is not None}

    # --- assemble the list of (title, a1_key, a2_key) pairs
    pairs = []
    # Lead always comes first
    if "Lead" in a1 or "Lead" in a2:
        pairs.append(("Lead", "Lead" if "Lead" in a1 else None, "Lead" if "Lead" in a2 else None))
    # every a1 section, tagged with the a2 section it matched (or None if it matched nothing)
    for a1_sec in a1_sections:
        pairs.append((a1_sec, a1_sec, a1_to_a2.get(a1_sec)))
    # a2 sections that matched no a1 section appear on their own (a1_key = None)
    for a2_sec in a2_sections:
        if a2_to_a1[a2_sec] is None:
            pairs.append((a2_sec, None, a2_sec))

    # --- ordering: content by fractional position, appendices pinned last
    a1_index = {title: i for i, title in enumerate(a1.keys())} # section title -> its absolute position in a1
    a2_index = {title: i for i, title in enumerate(a2.keys())} # section title -> its absolute position in a2
    def position(pair):
        _, a1_key, a2_key = pair
        fracs = []
        if a1_key is not None:
            fracs.append(a1_index[a1_key] / max(len(a1) - 1, 1)) # this section's fractional position within a1
        if a2_key is not None:
            fracs.append(a2_index[a2_key] / max(len(a2) - 1, 1)) # this section's fractional position within a2
        return sum(fracs) / len(fracs) # average across the editions that have this section

    # find sections which are appendices
    appendix_matches = _appendix_matches([p[0] for p in pairs]) # title -> canonical appendix rank, or None
    
    # split into content vs appendix sections, then sort each group
    content = [p for p in pairs if appendix_matches[p[0]] is None]
    appendix = [p for p in pairs if appendix_matches[p[0]] is not None]
    content.sort(key=position) # fractional position order
    appendix.sort(key=lambda p: appendix_matches[p[0]]) # canonical appendix order

    # content first (Lead sorts to the front because its fractional position is 0.0), appendices last
    return content + appendix
