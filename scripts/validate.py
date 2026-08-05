#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
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
    print(f"OK: {len(ids)} stories")
except Exception as exc:
    print(f"Validation failed: {exc}", file=sys.stderr)
    sys.exit(1)
