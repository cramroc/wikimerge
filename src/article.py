# imports
import wikipediaapi
from urllib.parse import urlparse, unquote

# function: url_to_title(url: str) -> str
def url_to_title(url):
    # check url is a string and looks like url
    if not isinstance(url, str) or "://" not in url:
        raise ValueError("Expected a full Wikipedia article URL: http(s)://...")

    # parse url
    p = urlparse(url)

    # make checks on parsed url
    ## scheme must be http(s)
    if p.scheme not in ("http", "https"):
        raise ValueError("Scheme must be http or https")
    ## host must be "wikipedia.org" or a subdomain
    if not p.netloc.endswith("wikipedia.org"):
        raise ValueError("Host must be wikipedia.org or a subdomain")
    ## path must begin with "/wiki/"
    if not p.path.startswith("/wiki/"):
        raise ValueError("Path must begin with /wiki/")

    # acquire title from url
    ## handle trailing "/" and split segments by "/" (ignoring first empty segment)
    path = p.path.rstrip("/")
    segments = [seg for seg in path.split("/") if seg]
    ## check there is a title segment
    if len(segments) < 2:
        raise ValueError("URL does not contain an article title")
    ## unquote the title segment (last segment)
    title = unquote(segments[-1])
    ## replace "_" with whitespaces and strip
    title = title.replace("_", " ")
    ## return title
    return title

# function: get_article(lang: str, title: str) -> dict[str, list[str]]
def get_article(lang, title):
    # instantiate wikipedia api
    wiki = wikipediaapi.Wikipedia(user_agent="Wikimerge/0.1",
                                  language=lang,
                                  extract_format=wikipediaapi.ExtractFormat.WIKI)
    
    # define page & make sure it exists
    title = title.strip()
    page = wiki.page(title)
    if not page.exists():
        raise ValueError("Article not found: " + title)
    
    # helper function: split_paragraphs(text: str) -> list[str]
    def split_paragraphs(text):
        # split text by blank lines into blocks
        blocks = text.split("\n\n")
        # clean up each block and store in paragraphs list
        paragraphs = []
        for b in blocks:
            b = b.strip()
            if b:
                paragraphs.append(b.replace("\n", " "))
        # return list of clean paragraphs
        return paragraphs

    # build result dictionary
    ## initiate dict
    out = {}
    ## introduction
    lead_text = split_paragraphs(page.summary)
    if lead_text:
        out["Lead"] = lead_text
    ## sections
    for s in page.sections:
        section_text = split_paragraphs(s.text)
        if section_text:
            out[s.title] = section_text
    
    # return result dictionary of section title & list of paragraphs in section
    return out

# test
if __name__ == "__main__":
    test_url = "https://es.wikipedia.org/wiki/Inteligencia_artificial"
    try:
        title = url_to_title(test_url)
        data = get_article("es", title)
    except Exception as e:
        print("Error", e)
    else:
        print("Lang: es")
        print("Title: " + title)
        lead = data.get("Lead", [])
        print("\nLead (first 2 paragraphs):")
        for p in lead[:2]:
            print("-", p, "\n")
        
        print("Section names:")
        print(list(data.keys()))