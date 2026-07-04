
from src.article import get_article, url_to_title, url_to_lang
from src.translate import translate_article, DeepLTranslator
from src.merge import merge_articles
from src.analysis import analyze_articles
from src.render import render_html

# function: run_pipeline(config: dict) -> None
def run_pipeline(config):
    """
    config keys:
        url1
        url2
        title_out
        outfile (optional)

    Note: outfile is derived from the title via _slugify in main.py. If absent
    or empty, render_html falls back to its default path (output/merged_article.html).
    """
    # parse title and language from url
    title1 = url_to_title(config["url1"])
    lang1 = url_to_lang(config["url1"])
    title2 = url_to_title(config["url2"])
    lang2 = url_to_lang(config["url2"])

    # fetch raw articles
    a1_orig = get_article(lang1, title1)
    a2_orig = get_article(lang2, title2)

    # translator
    translator = DeepLTranslator()

    # translate articles
    a1_trans = translate_article(a1_orig, lang1, translator)
    a2_trans = translate_article(a2_orig, lang2, translator)

    # merge articles
    merged = merge_articles(a1_trans, a2_trans)

    # analyse the two articles (agree / unique-per-language) on the PRE-merge translated
    # articles, so dedup hasn't yet removed the overlapping paragraphs we want to find
    analysis = analyze_articles(a1_trans, a2_trans)

    # render html (outfile derived from title; empty falls back to render's default path)
    render_html(config["title_out"], merged, config.get("outfile", ""), analysis, lang1, lang2)

    # print success message
    print("Wrote merged article to the output/ folder")

    # return nothing
    return None

    