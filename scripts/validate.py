#!/usr/bin/env python3
import argparse, json, sys
from collections import Counter
from pathlib import Path
root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--min-per-category', type=int, default=0)
args = parser.parse_args()
try:
    data = json.loads((root / 'data/news.json').read_text(encoding='utf-8'))
    assert isinstance(data.get('stories'), list)
    ids = [story['id'] for story in data['stories']]
    assert len(ids) == len(set(ids)), 'Duplicate story IDs'
    assert 'Protests' in data.get('categories', []), 'Missing Protests category'
    assert 'Governance & Administration' in data.get('categories', []), 'Missing governance category'
    for story in data['stories']:
        assert story['category'] in data['categories'], f"Unknown category: {story['id']}"
        assert story['image']['url'], f"Missing image: {story['id']}"
        assert story['sources'], f"Missing sources: {story['id']}"
        assert story['confidence']['level'] in {'High','Medium','Low'}
        assert story['coverage']['status'] in {'underreported','developing','widely_covered','unknown'}
        assert int(story['coverage']['source_count']) >= 1
        assert story['coverage']['rationale']
    if args.min_per_category:
        counts = Counter(story['category'] for story in data['stories'])
        shortfalls = {
            category: counts[category]
            for category in data['categories']
            if counts[category] < args.min_per_category
        }
        assert not shortfalls, f'Category minimum not met: {shortfalls}'
    print(f"OK: {len(ids)} stories")
except Exception as exc:
    print(f"Validation failed: {exc}", file=sys.stderr)
    sys.exit(1)
