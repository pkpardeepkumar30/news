#!/usr/bin/env python3
"""Collect configured RSS feeds and manually submitted social links.

Dependency-free by design. This collector does not bypass logins, paywalls,
robots rules, or platform restrictions. Use approved APIs where required.
"""
from __future__ import annotations
import argparse, hashlib, html, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
UA = "NazarIndiaResearchBot/0.2 (+https://github.com/pkpardeepkumar30/news)"

def text(node, names):
    for name in names:
        item = node.find(name)
        if item is not None and item.text:
            return html.unescape(item.text.strip())
    return ""

def strip_html(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()

def stable_id(url, title):
    return hashlib.sha256((url + "|" + title).encode()).hexdigest()[:18]

def parse_feed(content, source):
    root = ET.fromstring(content)
    items = root.findall('.//item')
    if not items:
        items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
    rows = []
    for item in items:
        title = text(item, ['title', '{http://www.w3.org/2005/Atom}title'])
        link = text(item, ['link'])
        if not link:
            link_node = item.find('{http://www.w3.org/2005/Atom}link')
            link = link_node.attrib.get('href', '') if link_node is not None else ''
        description = strip_html(text(item, [
            'description', 'summary', '{http://www.w3.org/2005/Atom}summary',
            '{http://purl.org/rss/1.0/modules/content/}encoded'
        ]))
        published_at = text(item, [
            'pubDate', 'published', 'updated',
            '{http://www.w3.org/2005/Atom}published',
            '{http://www.w3.org/2005/Atom}updated'
        ])
        image_url = ''
        for child in list(item):
            tag = child.tag.lower()
            if tag.endswith(('thumbnail', 'content', 'enclosure')):
                candidate = child.attrib.get('url', '')
                mime = child.attrib.get('type', '')
                if candidate and (mime.startswith('image/') or re.search(r'\.(jpg|jpeg|png|webp)(\?|$)', candidate, re.I)):
                    image_url = candidate
                    break
        if title and link:
            rows.append({
                'raw_id': stable_id(link, title), 'title': title, 'url': link,
                'summary': description[:2500], 'published_at': published_at,
                'image_url': image_url,
                'source': {
                    'id': source['id'], 'name': source['name'],
                    'type': source['type'], 'ownership': source.get('ownership', '')
                }
            })
    return rows

def fetch(source):
    request = Request(source['url'], headers={
        'User-Agent': UA,
        'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml'
    })
    with urlopen(request, timeout=25) as response:
        return parse_feed(response.read(), source)

def social_rows():
    path = ROOT / 'data/social_submissions.json'
    if not path.exists():
        return []
    rows = []
    for lead in json.loads(path.read_text(encoding='utf-8')):
        url = lead.get('url', '')
        title = lead.get('title') or f"Submitted social lead from {urlparse(url).netloc}"
        rows.append({
            'raw_id': stable_id(url, title), 'title': title, 'url': url,
            'summary': lead.get('note', ''),
            'published_at': lead.get('submitted_at', ''),
            'image_url': lead.get('image_url', ''),
            'suggested_category': lead.get('category', ''),
            'source': {
                'id': 'manual-social',
                'name': lead.get('submitted_by', 'Public submission'),
                'type': 'social', 'ownership': 'Individual/public account'
            },
            'requires_verification': True
        })
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT / 'config/sources.json').read_text(encoding='utf-8'))
    all_rows, errors = [], []
    for source in config['sources']:
        if not source.get('enabled'):
            continue
        try:
            all_rows.extend(fetch(source))
        except Exception as exc:
            errors.append({'source': source['id'], 'error': str(exc)})
            if args.strict:
                raise
    all_rows.extend(social_rows())
    unique = {row['raw_id']: row for row in all_rows}
    now = datetime.now(timezone.utc)
    payload = {
        'collected_at': now.isoformat(), 'count': len(unique),
        'items': list(unique.values()), 'errors': errors
    }
    inbox = ROOT / 'data/inbox'
    inbox.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime('%Y-%m-%d-%H%M')
    (inbox / f'{stamp}.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    (inbox / 'latest.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Collected {len(unique)} items; {len(errors)} source errors")

if __name__ == '__main__':
    main()
