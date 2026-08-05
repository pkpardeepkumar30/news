#!/usr/bin/env python3
"""Prepare a compact, deterministic file for manual or scheduled ChatGPT processing."""
from __future__ import annotations
import argparse, json, re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from difflib import SequenceMatcher
ROOT = Path(__file__).resolve().parents[1]

def norm(value):
    return re.sub(r'[^a-z0-9 ]', '', value.lower()).strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/inbox/latest.json')
    parser.add_argument('--max-items', type=int, default=80)
    args = parser.parse_args()
    payload = json.loads((ROOT / args.input).read_text(encoding='utf-8'))
    grouped = defaultdict(list)
    for item in payload.get('items', []):
        grouped[item.get('source', {}).get('id', 'unknown')].append(item)
    kept = []
    positions = {source_id: 0 for source_id in grouped}
    source_ids = list(grouped)
    while len(kept) < args.max_items:
        added = False
        for source_id in source_ids:
            rows = grouped[source_id]
            position = positions[source_id]
            if position >= len(rows):
                continue
            item = rows[position]
            positions[source_id] += 1
            added = True
            title = norm(item.get('title', ''))
            if any(SequenceMatcher(None, title, norm(existing.get('title', ''))).ratio() > .92 for existing in kept):
                continue
            compact = dict(item)
            compact['summary'] = compact.get('summary', '')[:1200]
            kept.append(compact)
            if len(kept) >= args.max_items:
                break
        if not added:
            break
    bundle = {
        'task': 'Cluster related reports, extract claims, assess evidence, assign category and produce processed stories using schema/processed-news.schema.json. Do not treat repeated copies as independent corroboration. Attribute official and social claims explicitly.',
        'prepared_at': datetime.now(timezone.utc).isoformat(),
        'input_count': len(payload.get('items', [])),
        'supplied_count': len(kept),
        'items': kept
    }
    output = ROOT / 'data/chatgpt-input/latest.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Prepared {len(kept)} items: {output}")

if __name__ == '__main__':
    main()
