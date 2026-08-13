#!/usr/bin/env python3
"""Build the public site, permanent story pages and search-engine discovery files."""
from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SITE_URL = "https://nazar-india.pages.dev"
SITE_NAME = "Nazar India"
FALLBACK_IMAGE = f"{SITE_URL}/assets/images/fallback.svg"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def story_slug(story: dict) -> str:
    """Return a stable URL segment derived from the persistent story ID."""
    value = re.sub(r"[^a-z0-9]+", "-", str(story.get("id", "")).lower()).strip("-")
    if not value:
        raise ValueError("Every published story must have a non-empty ID")
    return value[:160]


def story_path(story: dict) -> str:
    return f"/stories/{story_slug(story)}"


def story_output_path(story: dict) -> Path:
    """Map a clean public story URL to Cloudflare Pages' backing HTML file."""
    return Path("stories") / f"{story_slug(story)}.html"


def clean_text(value: object, fallback: str = "") -> str:
    return " ".join(str(value or fallback).split())


def canonical_timestamp(value: object, fallback: object = "") -> str:
    candidate = clean_text(value, str(fallback or ""))
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(candidate)
        except (TypeError, ValueError):
            parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def description_for(story: dict) -> str:
    value = clean_text(story.get("summary"), story.get("title", "Nazar India story"))
    if len(value) <= 160:
        return value
    return value[:157].rsplit(" ", 1)[0] + "…"


def public_image(story: dict) -> str:
    value = clean_text((story.get("image") or {}).get("url"))
    return value if urlparse(value).scheme in {"http", "https"} else FALLBACK_IMAGE


def json_ld(data: dict) -> str:
    # Prevent user-controlled text from prematurely closing the script element.
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def render_sources(story: dict) -> str:
    rows = []
    for source in story.get("sources") or []:
        url = clean_text(source.get("url"))
        name = html.escape(clean_text(source.get("name"), "Original source"))
        role = html.escape(clean_text(source.get("role"), source.get("type", "Source")))
        if urlparse(url).scheme not in {"http", "https"}:
            continue
        rows.append(
            f'<li><a href="{html.escape(url, quote=True)}" rel="noopener noreferrer">'
            f"<strong>{name}</strong><span>{role}</span></a></li>"
        )
    return "".join(rows) or "<li>No public source link is available.</li>"


def render_story_page(story: dict) -> str:
    title_text = clean_text(story.get("title"), "Nazar India story")
    summary_text = clean_text(story.get("summary"))
    why_text = clean_text(story.get("why_it_matters"))
    evidence_text = clean_text(story.get("evidence_status"))
    category_text = clean_text(story.get("category"), "News")
    location_text = clean_text(story.get("location"), "India")
    published = canonical_timestamp(story.get("published_at"), story.get("updated_at"))
    modified = canonical_timestamp(story.get("updated_at"), published)
    canonical = SITE_URL + story_path(story)
    image_url = public_image(story)
    image_alt = clean_text((story.get("image") or {}).get("alt"), title_text)
    description = description_for(story)
    confidence = story.get("confidence") or {}
    coverage = story.get("coverage") or {}
    source_urls = [
        clean_text(source.get("url"))
        for source in story.get("sources") or []
        if urlparse(clean_text(source.get("url"))).scheme in {"http", "https"}
    ]
    structured = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title_text,
        "description": description,
        "image": [image_url],
        "datePublished": published,
        "dateModified": modified,
        "articleSection": category_text,
        "inLanguage": "en-IN",
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "author": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/"},
        "publisher": {"@type": "NewsMediaOrganization", "name": SITE_NAME, "url": SITE_URL + "/"},
    }
    if source_urls:
        structured["isBasedOn"] = source_urls

    disagreements = story.get("disagreements") or []
    gaps_html = ""
    if disagreements:
        gaps_html = "<h2>Disagreements or gaps</h2><ul>" + "".join(
            f"<li>{html.escape(clean_text(item))}</li>" for item in disagreements
        ) + "</ul>"
    coverage_html = ""
    if coverage:
        status = clean_text(coverage.get("status")).replace("_", " ").title()
        rationale = html.escape(clean_text(coverage.get("rationale")))
        count = coverage.get("source_count")
        count_html = f" across {html.escape(str(count))} source desk{'s' if count != 1 else ''}" if count is not None else ""
        coverage_html = f"<h2>Coverage assessment</h2><p><strong>{html.escape(status)}</strong>{count_html}.</p><p>{rationale}</p>"

    return f"""<!doctype html>
<html lang="en-IN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="description" content="{html.escape(description, quote=True)}">
  <link rel="canonical" href="{html.escape(canonical, quote=True)}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{html.escape(title_text, quote=True)}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:url" content="{html.escape(canonical, quote=True)}">
  <meta property="og:image" content="{html.escape(image_url, quote=True)}">
  <meta property="article:published_time" content="{html.escape(published, quote=True)}">
  <meta property="article:modified_time" content="{html.escape(modified, quote=True)}">
  <meta property="article:section" content="{html.escape(category_text, quote=True)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title_text, quote=True)}">
  <meta name="twitter:description" content="{html.escape(description, quote=True)}">
  <meta name="twitter:image" content="{html.escape(image_url, quote=True)}">
  <title>{html.escape(title_text)} | {SITE_NAME}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/styles.css?v=20260806-3">
  <script type="application/ld+json">{json_ld(structured)}</script>
</head>
<body class="story-page-body">
  <header class="story-page-header">
    <a class="brand" href="/" aria-label="Nazar India home"><span class="brand-mark" aria-hidden="true">न</span><span><strong>Nazar</strong><small>INDIA</small></span></a>
    <a class="story-page-back" href="/">← Current briefing</a>
  </header>
  <main class="story-page-main">
    <article class="story-page-article">
      <p class="eyebrow">{html.escape(category_text)} · {html.escape(location_text)}</p>
      <h1>{html.escape(title_text)}</h1>
      <p class="story-page-date">Published <time datetime="{html.escape(published, quote=True)}">{html.escape(published)}</time></p>
      <img class="story-page-image" src="{html.escape(image_url, quote=True)}" alt="{html.escape(image_alt, quote=True)}">
      <p class="story-page-summary">{html.escape(summary_text)}</p>
      <div class="story-page-grid">
        <div>
          <h2>Why it matters</h2><p>{html.escape(why_text)}</p>
          <h2>Evidence assessment</h2><p>{html.escape(evidence_text)}</p>
          <p><strong>{html.escape(clean_text(confidence.get('level'), 'Unrated'))} confidence</strong> — {html.escape(clean_text(confidence.get('rationale')))}</p>
          {coverage_html}
          {gaps_html}
        </div>
        <aside><h2>Original sources</h2><ul class="story-page-sources">{render_sources(story)}</ul><p class="story-page-disclosure">Nazar India synthesises and rephrases source material. Follow the links to read the original reporting.</p></aside>
      </div>
    </article>
  </main>
  <footer class="story-page-footer"><a href="/">Nazar India</a><span>Source-transparent news coverage</span></footer>
</body>
</html>
"""


