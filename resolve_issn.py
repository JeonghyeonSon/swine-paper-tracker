"""
Resolve preferred ISSNs for journals using Crossref API.
Writes journals_issn.txt with lines in the format:
ISSN  # Journal Title

Usage:
    python resolve_issn.py --input my_journals.txt
    python resolve_issn.py --journal "Animal" --journal "Animals"

If no input file is provided, pass one or more --journal arguments.
Requires: requests
"""
import requests
import time
import json
import os
import argparse

API = "https://api.crossref.org/journals"

def lookup_journal(query, rows=3):
    try:
        r = requests.get(API, params={"query": query, "rows": rows}, timeout=10)
        r.raise_for_status()
        data = r.json()
        items = data.get("message", {}).get("items", [])
        return items
    except Exception as e:
        print(f"Error querying Crossref for '{query}': {e}")
        return []


def pick_best_issn(items):
    if not items:
        return None, None
    # prefer item with largest total-dois (best coverage)
    best = None
    best_count = -1
    for it in items:
        counts = it.get("counts", {})
        total = counts.get("total-dois") or counts.get("current-dois") or 0
        if total > best_count:
            best_count = total
            best = it
    issns = best.get("ISSN") or []
    title = best.get("title")
    if issns:
        return issns[0], title
    return None, title


def main():
    parser = argparse.ArgumentParser(description="Resolve journal names to ISSNs via Crossref")
    parser.add_argument("--input", "-i", help="Text file with one journal name per line")
    parser.add_argument("--journal", "-j", action="append", help="Journal name (repeatable)")
    parser.add_argument("--out", "-o", default="journals_issn.txt", help="Output ISSN file")
    args = parser.parse_args()

    lines = []
    if args.input:
        if not os.path.exists(args.input):
            print(f"Input file {args.input} not found")
            return
        with open(args.input, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
    elif args.journal:
        lines = args.journal
    else:
        print("Provide --input FILE or one or more --journal arguments")
        return

    results = []
    for q in lines:
        print(f"Looking up: {q}")
        items = lookup_journal(q, rows=5)
        issn, title = pick_best_issn(items)
        if issn:
            print(f"  -> {issn}  ({title})")
            results.append((issn, title, q))
        else:
            print(f"  -> No ISSN found, best match title: {title}")
            results.append((None, title, q))
        time.sleep(1)

    with open(args.out, "w", encoding="utf-8") as f:
        for issn, title, orig in results:
            if issn:
                f.write(f"{issn}  # {title} (from '{orig}')\n")
            else:
                f.write(f"# NO_ISSN  # {title} (from '{orig}')\n")

    print(f"Wrote {args.out} with {len(results)} entries.")

if __name__ == '__main__':
    main()
