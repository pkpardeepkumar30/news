#!/usr/bin/env python3
"""Validate processed output, merge it into the live feed and archive older stories."""
from __future__ import annotations
import argparse, json, re, unicodedata
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
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
INDEPENDENT_SOCIAL_TYPES = {'independent', 'local', 'social'}
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

def reader_text_fields(story):
    yield 'title', story.get('title', '')
    yield 'summary', story.get('summary', '')
    yield 'why_it_matters', story.get('why_it_matters', '')
    yield 'location', story.get('location', '')
    yield 'evidence_status', story.get('evidence_status', '')
    yield 'confidence.rationale', story.get('confidence', {}).get('rationale', '')
    yield 'coverage.rationale', story.get('coverage', {}).get('rationale', '')
    yield 'image.alt', story.get('image', {}).get('alt', '')
    for index, disagreement in enumerate(story.get('disagreements', [])):
        yield f'disagreements[{index}]', disagreement
    for index, source in enumerate(story.get('sources', [])):
        yield f'sources[{index}].role', source.get('role', '')

def contains_non_latin_letters(value):
    for character in value:
        if not unicodedata.category(character).startswith('L'):
            continue
        if 'LATIN' not in unicodedata.name(character, ''):
            return True
    return False

def normalised_words(value):
    return re.findall(r'[a-z0-9]+', value.casefold())

def has_long_verbatim_overlap(first, second, length=12):
    first_words, second_words = normalised_words(first), normalised_words(second)
    if len(first_words) < length or len(second_words) < length:
        return False
    phrases = {
        tuple(first_words[index:index + length])
        for index in range(len(first_words) - length + 1)
    }
    return any(
        tuple(second_words[index:index + length]) in phrases
        for index in range(len(second_words) - length + 1)
    )

def source_material_by_url(bundle):
    material = {}
    for item in bundle.get('items', []):
        if item.get('url'):
            material[item['url']] = {
                'title': item.get('title', ''),
                'summary': item.get('summary', '')
            }
        for related in item.get('related_reports', []):
            if related.get('url'):
                material[related['url']] = {
                    'title': related.get('title', ''),
                    'summary': related.get('summary', '')
                }
    return material

def reconcile_sources(story, source_material):
    """Keep evidence links present in the prepared collection.

    Story IDs are editorial identifiers, not foreign keys to crawler raw IDs.
    URL membership is the authoritative evidence check.
    """
    sources = story.get('sources', [])
    retained = [
        source for source in sources
        if source.get('url', '') in source_material
    ]
    removed = len(sources) - len(retained)
    if not retained:
        raise ValueError(
            f"No supplied source URL remains for {story.get('id', '<unknown>')}"
        )
    story['sources'] = retained
    if isinstance(story.get('coverage'), dict):
        story['coverage']['source_count'] = len({
            source.get('url') for source in retained if source.get('url')
        })
    return removed

def validate_editorial_text(story, source_material=None):
    for field, value in reader_text_fields(story):
        if contains_non_latin_letters(str(value)):
            raise ValueError(
                f"Reader-facing field {field} is not fully English for {story.get('id', '<unknown>')}"
            )
    if not source_material:
        return
    for source in story.get('sources', []):
        raw = source_material.get(source.get('url', ''))
        if not raw:
            continue
        story_title = ' '.join(normalised_words(story.get('title', '')))
        raw_title = ' '.join(normalised_words(raw.get('title', '')))
        if len(story_title) >= 30 and len(raw_title) >= 30:
            similarity = SequenceMatcher(None, story_title, raw_title).ratio()
            if similarity >= .90:
                raise ValueError(
                    f"Headline is too similar to source wording for {story.get('id', '<unknown>')}"
                )
        raw_text = f"{raw.get('title', '')} {raw.get('summary', '')}"
        for field in ('summary', 'why_it_matters'):
            if has_long_verbatim_overlap(raw_text, story.get(field, '')):
                raise ValueError(
                    f"Reader-facing field {field} copies a long source phrase for "
                    f"{story.get('id', '<unknown>')}"
                )

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

