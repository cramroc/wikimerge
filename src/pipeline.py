
from src.article import get_article, url_to_title
from src.translate import translate_article, DeepLTranslator
from src.merge import merge_articles
from src.render_html import render_html

# function: run_pipeline(config: dict) -> None
def run_pipeline(config):
    """
    config keys:
        url1
        lang1
        url2
        lang2
        title
        outfile
    """
    # parse title from url
    title1 = url_to_title(config["url1"])
    title2 = url_to_title(config["url2"])
    
    # fetch raw articles
    a1_orig = get_article(config["lang1"], title1)
    a2_orig = get_article(config["lang2"], title2)

    # translator
    translator = DeepLTranslator()

    # translate articles
    a1_trans = translate_article(a1_orig, config["lang1"], translator)
    a2_trans = translate_article(a2_orig, config["lang2"], translator)

    # merge articles
    merged = merge_articles(a1_trans, a2_trans)

    # render html
    render_html(config["title"], merged, config["outfile"])
    
    # print success message
    print("Wrote " + config["outfile"])

    # return nothing
    return None

    