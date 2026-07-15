# WikiMerge

> Read one Wikipedia topic across two languages — merged into a single, unified page.

WikiMerge is a Python command-line tool that fetches two Wikipedia articles (in different languages, or even the same language), translates each into English, and weaves them together into one combined article rendered as a clean, Wikipedia-styled HTML page. Every paragraph stays tagged with its source language, so you always know where each piece of information came from.

## Demo

<!-- Add a screenshot or GIF of a generated article here, e.g.: ![WikiMerge demo](docs/demo.png) -->

The output is a standalone HTML file styled to look like Wikipedia. Sections from both source articles appear under shared headings, and each paragraph is prefixed with a `[LANG]` tag (for example `[ES]` or `[FR]`) showing which language edition it came from.

## Overview

**Who is this for?** — Wikipedia readers who are curious how the same topic is covered across different language editions and who want to compare or consolidate those perspectives in one place.

**What problem does it solve?** — Different language editions of the same article are written independently, so they often diverge: one may have more content, conflicting details, or emphasis the other lacks. WikiMerge brings both into a single document so the differences and the combined picture are easy to see.

**What does the output look like?** — A standalone HTML file with Wikipedia-like styling and formatting, written to the `output/` folder and openable in any browser.

## Features

- **Two-source merge** — Combine any two Wikipedia articles by URL, across language editions.
- **Automatic title extraction** — Article titles are parsed straight from the URLs you provide.
- **Translation to English** — Section titles and paragraphs are translated via the DeepL API, batched to respect free-tier limits.
- **Section-aware merging** — Shared sections are combined under one heading; the lead comes first, followed by the first article's sections, then any sections unique to the second.
- **Source-language tags** — Every paragraph keeps a tag marking its origin, so merged content is always traceable.
- **Wikipedia-style output** — A self-contained HTML page rendered from a Jinja2 template with accompanying CSS.
- **Modular pipeline** — Each stage (fetch, translate, merge, render) is its own module, making the tool easy to read and extend.

## Requirements

