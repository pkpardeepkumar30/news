#!/usr/bin/env python3
import argparse, json, sys
from collections import Counter
from pathlib import Path
from publish import (
    INDEPENDENT_SOCIAL_TYPES, contains_non_latin_letters, reader_text_fields
)
root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--min-per-category', type=int, default=0)
parser.add_argument('--require-independent-majority', action='store_true')
parser.add_argument('--max-stories', type=int, default=0)
args = parser.parse_args()
try:
    data = json.loads((root / 'data/news.json').read_text(encoding='utf-8'))
    assert isinstance(data.get('stories'), list)
    ids = [story['id'] for story in data['stories']]
    assert len(ids) == len(set(ids)), 'Duplicate story IDs'
    if args.max_stories:
        assert len(ids) <= args.max_stories, (
            f'Story maximum exceeded: {len(ids)}/{args.max_stories}'
        )
    assert 'Protests' in data.get('categories', []), 'Missing Protests category'
    assert 'Governance & Administration' in data.get('categories', []), 'Missing governance category'
    for story in data['stories']:
        assert story['category'] in data['categories'], f"Unknown category: {story['id']}"
        for field, value in reader_text_fields(story):
            assert not contains_non_latin_letters(str(value)), f"Non-English reader text in {field}: {story['id']}"
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
    if args.require_independent_majority:
        independent_social = sum(
            story['sources'][0].get('type') in INDEPENDENT_SOCIAL_TYPES
            for story in data['stories']
        )
        established = sum(
            story['sources'][0].get('type') == 'mainstream'
            for story in data['stories']
        )
        assert independent_social * 2 > len(data['stories']), (
            'Independent/local/social discovery is not a strict majority: '
            f'{independent_social}/{len(data["stories"])}'
        )
        assert established * 2 <= len(data['stories']), (
            f'Established-media discovery exceeds 50%: {established}/{len(data["stories"])}'
        )
    print(f"OK: {len(ids)} stories")
except Exception as exc:
    print(f"Validation failed: {exc}", file=sys.stderr)
    sys.exit(1)
