import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

# define paths
THIS_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(THIS_DIR, os.pardir))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# define default output file name
DEFAULT_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "merged_article.html")

# function to resolve outfile situations: the file must end up inside OUTPUT_DIR
def resolve_output_path(outfile):
    # if empty: default location
    if not outfile:
        return DEFAULT_OUTPUT_FILE

    # an absolute path is only respected if it actually lives inside OUTPUT_DIR
    if os.path.isabs(outfile):
        # normalise both paths (resolve "..", unify separators/case) so the comparison is
        # not fooled by e.g. "output/../secret" or casing differences on Windows
        resolved = os.path.normcase(os.path.normpath(outfile))
        output_dir_resolved = os.path.normcase(os.path.normpath(OUTPUT_DIR))
        try:
            # the path is confined iff OUTPUT_DIR is the common ancestor of the two
            confined = os.path.commonpath([resolved, output_dir_resolved]) == output_dir_resolved
        except ValueError:
            # commonpath raises if the paths are on different drives (Windows) -> not confined
            confined = False
        if confined:
            return outfile
        # absolute but outside OUTPUT_DIR: fall back to just its filename inside OUTPUT_DIR
        return os.path.join(OUTPUT_DIR, os.path.basename(resolved))

    # a relative path is sandboxed to its bare filename inside OUTPUT_DIR (drop any dirs)
    return os.path.join(OUTPUT_DIR, os.path.basename(outfile))

# function: render_html(title, analysis, outfile, lang1="", lang2="") -> None
def render_html(title, analysis, outfile, lang1="", lang2=""):
    # prepare jinja environment
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"])
    )

    # load template file
    template = env.get_template("article_template.html")

    # force output into OUTPUT_DIR unless absolute path provided
    outfile = resolve_output_path(outfile)
    os.makedirs(os.path.dirname(outfile) or ".", exist_ok=True)

    # compute CSS path relative to output file
    css_path = os.path.relpath(
        os.path.join(STATIC_DIR, "wikipedia-style.css"),
        start = os.path.dirname(outfile)
    )

    # render html
    html = template.render(
        title=title,
        analysis=analysis,
        css_href=css_path,
        lang1=lang1,
        lang2=lang2
    )
    
    # write to outfile
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(html)

# testing
if __name__ == "__main__":
    # analysis-shaped demo: one shared point, one contradiction, one neutral pair,
    # and one unique-per-edition section
    demo_analysis = {
        "Lead": {
            "agree": [{
                "a1": {"lang": "ES", "translated": "Paris is the capital of France."},
                "a2": {"lang": "FR", "translated": "Paris is the capital city of France."},
                "score": 0.95
            }],
            "contradict": [],
            "neutral": [],
            "unique_a1": [],
            "unique_a2": []
        },
        "Population": {
            "agree": [],
            "contradict": [{
                "a1": {"lang": "ES", "translated": "The city has a population of two million people."},
                "a2": {"lang": "FR", "translated": "The city has a population of five million people."},
                "score": 0.71
            }],
            "neutral": [{
                "a1": {"lang": "ES", "translated": "The population grew rapidly after the war, driven by industrial jobs."},
                "a2": {"lang": "FR", "translated": "The population is one of the most diverse in the region."},
                "score": 0.58
            }],
            "unique_a1": [],
            "unique_a2": []
        },
        "History": {
            "agree": [],
            "contradict": [],
            "neutral": [],
            "unique_a1": [{"lang": "ES", "heading": "Ancient period", "translated": "Founded in ancient times (from Spanish)."}],
            "unique_a2": [{"lang": "FR", "translated": "It also has many museums (from French)."}]
        }
    }

    render_html(
        title="Example Article (Merged)",
        analysis=demo_analysis,
        outfile="output/merged_article.html",
        lang1="ES",
        lang2="FR"
    )
    print("Wrote output/merged_article.html")