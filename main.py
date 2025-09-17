import sys
from src.pipeline import run_pipeline

def prompt_user():
    print("=== Wikimerge ===")
    url1 = input("Enter article URL 1: ").strip()
    lang1 = input("Enter article language code 1 (e.g. 'es', 'fr'): ").strip()
    url2 = input("Enter article URL 2: ").strip()
    lang2 = input("Enter article language code 2 (e.g. 'es', 'fr'): ").strip()
    title = input("Enter output article title: ").strip()
    outfile = input("Enter output HTML file name (without .html extension): ").strip() + ".html"
    return {
        "url1": url1,
        "lang1": lang1,
        "url2": url2,
        "lang2": lang2,
        "title": title,
        "outfile": outfile
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