def validate(story, source_material=None):
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
    validate_editorial_text(story, source_material)
    discovery_source = story['sources'][0]
    if discovery_source.get('type') == 'social':
        corroborating_sources = {
            source.get('url', '')
            for source in story['sources'][1:]
            if source.get('type') != 'social' and source.get('url')
        }
        if not corroborating_sources or int(story['coverage'].get('source_count', 0)) < 2:
            raise ValueError(
                f"Social-origin story lacks independent non-social corroboration: {story['id']}"
            )

def reconcile_and_validate_stories(stories, source_material, maximum_stories):
    accepted, rejected = [], []
    for story in stories:
        try:
            removed_sources = reconcile_sources(story, source_material)
            validate(story, source_material)
            accepted.append(story)
            if removed_sources:
                print(
                    f"Reconciled {story.get('id', '<unknown>')}: "
                    f"removed {removed_sources} unsupported source link(s)"
                )
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            rejected.append((story.get('id', '<unknown>'), str(exc)))
            print(f"Skipping invalid story {story.get('id', '<unknown>')}: {exc}")
    return accepted[:maximum_stories], rejected

def validate_portfolio(stories, minimum_per_category):
    if minimum_per_category > 0:
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
    independent_social = sum(
        bool(story.get('sources'))
        and story['sources'][0].get('type') in INDEPENDENT_SOCIAL_TYPES
        for story in stories
    )
    established = sum(
        bool(story.get('sources')) and story['sources'][0].get('type') == 'mainstream'
        for story in stories
    )
    if independent_social * 2 <= len(stories):
        raise ValueError(
            'Refusing to publish without a strict independent/local/social discovery '
            f'majority; found {independent_social} of {len(stories)} stories.'
        )
    if established * 2 > len(stories):
        raise ValueError(
            'Refusing to publish more than 50% established-media-origin stories; '
            f'found {established} of {len(stories)} stories.'
        )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/processed/latest.json')
    parser.add_argument('--min-per-category', type=int, default=5)
    parser.add_argument('--max-stories', type=int, default=150)
    args = parser.parse_args()
    processed_path = ROOT / args.input
    # Scheduled desktop tasks may save otherwise valid JSON with a UTF-8 BOM.
    # utf-8-sig accepts both forms; rewrite valid input as canonical BOM-free UTF-8.
    processed = repair_text(json.loads(processed_path.read_text(encoding='utf-8-sig')))
    collection_path = ROOT / 'data/chatgpt-input/latest.json'
    collection = json.loads(collection_path.read_text(encoding='utf-8-sig')) if collection_path.exists() else {}
    source_material = source_material_by_url(collection)
    incoming = processed.get('stories', processed if isinstance(processed, list) else [])
    if not incoming:
        raise ValueError('No processed stories found; refusing to replace the live feed with an empty result.')
    incoming, rejected = reconcile_and_validate_stories(
        incoming, source_material, args.max_stories
    )
    if not incoming:
        raise ValueError('No valid processed stories remain after evidence reconciliation.')
    validate_portfolio(incoming, args.min_per_category)
    if isinstance(processed, dict):
        processed['stories'] = incoming
    else:
        processed = incoming
    processed_path.write_text(json.dumps(processed, indent=2, ensure_ascii=False), encoding='utf-8')
    live_path = ROOT / 'data/news.json'
    live = repair_text(json.loads(live_path.read_text(encoding='utf-8')))
    previous = {
        story['id']: story
        for story in live.get('stories', [])
        if not story.get('demo')
    }
    for story in incoming:
        story.pop('demo', None)
        story['category'] = CATEGORY_ALIASES.get(story.get('category'), story.get('category'))
        normalise_coverage(story)
    now = datetime.now(timezone.utc)
    active = list(incoming)
    incoming_ids = {story['id'] for story in incoming}
    archive = {}
    # The latest validated portfolio is the complete live basket. Older live
    # stories not selected this time are archived instead of silently lingering
    # and pushing the public feed beyond its configured maximum.
    for story_id, story in previous.items():
        if story_id not in incoming_ids:
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
        'selection_group': source.get('selection_group', ''),
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
    print(
        f"Published {len(incoming)} incoming; skipped {len(rejected)} invalid; "
        f"{len(active)} active; {sum(map(len, archive.values()))} archived"
    )

if __name__ == '__main__':
    main()
