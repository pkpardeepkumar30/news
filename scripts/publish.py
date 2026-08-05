#!/usr/bin/env python3
"""Validate processed output, merge it into the live feed and archive older stories."""
from __future__ import annotations
import argparse, json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {'id','category','title','summary','why_it_matters','location','published_at','updated_at','underreported_score','evidence_status','confidence','image','sources'}
CATEGORIES = [
    'Politics & Elections', 'Governance & Administration', 'Protests',
    'States & Local', 'Economy & Employment',
    'Society, Rights & Justice', 'Environment, Health & Science', 'Sports',
    'International & Geopolitics'
]
CATEGORY_ALIASES = {'Politics & Governance': 'Politics & Elections'}
COVERAGE_STATUSES = {'underreported', 'developing', 'widely_covered', 'unknown'}
MOJIBAKE_REPLACEMENTS = {
    '\u00e2\u20ac\u2122': '\u2019',
    '\u00e2\u20ac\u02dc': '\u2018',
    '\u00e2\u20ac\u201d': '\u2014',
    '\u00e2\u20ac\u201c': '\u2013',
    '\u00e2\u201a\u00b9': '\u20b9',
    '\u00c3\u00b1': '\u00f1'
}

def repair_text(value):
    if isinstance(value, str):
        for broken, repaired in MOJIBAKE_REPLACEMENTS.items():
            value = value.replace(broken, repaired)
        return value
    if isinstance(value, list):
        return [repair_text(item) for item in value]
    if isinstance(value, dict):
        return {key: repair_text(item) for key, item in value.items()}
    return value

def normalise_coverage(story):
    coverage = story.get('coverage')
    if not isinstance(coverage, dict):
        coverage = {
            'status': 'unknown',
            'source_count': max(1, len({source.get('name', '') for source in story.get('sources', [])})),
            'rationale': 'Cross-source prominence was not assessed when this story was processed.'
        }
        story['coverage'] = coverage
    if coverage.get('status') not in COVERAGE_STATUSES:
        raise ValueError(f"Invalid coverage status for {story.get('id', '<unknown>')}")
    if int(coverage.get('source_count', 0)) < 1:
        raise ValueError(f"Invalid coverage source count for {story.get('id', '<unknown>')}")
    if not coverage.get('rationale'):
        raise ValueError(f"Missing coverage rationale for {story.get('id', '<unknown>')}")

def validate(story):
    story['category'] = CATEGORY_ALIASES.get(story.get('category'), story.get('category'))
    missing = REQUIRED - set(story)
    if missing:
        raise ValueError(f"{story.get('id', '<unknown>')} missing: {sorted(missing)}")
    if story['confidence'].get('level') not in {'High','Medium','Low'}:
        raise ValueError(f"Invalid confidence level for {story['id']}")
    if not 0 <= int(story['confidence'].get('score', -1)) <= 100:
        raise ValueError(f"Invalid confidence score for {story['id']}")
    if not 0 <= int(story['underreported_score']) <= 100:
        raise ValueError(f"Invalid underreported score for {story['id']}")
    if not story['sources']:
        raise ValueError(f"No sources for {story['id']}")
    if story['category'] not in CATEGORIES:
        raise ValueError(f"Invalid category for {story['id']}")
    normalise_coverage(story)

def validate_portfolio(stories, minimum_per_category):
    if minimum_per_category <= 0:
        return
    counts = Counter(story['category'] for story in stories)
    shortfalls = {
        category: counts[category]
        for category in CATEGORIES
        if counts[category] < minimum_per_category
    }
    if shortfalls:
        detail = ', '.join(f'{category}: {count}' for category, count in shortfalls.items())
        raise ValueError(
            f'Refusing to publish fewer than {minimum_per_category} stories per category; {detail}'
        )

