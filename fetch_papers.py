import requests
import datetime

def fetch_recent_swine_papers():
    today = datetime.date.today()
    year = today.year
    url = "https://api.crossref.org/works"
    params = {
        "filter": f"container-title:Journal of Animal Science,from-pub-date:{year}-01-01",
        "query": "swine",
        "sort": "published",
        "order": "desc",
        "rows": 10
    }

    r = requests.get(url, params=params)
    data = r.json()

    papers = []
    for item in data["message"]["items"]:
        title = item["title"][0]
        doi = item["DOI"]
        date = item.get("published-print", {}).get("date-parts", [[year]])[0]
        papers.append({"title": title, "doi": doi, "date": date})

    return papers


def save_to_markdown(papers):
    with open("latest_papers.md", "w", encoding="utf-8") as f:
        f.write(f"# 🐷 Latest Swine Papers ({datetime.date.today()})\n\n")
        for p in papers:
            f.write(f"- **{p['title']}**  \n  DOI: [https://doi.org/{p['doi']}](https://doi.org/{p['doi']})  \n  Published: {p['date']}\n\n")


if __name__ == "__main__":
    papers = fetch_recent_swine_papers()
    save_to_markdown(papers)