- **Python 3.10+**
- A **DeepL API key** — the free tier works. Sign up at [deepl.com/pro-api](https://www.deepl.com/pro-api).

Python dependencies (pinned in `requirements.txt`):

| Package | Role |
|---|---|
| `Wikipedia-API` | Fetching and parsing Wikipedia articles |
| `requests` | HTTP calls to the DeepL translation API |
| `Jinja2` | HTML templating |
| `python-dotenv` | Loading the API key from `.env` |

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/cramroc/wikimerge.git
cd wikimerge

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your DeepL API key (see Configuration below)
```

### Configuration

WikiMerge reads your DeepL API key from a `.env` file in the project root. Create one:

```bash
# .env
DEEPL_API_KEY=your-deepl-api-key-here
```

The `.env` file is gitignored, so your key stays out of version control.

## Usage

Run the CLI and answer the interactive prompts:

```bash
python main.py
```

It asks for five inputs:

| Prompt | Description | Example |
|---|---|---|
| Article URL 1 | Full URL of the first article | `https://es.wikipedia.org/wiki/Inteligencia_artificial` |
| Language code 1 | Language of the first article | `es` |
| Article URL 2 | Full URL of the second article | `https://fr.wikipedia.org/wiki/Intelligence_artificielle` |
| Language code 2 | Language of the second article | `fr` |
| Output article title | Heading of the merged article | `Artificial Intelligence (Merged)` |

### Worked example

```
$ python main.py
=== Wikimerge ===
Enter article URL 1: https://es.wikipedia.org/wiki/Inteligencia_artificial
Enter article language code 1 (e.g. 'es', 'fr'): es
Enter article URL 2: https://fr.wikipedia.org/wiki/Intelligence_artificielle
Enter article language code 2 (e.g. 'es', 'fr'): fr
Enter output article title: Artificial Intelligence (Merged)
Pipeline completed successfully!
```

WikiMerge fetches both articles, translates them, merges them, and writes the result to the **`output/`** folder. Open the generated `.html` file in any browser to read your merged article.

> **Tip:** Provide full Wikipedia article URLs and the matching language code for each. The two articles should be the same topic in two different languages for the merge to be meaningful.

## Project structure

```
wikimerge/
├── main.py                       # CLI entry point — prompts for input, runs the pipeline
├── requirements.txt              # Pinned dependencies
├── .env                          # DeepL API key (gitignored, create this yourself)
├── src/
│   ├── article.py                # url_to_title() + get_article(): fetch & parse Wikipedia
│   ├── translate.py              # DeepLTranslator + translate_article(): translate to English
│   ├── merge.py                  # merge_articles(): combine two translated articles
│   ├── render.py                 # render_html(): produce the styled HTML page
│   └── pipeline.py               # run_pipeline(): glue the stages together
├── templates/
│   └── article_template.html     # Jinja2 template for the output page
├── static/
│   └── wikipedia-style.css       # Wikipedia-inspired styling
└── output/                       # Generated HTML articles (gitignored)
```

## How it works

WikiMerge is a small pipeline. Each stage has one responsibility and hands its output to the next:

```
URLs ──▶ article.py ──▶ translate.py ──▶ merge.py ──▶ render.py ──▶ HTML
         fetch + parse   translate to EN   combine        styled page
```

1. **Fetch & parse** (`article.py`) — Each URL is validated and parsed into a `(language, title)` pair, then the article is pulled from Wikipedia and split into sections, each holding a list of paragraphs.
2. **Translate** (`translate.py`) — Section titles and paragraphs are sent to DeepL with English as the target language. Requests are batched (up to 50 texts each) to stay within free-tier limits, and each paragraph becomes a record carrying its source language, original text, and translation.
3. **Merge** (`merge.py`) — The two translated articles are aligned by section title. The lead is placed first, then the first article's sections, then any sections unique to the second; within a shared section, the first article's paragraphs precede the second's.
4. **Render** (`render.py`) — The merged article is passed through a Jinja2 template and written as a styled HTML file, each paragraph prefixed with its `[LANG]` source tag.

`pipeline.py` (`run_pipeline`) wires these stages together, and `main.py` provides the interactive front end.

### Data model

Internally, an article is a dictionary mapping section titles to lists of paragraphs. After translation, each paragraph becomes a record tagged with its source language:

```python
{
    "Lead": [
        {"lang": "ES", "original": "Hola mundo.", "translated": "Hello world.", "idx": 0},
        ...
    ],
    "History": [ ... ],
}
```

Merging combines both articles' sections under shared titles while preserving each paragraph's language tag — which is what powers the `[ES]` / `[FR]` markers in the rendered page.

## Roadmap

This is a personal project and isn't open to external contributions right now. A few directions it may grow in:

- A non-interactive mode that accepts command-line arguments and a custom output filename.
- Smarter section alignment (matching equivalent sections even when their titles differ across languages).
- Support for merging more than two articles.
- A side-by-side layout as an alternative to interleaved paragraphs.
- Support for other languages for the output file apart from English.
- Allow for original reference tracking in the output file (tracking sources is important!).
- Meta-analysis of merged articles (same content vs missing content vs contradicting content).

## License

The **code** in this project is licensed under the [MIT License](LICENSE) — © 2026 cramroc. You may reuse, modify, and distribute it provided the copyright notice and license text are retained.

**A note on Wikipedia content:** Articles fetched from Wikipedia are licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Any merged page WikiMerge produces is a derivative work of that content, so if you publish or distribute the output you must comply with CC BY-SA's attribution and share-alike requirements: credit the source articles (with links), note that the text was machine-translated (a modification), and license the result under CC BY-SA 4.0. The MIT license above covers WikiMerge's own source code, not the Wikipedia-derived content it produces.

**Translations:** English translations are produced by the [DeepL API](https://www.deepl.com/) and are subject to DeepL's terms of service.