def parse_dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/processed/latest.json')
    parser.add_argument('--active-days', type=int, default=14)
    parser.add_argument('--min-per-category', type=int, default=5)
    args = parser.parse_args()
    processed_path = ROOT / args.input
    # Scheduled desktop tasks may save otherwise valid JSON with a UTF-8 BOM.
    # utf-8-sig accepts both forms; rewrite valid input as canonical BOM-free UTF-8.
    processed = repair_text(json.loads(processed_path.read_text(encoding='utf-8-sig')))
    incoming = processed.get('stories', processed if isinstance(processed, list) else [])
    if not incoming:
        raise ValueError('No processed stories found; refusing to replace the live feed with an empty result.')
    for story in incoming:
        validate(story)
    validate_portfolio(incoming, args.min_per_category)
    processed_path.write_text(json.dumps(processed, indent=2, ensure_ascii=False), encoding='utf-8')
    live_path = ROOT / 'data/news.json'
    live = repair_text(json.loads(live_path.read_text(encoding='utf-8')))
    merged = {story['id']: story for story in live.get('stories', []) if not story.get('demo')}
    for story in incoming:
        story.pop('demo', None)
        merged[story['id']] = story
    for story in merged.values():
        story['category'] = CATEGORY_ALIASES.get(story.get('category'), story.get('category'))
        normalise_coverage(story)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.active_days)
    active, archive = [], {}
    for story in merged.values():
        try:
            is_active = parse_dt(story['updated_at']).astimezone(timezone.utc) >= cutoff
        except Exception:
            is_active = True
        if is_active:
            active.append(story)
        else:
            archive.setdefault(story['published_at'][:7], []).append(story)
    for month, stories in archive.items():
        year, mon = month.split('-')
        path = ROOT / f'data/archive/{year}/{mon}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        old = json.loads(path.read_text(encoding='utf-8')).get('stories', []) if path.exists() else []
        by_id = {story['id']: story for story in old}
        by_id.update({story['id']: story for story in stories})
        path.write_text(json.dumps({'month': month, 'stories': list(by_id.values())}, indent=2, ensure_ascii=False), encoding='utf-8')
    live['generated_at'] = now.isoformat()
    live['categories'] = CATEGORIES
    live['stories'] = sorted(active, key=lambda story: story['updated_at'], reverse=True)
    source_config = json.loads((ROOT / 'config/sources.json').read_text(encoding='utf-8'))
    treatment = {
        'independent': 'Use as reporting; inspect cited evidence, attribution and corrections.',
        'local': 'Prioritise first-hand regional reporting; corroborate consequential claims.',
        'mainstream': 'Use for reporting, chronology and comparison; preserve original attribution.',
        'government': 'Attribute as an official claim; seek independent confirmation.',
        'social': 'Treat as a lead or eyewitness claim, not automatic confirmation.'
    }
    live['source_registry'] = [{
        'id': source['id'],
        'name': source['name'],
        'type': source['type'],
        'ownership': source.get('ownership', ''),
        'treatment': treatment.get(source['type'], 'Assess the evidence and attribution in context.')
    } for source in source_config['sources'] if source.get('enabled')]
    live_path.write_text(json.dumps(live, indent=2, ensure_ascii=False), encoding='utf-8')
    archive_entries = []
    archive_root = ROOT / 'data/archive'
    for path in sorted(archive_root.glob('[0-9][0-9][0-9][0-9]/[0-9][0-9].json'), reverse=True):
        payload = json.loads(path.read_text(encoding='utf-8'))
        relative = path.relative_to(ROOT).as_posix()
        archive_entries.append({'month': payload.get('month', f'{path.parent.name}-{path.stem}'), 'path': relative, 'count': len(payload.get('stories', []))})
    (archive_root / 'index.json').write_text(json.dumps({'generated_at': now.isoformat(), 'months': archive_entries}, indent=2), encoding='utf-8')
    print(f"Published {len(incoming)} incoming; {len(active)} active; {sum(map(len, archive.values()))} archived")

if __name__ == '__main__':
    main()
