import argparse
import datetime
import json
import os
import re
import requests
import time
from html import unescape


API_URL = "https://api.crossref.org/works"


def _strip_html(text: str) -> str:
    if not text:
        return ""
    # remove simple HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text).strip()


def _format_date_from_parts(parts):
    # parts is a list like [YYYY, MM, DD] or [YYYY, MM]
    try:
        if not parts:
            return ""
        year = parts[0]
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        return datetime.date(int(year), int(month), int(day)).isoformat()
    except Exception:
        return str(parts)


def parse_item(item):
    title = "".join(item.get("title", [])) if item.get("title") else ""
    doi = item.get("DOI")
    # try several date fields
    date_parts = None
    for key in ("published-print", "published-online", "issued", "created"):
        dp = item.get(key, {}).get("date-parts") if item.get(key) else None
        if dp:
            date_parts = dp[0]
            break
    date = _format_date_from_parts(date_parts) if date_parts else ""

    # journal / container title
    journal = "".join(item.get("container-title", [])) if item.get("container-title") else item.get("publisher", "")

    # authors and affiliations
    authors_raw = item.get("author", []) or []
    authors = []
    for a in authors_raw:
        name = " ".join(filter(None, [a.get("given"), a.get("family")])) or a.get("name") or ""
        affs = [aff.get("name") for aff in (a.get("affiliation") or []) if aff.get("name")]
        if affs:
            authors.append(f"{name} ({'; '.join(affs)})")
        else:
            authors.append(name)

    # abstract (may contain html)
    abstract_raw = item.get("abstract")
    abstract = _strip_html(abstract_raw) if abstract_raw else ""
    abstract_snippet = (abstract[:200] + "...") if abstract and len(abstract) > 200 else abstract

    # subjects/keywords
    subjects = item.get("subject") or item.get("subjects") or []

    return {
        "title": title,
        "doi": doi,
        "date": date,
        "journal": journal,
        "authors": authors,
        "abstract": abstract,
        "abstract_snippet": abstract_snippet,
        "subjects": subjects,
    }


def fetch_recent_swine_papers(query="swine", journal=None, from_date=None, rows=100, timeout=10, retries=2):
    params = {
        "query": query,
        "rows": rows,
        "sort": "published",
        "order": "desc",
    }
    filters = []
    if journal:
        # support passing an ISSN filter as 'issn:XXXX' (from journals_issn.txt) or plain names
        if isinstance(journal, str) and journal.lower().startswith("issn:"):
            # journal already contains the correct Crossref filter (issn:XXXX)
            filters.append(journal)
        else:
            filters.append(f"container-title:{journal}")
    if from_date:
        filters.append(f"from-pub-date:{from_date}")
    if filters:
        params["filter"] = ",".join(filters)

    attempt = 0
    while attempt <= retries:
        try:
            r = requests.get(API_URL, params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            items = data.get("message", {}).get("items", [])
            papers = [parse_item(it) for it in items]
            return papers
        except Exception as e:
            attempt += 1
            if attempt > retries:
                raise
            time.sleep(1 + attempt)


def _load_index(index_path):
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def _save_index(index_path, doi_set):
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(doi_set)), f, ensure_ascii=False, indent=2)


def save_to_markdown(papers, out_path="latest_papers.md", append=True, index_path=".papers_index.json", create_if_empty=False):
    existing = _load_index(index_path)
    new_papers = [p for p in papers if p.get("doi") and p["doi"] not in existing]

    if not new_papers:
        if not create_if_empty:
            print("No new papers to add.")
            return 0
        # fallthrough: create an empty file with header/message

    mode = "a" if append and os.path.exists(out_path) else "w"
    header = f"# 🐷 Latest Swine Papers — {datetime.date.today()}\n\n"
    with open(out_path, mode, encoding="utf-8") as f:
        if mode == "w":
            f.write(header)
        else:
            f.write(f"\n## New on {datetime.date.today()}\n\n")

        def _format_authors(authors):
            if not authors:
                return ""
            # Show up to 3 authors with affiliations. If more than 3, append 'et al.'
            if len(authors) > 3:
                first_three = authors[:3]
                return f"{', '.join(first_three)} et al."
            return ', '.join(authors)

        for p in new_papers:
            f.write(f"- **{p['title']}**  \n")
            if p.get("authors"):
                f.write(f"  - Authors: {_format_authors(p['authors'])}  \n")
            if p.get("journal"):
                f.write(f"  - Journal: {p['journal']}  \n")
            if p.get("date"):
                f.write(f"  - Published: {p['date']}  \n")
            if p.get("subjects"):
                f.write(f"  - Keywords: {', '.join(p['subjects'])}  \n")
            if p.get("abstract_snippet"):
                f.write(f"  - Abstract: {p['abstract_snippet']}  \n")
            if p.get("doi"):
                f.write(f"  - DOI: https://doi.org/{p['doi']}  \n")
            f.write("\n")

    # update index
    for p in new_papers:
        if p.get("doi"):
            existing.add(p["doi"])
    _save_index(index_path, existing)
    if new_papers:
        print(f"Added {len(new_papers)} new papers to {out_path}")
    else:
        print(f"Created empty weekly file {out_path} (no new papers)")
    return len(new_papers)