def collect_stories(current: dict) -> list[dict]:
    by_id: dict[str, dict] = {}
    for story in current.get("stories") or []:
        by_id[str(story.get("id", ""))] = story
    archive_root = ROOT / "data/archive"
    if archive_root.exists():
        for source in sorted(archive_root.rglob("*.json")):
            payload = load_json(source)
            for story in payload.get("stories") or []:
                by_id.setdefault(str(story.get("id", "")), story)
    by_id.pop("", None)
    return list(by_id.values())


def write_sitemap(stories: list[dict], generated_at: str) -> None:
    rows = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "  <url>",
        f"    <loc>{SITE_URL}/</loc>",
        f"    <lastmod>{html.escape(canonical_timestamp(generated_at))}</lastmod>",
        "  </url>",
    ]
    for story in sorted(stories, key=lambda item: clean_text(item.get("updated_at")), reverse=True):
        rows.extend(
            [
                "  <url>",
                f"    <loc>{SITE_URL}{story_path(story)}</loc>",
                f"    <lastmod>{html.escape(canonical_timestamp(story.get('updated_at'), story.get('published_at')))}</lastmod>",
                "  </url>",
            ]
        )
    rows.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for name in ("index.html", "app.js", "styles.css", "robots.txt"):
        shutil.copy2(ROOT / name, DIST / name)
    shutil.copy2(ROOT / "cloudflare-worker.js", DIST / "_worker.js")
    shutil.copytree(ROOT / "assets", DIST / "assets")
    (DIST / "data/archive").mkdir(parents=True)
    shutil.copy2(ROOT / "data/news.json", DIST / "data/news.json")
    archive = ROOT / "data/archive"
    for source in archive.rglob("*.json"):
        target = DIST / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    current = load_json(ROOT / "data/news.json")
    stories = collect_stories(current)
    story_dir = DIST / "stories"
    story_dir.mkdir()
    seen_paths: set[str] = set()
    for story in stories:
        path = story_path(story)
        if path in seen_paths:
            raise ValueError(f"Duplicate permanent story path: {path}")
        seen_paths.add(path)
        (DIST / story_output_path(story)).write_text(render_story_page(story), encoding="utf-8")
    write_sitemap(stories, clean_text(current.get("generated_at")))
    print(f"Static site staged: {DIST} ({len(stories)} permanent story pages)")


if __name__ == "__main__":
    main()
