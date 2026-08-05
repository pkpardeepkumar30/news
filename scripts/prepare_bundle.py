#!/usr/bin/env python3
"""Prepare a compact, dynamically ranked file for news distillation."""
from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOP_WORDS = {
    'about', 'after', 'against', 'amid', 'from', 'have', 'india', 'into',
    'latest', 'news', 'over', 'says', 'that', 'their', 'this', 'with'
}
CATEGORIES = [
    'Politics & Elections', 'Governance & Administration', 'Protests',
    'States & Local', 'Economy & Employment',
    'Society, Rights & Justice', 'Environment, Health & Science', 'Sports',
    'International & Geopolitics'
]
INDEPENDENT_SOCIAL_TYPES = {'independent', 'local', 'social'}
CATEGORY_TERMS = {
    'Politics & Elections': (
        'election', 'elections', 'electoral', 'campaign', 'campaigning',
        'political party', 'opposition party', 'ruling party', 'ballot', 'voters'
    ),
    'Governance & Administration': (
        'bill', 'bills', 'legislation', 'law', 'laws', 'regulation', 'regulations',
        'policy decision', 'cabinet decision', 'appointment', 'appointments',
        'bureaucrat', 'bureaucrats', 'civil servant', 'transfer order', 'audit',
        'audits', 'investigation', 'investigations', 'raid', 'raids', 'enforcement',
        'administration', 'administrative action', 'public authority'
    ),
    'Protests': (
        'protest', 'protests', 'protester', 'protesters', 'protesting',
        'demonstration', 'demonstrations', 'demonstrator', 'demonstrators',
        'sit in', 'hunger strike', 'on strike', 'workers strike', 'worker strike',
        'walkout', 'blockade', 'agitation', 'dharna', 'mass rally', 'protest march',
        'आंदोलन', 'धरना', 'प्रदर्शन', 'हड़ताल', 'विरोध प्रदर्शन'
    ),
    'States & Local': (
        'district administration', 'district collector', 'municipal', 'municipality',
        'panchayat', 'gram sabha', 'village council', 'local body', 'civic body',
        'state government', 'state assembly'
    ),
    'Economy & Employment': (
        'economy', 'economic', 'employment', 'unemployment', 'jobs', 'job market',
        'workers', 'labour', 'labor', 'industry', 'industries', 'business', 'trade',
        'tax', 'taxation', 'inflation', 'gdp', 'market', 'markets', 'banking'
    ),
    'Society, Rights & Justice': (
        'rights', 'justice', 'education', 'school', 'schools', 'university',
        'students', 'discrimination', 'caste', 'gender', 'disability', 'welfare',
        'legal aid', 'civil liberties', 'human rights', 'social justice'
    ),
    'Environment, Health & Science': (
        'environment', 'environmental', 'climate', 'forest', 'forests', 'wildlife',
        'pollution', 'health', 'hospital', 'disease', 'medicine', 'medical',
        'science', 'scientists', 'research', 'species', 'conservation'
    ),
    'Sports': (
        'sport', 'sports', 'tournament', 'championship', 'match', 'league', 'team',
        'athlete', 'athletes', 'football', 'cricket', 'hockey', 'badminton', 'tennis'
    ),
    'International & Geopolitics': (
        'international', 'geopolitics', 'geopolitical', 'diplomatic', 'diplomacy',
        'foreign ministry', 'foreign minister', 'ceasefire', 'cross border',
        'peace talks', 'sanctions', 'embassy', 'ambassador'
    )
}


def norm(value):
    cleaned = ''.join(
        character
        if character.isalnum() or character.isspace()
        or unicodedata.category(character).startswith('M')
        else ' '
        for character in value.casefold()
    )
    return re.sub(r'\s+', ' ', cleaned).strip()


def title_tokens(value):
    return {
        token for token in norm(value).split()
        if len(token) > 2 and token not in STOP_WORDS
    }


def contains_phrase(text, phrase):
    return f' {norm(phrase)} ' in f' {text} '


def is_independent_social(item):
    source = item.get('source', {})
    group = source.get('selection_group', '')
    if group:
        return group == 'independent_social'
    return source.get('type') in INDEPENDENT_SOCIAL_TYPES


def category_candidate_scores(item):
    """Return broad discovery signals; the editorial model makes the final label."""
    title = norm(item.get('title', ''))
    summary = norm(item.get('summary', ''))
    hint = item.get('suggested_category', '')
    scores = {}
    for category in CATEGORIES:
        score = 8 if hint == category else 0
        for phrase in CATEGORY_TERMS[category]:
            if contains_phrase(title, phrase):
                score += 4
            elif contains_phrase(summary, phrase):
                score += 1
        if score:
            scores[category] = score
    return scores


