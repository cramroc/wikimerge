import sys, re
from src.pipeline import run_pipeline

# helper function to slugify text (to transform title to output filename)
def _slugify(text, max_length=50):
    s = (text or "").strip().lower() # strip and lowercase
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-") # non-alphanumerics to hyphens, trim stray hyphens
    return s[:max_length] or "merged_article" # cap length, fallback if empty

# helper function to prompt user for input (input either url or title)????????????????????????
def prompt_user():
    print("=== Wikimerge ===")
    url1 = input("Enter article URL 1: ").strip()
    url2 = input("Enter article URL 2: ").strip()
    title_out = input("Enter output article title: ").strip()
    return {
        "url1": url1,
        "url2": url2,
        "title_out": title_out,
        "outfile": _slugify(title_out) + ".html" # derive filename from title (e.g. "Giant Tortoise" -> giant-tortoise.html)
    }

def main():
    try:
        config  = prompt_user()
        out = run_pipeline(config)
        print("Pipeline completed successfully!", out)
        print("You can open the output file from the 'output' folder.")
    except Exception as e:
        print("\nError:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()