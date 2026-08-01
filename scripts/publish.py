#!/usr/bin/env python3
"""Validate processed output, merge it into the live feed and archive older stories."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {'id','category','title','summary','why_it_matters','location','published_at','updated_at','underreported_score','evidence_status','confidence','image','sources'}

def validate(story):
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

def parse_dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/processed/latest.json')
    parser.add_argument('--active-days', type=int, default=14)
    args = parser.parse_args()
    processed = json.loads((ROOT / args.input).read_text(encoding='utf-8'))
    incoming = processed.get('stories', processed if isinstance(processed, list) else [])
    if not incoming:
        raise ValueError('No processed stories found; refusing to replace the live feed with an empty result.')
    for story in incoming:
        validate(story)
    live_path = ROOT / 'data/news.json'
    live = json.loads(live_path.read_text(encoding='utf-8'))
    merged = {story['id']: story for story in live.get('stories', []) if not story.get('demo')}
    for story in incoming:
        story.pop('demo', None)
        merged[story['id']] = story
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