def build_event_signals(items):
    """Estimate prominence without relying on named topics, places or incidents."""
    tokens = [title_tokens(item.get('title', '')) for item in items]
    inverted = defaultdict(set)
    for index, words in enumerate(tokens):
        for word in words:
            inverted[word].add(index)

    related = [set([index]) for index in range(len(items))]
    frequency_limit = max(60, len(items) // 12)
    for index, words in enumerate(tokens):
        candidates = set()
        for word in words:
            if len(inverted[word]) <= frequency_limit:
                candidates.update(inverted[word])
        for other in candidates:
            if other <= index:
                continue
            overlap = len(words & tokens[other])
            union = len(words | tokens[other])
            if overlap < 2 or not union:
                continue
            jaccard = overlap / union
            sequence = SequenceMatcher(
                None, norm(items[index].get('title', '')),
                norm(items[other].get('title', ''))
            ).ratio()
            if jaccard >= .58 or sequence >= .84:
                related[index].add(other)
                related[other].add(index)

    signals = []
    for index, neighbours in enumerate(related):
        reports = [items[position] for position in neighbours]
        source_ids = {
            row.get('source', {}).get('id', 'unknown') for row in reports
        }
        source_types = {
            row.get('source', {}).get('type', 'unknown') for row in reports
        }
        social_score = max(
            (int(row.get('social_attention', {}).get('score', 0)) for row in reports),
            default=0
        )
        report_count = len(reports)
        score = min(100, round(
            10
            + min(34, max(0, len(source_ids) - 1) * 12)
            + min(18, math.log2(1 + report_count) * 6)
            + min(34, social_score * .34)
            + min(8, max(0, len(source_types) - 1) * 4)
            + (4 if {'local', 'independent'} & source_types else 0)
            + (8 if items[index].get('priority_discovery') else 0)
        ))
        reasons = []
        if len(source_ids) > 1:
            reasons.append(f'{len(source_ids)} distinct source desks report a similar event')
        if social_score:
            reasons.append(f'observed social-attention score {social_score}/100')
        if {'local', 'independent'} & source_types:
            reasons.append('includes local or independent reporting')
        if items[index].get('priority_discovery'):
            reasons.append('comes from a configured priority discovery profile')
        if not reasons:
            reasons.append('retained through source-balanced review')
        signals.append({
            'dynamic_rank_score': score,
            'observed_report_count': report_count,
            'distinct_source_count': len(source_ids),
            'distinct_source_types': sorted(source_types),
            'social_attention_score': social_score,
            'rationale': '; '.join(reasons)
        })
    return signals, related


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/inbox/latest.json')
    parser.add_argument('--output', default='data/chatgpt-input/latest.json')
    parser.add_argument('--max-items', type=int, default=200)
    parser.add_argument('--chunk-size', type=int, default=40)
    parser.add_argument('--category-reserve', type=int, default=12)
    args = parser.parse_args()
    payload = json.loads((ROOT / args.input).read_text(encoding='utf-8-sig'))
    items = payload.get('items', [])
    available_independent_social = sum(is_independent_social(item) for item in items)
    selection_cap = min(
        args.max_items,
        max(0, available_independent_social * 2 - 1)
    )
    if selection_cap == 0:
        raise ValueError('No independent, local or social discovery material was collected.')
    independent_social_target = selection_cap // 2 + 1
    signals, related = build_event_signals(items)
    category_scores = [category_candidate_scores(item) for item in items]
    for index, scores in enumerate(category_scores):
        signals[index]['category_candidate_scores'] = scores
        signals[index]['candidate_categories'] = sorted(scores)

    grouped = defaultdict(list)
    for index, item in enumerate(items):
        source_id = item.get('source', {}).get('id', 'unknown')
        grouped[source_id].append(index)
    for rows in grouped.values():
        rows.sort(key=lambda position: signals[position]['dynamic_rank_score'], reverse=True)

    kept = []
    selected_ids = set()

    def related_reports(index):
        rows = []
        for position in sorted(related[index], key=lambda value: signals[value]['dynamic_rank_score'], reverse=True):
            if position == index:
                continue
            item = items[position]
            rows.append({
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'source': item.get('source', {}),
                'social_attention': item.get('social_attention')
            })
        return rows[:12]

    def add_item(index):
        item = items[index]
        raw_id = item.get('raw_id')
        if raw_id in selected_ids:
            return False
        title = norm(item.get('title', ''))
        similar = next((
            existing for existing in kept
            if title and norm(existing.get('title', ''))
            and SequenceMatcher(None, title, norm(existing.get('title', ''))).ratio() > .92
        ), None)
        if similar is not None:
            similar.setdefault('related_reports', []).append({
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'source': item.get('source', {}),
                'social_attention': item.get('social_attention')
            })
            selected_ids.add(raw_id)
            return False
        compact = dict(item)
        compact['summary'] = compact.get('summary', '')[:1200]
        compact['selection_signals'] = signals[index]
        reports = related_reports(index)
        if reports:
            compact['related_reports'] = reports
            for position in related[index]:
                selected_ids.add(items[position].get('raw_id'))
        kept.append(compact)
        selected_ids.add(raw_id)
        return True

    # Reserve a buffer of distinct candidates for every broad beat before the
    # collection cap is applied. These are discovery signals, not final labels.
    category_candidates = {
        category: sorted(
            (index for index in range(len(items)) if category_scores[index].get(category)),
            key=lambda index: (
                category_scores[index][category],
                signals[index]['dynamic_rank_score']
            ),
            reverse=True
        )
        for category in CATEGORIES
    }
    reserve = min(args.category_reserve, max(1, selection_cap // len(CATEGORIES)))
    for category in sorted(CATEGORIES, key=lambda value: len(category_candidates[value])):
        added_for_category = 0
        candidates = sorted(
            category_candidates[category],
            key=lambda index: (
                is_independent_social(items[index]),
                bool(items[index].get('priority_discovery')),
                category_scores[index][category],
                signals[index]['dynamic_rank_score']
            ),
            reverse=True
        )
        for index in candidates:
            before = len(kept)
            add_item(index)
            if len(kept) > before:
                added_for_category += 1
            if added_for_category >= reserve or len(kept) >= selection_cap:
                break

    # Guarantee that independent, local and social discovery has a strict
    # majority before established-source candidates can fill remaining slots.
    independent_ranked = sorted(
        (index for index in range(len(items)) if is_independent_social(items[index])),
        key=lambda index: (
            bool(items[index].get('priority_discovery')),
            signals[index]['dynamic_rank_score']
        ),
        reverse=True
    )
    for index in independent_ranked:
        if sum(is_independent_social(item) for item in kept) >= independent_social_target:
            break
        add_item(index)

    # Add events with observable cross-source or social momentum. The remaining
    # places are filled across every source desk so a consequential single-source
    # local report can still reach editorial review.
    ranked = sorted(
        range(len(items)),
        key=lambda index: signals[index]['dynamic_rank_score'],
        reverse=True
    )
    signal_limit = min(selection_cap, len(kept) + min(40, max(1, selection_cap // 5)))
    for index in ranked:
        add_item(index)
        if len(kept) >= signal_limit:
            break

    positions = {source_id: 0 for source_id in grouped}
    source_ids = list(grouped)
    while len(kept) < selection_cap:
        added = False
        for source_id in source_ids:
            rows = grouped[source_id]
            while positions[source_id] < len(rows):
                index = rows[positions[source_id]]
                positions[source_id] += 1
                if items[index].get('raw_id') not in selected_ids:
                    added = True
                    add_item(index)
                    break
            if len(kept) >= selection_cap:
                break
        if not added:
            break

    independent_social_count = sum(is_independent_social(item) for item in kept)
    if independent_social_count * 2 <= len(kept):
        raise ValueError(
            'Unable to prepare a strict independent/social discovery majority: '
            f'{independent_social_count} of {len(kept)} selected candidates.'
        )
    established_count = len(kept) - independent_social_count

    prepared_at = datetime.now(timezone.utc).isoformat()
    task = (
        'Review every supplied part, discover the most consequential events from '
        'the supplied evidence, cluster related reports, assign the best-fit broad '
        'news category dynamically and produce up to 100 processed stories using '
        'schema/processed-news.schema.json. The final portfolio must contain at '
        'least five well-supported stories in every category. Treat social attention '
        'as a discovery signal rather than verification. More than half of the final '
        'stories must originate with independent, local or social discovery, using the '
        'first source in each story as the discovery source; established outlets may '
        'account for no more than half.'
    )
    output = ROOT / args.output
    parts_dir = output.parent / 'parts'
    parts_dir.mkdir(parents=True, exist_ok=True)
    for old_part in parts_dir.glob('part-*.json'):
        old_part.unlink()
    chunks = [kept[index:index + args.chunk_size] for index in range(0, len(kept), args.chunk_size)]
    part_paths = []
    for index, part_items in enumerate(chunks, start=1):
        part_path = parts_dir / f'part-{index:02d}.json'
        relative = part_path.relative_to(ROOT).as_posix()
        part_payload = {
            'task': task,
            'prepared_at': prepared_at,
            'input_count': len(items),
            'supplied_count': len(kept),
            'source_mix': {
                'independent_social': independent_social_count,
                'established_or_other': established_count,
                'independent_social_majority_required': True
            },
            'part': index,
            'part_count': len(chunks),
            'items': part_items
        }
        part_path.write_text(json.dumps(part_payload, indent=2, ensure_ascii=False), encoding='utf-8')
        part_paths.append(relative)
    bundle = {
        'task': task,
        'prepared_at': prepared_at,
        'input_count': len(items),
        'supplied_count': len(kept),
        'source_mix': {
            'independent_social': independent_social_count,
            'established_or_other': established_count,
            'independent_social_majority_required': True
        },
        'part_count': len(chunks),
        'parts': part_paths,
        'items': kept
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Prepared {len(kept)} items in {len(chunks)} parts: {output}")


if __name__ == '__main__':
    main()
