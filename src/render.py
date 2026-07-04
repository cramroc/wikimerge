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

# function to resolve outfile situations
def resolve_output_path(outfile):
    # if empty: default location
    if not outfile:
        return DEFAULT_OUTPUT_FILE
    
    # if user gives absolute path: respect it
    if os.path.isabs(outfile):
        return outfile
    
    # otherwise, treat as relative to OUTPUT_DIR
    filename = os.path.basename(outfile)
    return os.path.join(OUTPUT_DIR, filename)

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
    # analysis-shaped demo: one shared point (both editions) + one unique per edition
    demo_analysis = {
        "Lead": {
            "agree": [{
                "a1": {"lang": "ES", "translated": "Paris is the capital of France."},
                "a2": {"lang": "FR", "translated": "Paris is the capital city of France."},
                "score": 0.95
            }],
            "unique_a1": [],
            "unique_a2": []
        },
        "History": {
            "agree": [],
            "unique_a1": [{"lang": "ES", "translated": "Founded in ancient times (from Spanish)."}],
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