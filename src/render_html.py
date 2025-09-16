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

# function: render_html(title: str, sections: dict, outfile: str) -> None
def render_html(title, sections, outfile):
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
        sections=sections,
        css_href=css_path
    )
    
    # write to outfile
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(html)

# testing
if __name__ == "__main__":
    demo_sections = {
        "Lead": [
            {"lang": "ES", "translated": "Hello world translated from Spanish."},
            {"lang": "FR", "translated": "Hello world translated from French."},
        ],
        "History": [
            {"lang": "ES", "translated": "History from Spanish."},
            {"lang": "FR", "translated": "History from French."},
        ]
    }
    
    render_html(
        title="Example Article (Merged)",
        sections=demo_sections,
        outfile="output/merged_article.html"
    )
    print("Wrote output/merged_article.html")