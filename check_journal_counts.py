import datetime
import requests
import sys

ISSN_FILE = 'journals_issn.txt'
DAYS = 365

if not __name__ == '__main__':
    raise SystemExit

try:
    with open(ISSN_FILE, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]
except FileNotFoundError:
    print(f'{ISSN_FILE} not found')
    sys.exit(1)

today = datetime.date.today()
from_date = (today - datetime.timedelta(days=DAYS)).isoformat()
API = 'https://api.crossref.org/works'

for line in lines:
    # extract issn (before any '#')
    issn = line.split('#', 1)[0].strip()
    if not issn:
        continue
    print('\nISSN:', issn)
    for qlabel, query in [('swine', 'swine'), ('none', None)]:
        params = {'filter': f'issn:{issn},from-pub-date:{from_date}', 'rows': 1}
        if query is not None:
            params['query'] = query
        try:
            r = requests.get(API, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            total = data.get('message', {}).get('total-results', 0)
            print(f"  -> {total} works in last {DAYS} days (query={qlabel})")
            if total > 0 and qlabel == 'none':
                # fetch one item for sample title
                params2 = {'filter': f'issn:{issn},from-pub-date:{from_date}', 'rows': 1}
                rr = requests.get(API, params=params2, timeout=15)
                rr.raise_for_status()
                items = rr.json().get('message', {}).get('items', [])
                if items:
                    title = ''.join(items[0].get('title', []) or [])
                    print('    sample title:', title[:200])
        except Exception as e:
            print('  -> error:', e)
