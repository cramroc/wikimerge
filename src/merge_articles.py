def merge_articles(a1: dict, a2: dict):
    """
    Merge two translated Wikipedia articles.
    Input:
        a1 (dict): translated_article from language 1
        a2 (dict): translated_article from language 2
    Output:
        dict: merged sections -> list of paragraph records
              (order rule: all sections from a1 first, then any new sections from a2;
               within a section: paragraphs from a1 first, then a2)
    """

    # ensure both input are not empty
    if a1 is None: raise ValueError("First argument is None")
    if a2 is None: raise ValueError("Second argument is None")
    # ensure both input are dicts
    if not isinstance(a1, dict):
        raise ValueError("First argument is not a dictionary")
    if not isinstance(a2, dict):
        raise ValueError("Second argument is not a dictionary")

    # instantiate list of section titles in order
    sec_titles_in_order = []
    # add "Lead" first if present in either dictionary
    if "Lead" in a1 or "Lead" in a2:
        sec_titles_in_order.append("Lead")
    # add other sections from a1 and a2 in order of appearance
    for sec in a1.keys():
        if sec != "Lead" and sec not in sec_titles_in_order:
            sec_titles_in_order.append(sec)
    for sec in a2.keys():
        if sec != "Lead" and sec not in sec_titles_in_order:
            sec_titles_in_order.append(sec)

    # initialise empty dict and fill it section by section.
    merged = {}

    # loop through sec_titles_in_order:
    for section in sec_titles_in_order:
        # get list of paragaph records from a1 & a2
        list1 = a1.get(section, [])
        list2 = a2.get(section, [])
        # ensure both are lists
        if not isinstance(list1, list):
            raise ValueError("Section " + section + " in first argument is not a list")
        if not isinstance(list2, list):
            raise ValueError("Section " + section + " in second argument is not a list")
        # Shallow-copy each paragraph records (so later modifications to inputs do not affect merged output)
        combined = []
        for p in list1:
            if isinstance(p, dict):
                combined.append(dict(p))
            else:
                raise ValueError("Paragraph in section " + section + " in first argument is not a dictionary")
        for p in list2:
            if isinstance(p, dict):
                combined.append(dict(p))
            else:
                raise ValueError("Paragraph in section " + section + " in second argument is not a dictionary")
        # assign paragraph list to merged dict
        merged[section] = combined

    # return merged dict: dict[str, list[dict[str, str]]]
    return merged

if __name__ == "__main__":
    # test data
    a1 = {
        "Lead": [
            {"lang": "ES", "original": "Hola mundo.", "translated": "Hello world.", "idx": 0},
            {"lang": "ES", "original": "Esto es una prueba.", "translated": "This is a test.", "idx": 1}
        ],
        "Historia": [
            {"lang": "ES", "original": "La historia es larga.", "translated": "The history is long.", "idx": 0},
            {"lang": "ES", "original": "Muchos cosas pasaron.", "translated": "Many things happened.", "idx": 1}
        ]
    }
    
    a2 = {
        "Lead": [
            {"lang": "FR", "original": "Bonjour monde.", "translated": "Hello world.", "idx": 0}
        ],
        "Géographie": [
            {"lang": "FR", "original": "La géographie est vaste.", "translated": "Geography is vast.", "idx": 0}
        ],
        "Historia": [
            {"lang": "FR", "original": "L'histoire est intéressante.", "translated": "History is interesting.", "idx": 0}
        ]
    }

    # test merge_articles
    merged = merge_articles(a1, a2)

    print("Merged article sections and paragraphs:")
    for section, paragraphs in merged.items():
        print("Section: " + section)
        for record in paragraphs:
            print(" -", record)
