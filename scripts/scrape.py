#!/usr/bin/env python3
"""Collect configured RSS feeds and manually submitted social links.

Dependency-free by design. This collector does not bypass logins, paywalls,
robots rules, or platform restrictions. Use approved APIs where required.
"""
from __future__ import annotations
import argparse, hashlib, html, json, math, os, re
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

def count(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0

def platform_name(url, supplied=''):
    if supplied:
        return str(supplied).strip()
    host = urlparse(url).netloc.lower().removeprefix('www.')
    return host.split('.')[0].replace('-', ' ').title() or 'Social platform'

def social_attention(lead):
    supplied = lead.get('metrics') or lead.get('engagement') or {}
    metrics = {
        key: count(supplied.get(key, lead.get(key, 0)))
        for key in ('views', 'likes', 'comments', 'shares', 'reposts')
    }
    weighted = (
        metrics['views'] + metrics['likes'] * 4 + metrics['comments'] * 12
        + metrics['shares'] * 20 + metrics['reposts'] * 20
    )
    score = min(100, round(math.log10(1 + weighted) / 7 * 100)) if weighted else 0
    return {
        'platform': platform_name(lead.get('url', ''), lead.get('platform', '')),
        'observed_at': lead.get('observed_at', lead.get('submitted_at', '')),
        'metrics': metrics,
        'score': score
    }

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
                'suggested_category': source.get('category_hint', ''),
                'source': {
                    'id': source['id'], 'name': source['name'],
                    'type': source['type'], 'ownership': source.get('ownership', '')
                }
            })
    return rows

def parse_news_sitemap(content, source):
    root = ET.fromstring(content)
    sitemap_ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    news_ns = 'http://www.google.com/schemas/sitemap-news/0.9'
    image_ns = 'http://www.google.com/schemas/sitemap-image/1.1'
    allowed_paths = source.get('include_paths', [])
    path_categories = source.get('path_categories', {})
    rows = []
    for item in root.findall(f'.//{{{sitemap_ns}}}url'):
        link = (item.findtext(f'{{{sitemap_ns}}}loc') or '').strip()
        if allowed_paths and not any(path in link for path in allowed_paths):
            continue
        title = html.unescape((item.findtext(f'.//{{{news_ns}}}title') or '').strip())
        published_at = (item.findtext(f'.//{{{news_ns}}}publication_date') or '').strip()
        image_url = (item.findtext(f'.//{{{image_ns}}}loc') or '').strip()
        suggested_category = next(
            (category for path, category in path_categories.items() if path in link),
            source.get('category_hint', '')
        )
        if title and link:
            rows.append({
                'raw_id': stable_id(link, title), 'title': title, 'url': link,
                'summary': '', 'published_at': published_at,
                'image_url': image_url,
                'suggested_category': suggested_category,
                'requires_verification': True,
                'source': {
                    'id': source['id'], 'name': source['name'],
                    'type': source['type'], 'ownership': source.get('ownership', ''),
                    'language': source.get('language', '')
                }
            })
    return rows

def fetch(source):
    request = Request(source['url'], headers={
        'User-Agent': UA,
        'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml'
    })
    with urlopen(request, timeout=25) as response:
        content = response.read()
        if source.get('format') == 'news_sitemap':
            return parse_news_sitemap(content, source)
        return parse_feed(content, source)

def social_row(lead, provider=None):
    provider = provider or {}
    url = lead.get('url', '')
    if not url:
        return None
    title = lead.get('title') or f"Submitted social lead from {urlparse(url).netloc}"
    attention = social_attention(lead)
    return {
        'raw_id': stable_id(url, title), 'title': title, 'url': url,
        'summary': lead.get('note', lead.get('summary', '')),
        'published_at': lead.get('published_at', lead.get('submitted_at', '')),
        'image_url': lead.get('image_url', ''),
        'suggested_category': lead.get('category', ''),
        'social_attention': attention,
        'source': {
            'id': lead.get('source_id', f"social-{attention['platform'].lower().replace(' ', '-') }"),
            'name': lead.get('account', lead.get('submitted_by', provider.get('name', 'Public social post'))),
            'type': 'social',
            'ownership': f"Public account on {attention['platform']}"
        },
        'requires_verification': True
    }

def local_social_rows():
    path = ROOT / 'data/social_submissions.json'
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding='utf-8'))
    leads = payload.get('items', []) if isinstance(payload, dict) else payload
    return [row for lead in leads if (row := social_row(lead))]

def remote_social_rows(config):
    rows, errors = [], []
    for provider in config.get('social_signal_feeds', []):
        if not provider.get('enabled'):
            continue
        url = provider.get('url') or os.environ.get(provider.get('url_env', ''), '')
        if not url:
            continue
        headers = {'User-Agent': UA, 'Accept': 'application/json'}
        token = os.environ.get(provider.get('token_env', ''), '')
        if token:
            headers['Authorization'] = f'Bearer {token}'
        try:
            with urlopen(Request(url, headers=headers), timeout=25) as response:
                payload = json.loads(response.read().decode('utf-8-sig'))
            leads = payload.get('items', []) if isinstance(payload, dict) else payload
            rows.extend(row for lead in leads if (row := social_row(lead, provider)))
        except Exception as exc:
            errors.append({'source': provider['id'], 'error': str(exc)})
    return rows, errors

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
    all_rows.extend(local_social_rows())
    remote_rows, remote_errors = remote_social_rows(config)
    all_rows.extend(remote_rows)
    errors.extend(remote_errors)
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