def main():
    parser = argparse.ArgumentParser(description="Fetch recent swine papers from Crossref and save to markdown")
    parser.add_argument("--query", "-q", default="swine")
    parser.add_argument("--journal", "-j", default="Journal of Animal Science",
                        help="Journal name or comma-separated list of journals (e.g. 'Journal of Animal Science,Other Journal')")
    parser.add_argument("--last-days", type=int, default=30)
    parser.add_argument("--rows", "-n", type=int, default=100)
    parser.add_argument("--out", "-o", default="latest_papers.md")
    parser.add_argument("--append", action="store_true", help="Append to existing output (default: overwrite if not set)")
    parser.add_argument("--weekly", action="store_true", help="Create a weekly archive file instead of writing to --out")
    parser.add_argument("--archive-dir", default="weekly", help="Directory to store weekly archives when --weekly is used")
    parser.add_argument("--dry-run", action="store_true", help="Don't call API; show parameters only")
    args = parser.parse_args()

    today = datetime.date.today()
    from_date = (today - datetime.timedelta(days=args.last_days)).isoformat()

    print(f"Parameters: query={args.query!r}, journal={args.journal!r}, from_date={from_date}, rows={args.rows}, weekly={args.weekly}")
    if args.dry_run:
        print("Dry run: exiting without network call.")
        return

    # prefer manual ISSN file if present; otherwise use names from --journal
    journals = []
    issn_file = 'journals_issn.txt'
    if os.path.exists(issn_file):
        with open(issn_file, 'r', encoding='utf-8') as jf:
            for line in jf:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # line format: ISSN  # comment
                parts = line.split('#', 1)[0].strip()
                s = parts
                if s:
                    journals.append(s)
    else:
        journals = [j.strip() for j in args.journal.split(',') if j.strip()]
    collected = []
    for j in journals:
        try:
            # if j looks like an ISSN, use the issn filter; otherwise treat as container-title
            if re.match(r"^\d{4}-?\d{3}[\dXx]$", j):
                collected.extend(fetch_recent_swine_papers(query=args.query, journal=f"issn:{j}", from_date=from_date, rows=args.rows))
            else:
                collected.extend(fetch_recent_swine_papers(query=args.query, journal=j, from_date=from_date, rows=args.rows))
        except Exception as e:
            print(f"Warning: failed to fetch for journal={j}: {e}")

    # dedupe within this run by DOI
    seen = set()
    unique_papers = []
    for p in collected:
        doi = p.get('doi')
        if not doi:
            continue
        if doi in seen:
            continue
        seen.add(doi)
        unique_papers.append(p)

    # determine output path: weekly archive or provided out
    out_path = args.out
    if args.weekly:
        # use YYYY_MM_DD.md (e.g., 2025_10_15.md) so files sort lexicographically by date
        file_name = f"{today.year:04d}_{today.month:02d}_{today.day:02d}.md"
        os.makedirs(args.archive_dir, exist_ok=True)
        out_path = os.path.join(args.archive_dir, file_name)
        # do not append to weekly archive files by default; write a new file each run
        args.append = False

    save_to_markdown(unique_papers, out_path=out_path, append=args.append, create_if_empty=(args.weekly))


if __name__ == "__main__":
    main()
