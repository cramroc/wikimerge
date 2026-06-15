import sys
from src.pipeline import run_pipeline

# helper function to slugify text (to transform title to output filename)
def _slugify(text, max_length=50):
    s = (text or "").strip
    return text.lower().replace(" ", "-")

# helper function to valdate language code

# helper function to check prompt is not empty

# helper function to prompt user for input (input either url or title)????????????????????????
def prompt_user():
    print("=== Wikimerge ===")
    url1 = input("Enter article URL 1: ").strip()
    lang1 = input("Enter article language code 1 (e.g. 'es', 'fr'): ").strip()
    url2 = input("Enter article URL 2: ").strip()
    lang2 = input("Enter article language code 2 (e.g. 'es', 'fr'): ").strip()
    title_out = input("Enter output article title: ").strip()
    # outfile = input("Enter output HTML file name (without .html extension): ").strip() + ".html"
    return {
        "url1": url1,
        "lang1": lang1,
        "url2": url2,
        "lang2": lang2,
        "title_out": title_out
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