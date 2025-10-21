#!/usr/bin/env python3
import json
import re
import glob
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))
INDEX_PATH = os.path.join(ROOT, '.papers_index.json')
BACKUP_PATH = INDEX_PATH + '.bak.' + datetime.now().strftime('%Y%m%d%H%M%S')

DOI_RE = re.compile(r'https?://doi\.org/([^\)\s]+)|\b(10\.\d{4,9}/[^\s\)]+)', re.I)

def load_index(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_index(path, dois):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(dois)), f, ensure_ascii=False, indent=2)

def extract_from_weekly():
    found = set()
    pattern_files = glob.glob(os.path.join(ROOT, 'weekly', '*.md'))
    for p in pattern_files:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                txt = f.read()
        except Exception:
            continue
        for m in DOI_RE.finditer(txt):
            doi = m.group(1) or m.group(2)
            if doi:
                found.add(doi.strip())
    return found

def main():
    print('Backing up existing index (if present) ->', BACKUP_PATH)
    if os.path.exists(INDEX_PATH):
        try:
            os.replace(INDEX_PATH, BACKUP_PATH)
        except Exception:
            print('Warning: failed to backup existing index')

    old = load_index(BACKUP_PATH) if os.path.exists(BACKUP_PATH) else set()
    found = extract_from_weekly()
    merged = old.union(found)
    save_index(INDEX_PATH, merged)
    print(f'Found {len(found)} DOIs in weekly files. Index had {len(old)} entries. Merged -> {len(merged)} entries.')

if __name__ == '__main__':
    main()
