# Nazar India

Nazar India is a dependency-free, source-transparent Indian news aggregator. It crawls selected public RSS feeds, keeps a compact audit bundle in the repository, uses the OpenAI Responses API for structured editorial distillation, validates the result, and publishes the static site.

## Included

- Responsive homepage with dynamically populated lead and category sections, including Protests and Governance & Administration.
- Search, category and source-type filters.
- Story details with original sources, evidence status, disagreements and confidence rationale.
- Date-based archive and source-methodology views.
- Permanent server-rendered HTML pages for current and archived stories, with canonical URLs and `NewsArticle` structured data.
- Search-engine discovery through `robots.txt`, a generated XML sitemap, homepage canonical metadata and site/organization structured data.
- RSS collector, ChatGPT bundle generator, processed-output validator, publisher and archive scripts.
- Four-hour GitHub Actions collection, balanced 200-item preparation, chunked distillation and publishing workflow.
- No JavaScript framework or package installation required.

## Run locally

```powershell
.\serve.ps1
```

Open `http://localhost:8080`.

## Configure sources

Edit `config/sources.json` to add, disable or update public RSS sources. Only enable feeds intended for automated consumption, and continue to respect each publisher's terms, robots policy and applicable law.

Instagram and similar platforms are not scraped through login bypasses or unstable HTML automation. Social discovery can enter through the repository-managed input file or an approved monitoring/API provider; there is no public submission form. The optional provider is enabled by setting GitHub Actions secrets named `SOCIAL_SIGNALS_URL` and, when required, `SOCIAL_SIGNALS_TOKEN`.

The social endpoint may return an array, or an object with an `items` array. Each entry accepts `url`, `title`, `note`, `published_at`, `image_url`, `platform`, `account`, and a `metrics` object containing `views`, `likes`, `comments`, `shares` and `reposts`. Engagement affects discovery priority but never counts as factual corroboration.

Scheduled collection retries failed publication feeds once after five minutes. Only failures that remain after the retry are recorded in the final collection error list; successful recoveries are recorded in its retry log. Other enabled sources continue to provide coverage while a particular publisher is unavailable.

## Manual or local processing

```powershell
python scripts/scrape.py
python scripts/prepare_bundle.py
```

The crawler output ChatGPT can read is always:

- `data/chatgpt-input/latest.json`
- `data/chatgpt-input/parts/part-*.json` when the collection is split for reliable processing
- `prompts/process-news.md`
- `schema/processed-news.schema.json`

Repository-aware ChatGPT/Codex sessions also receive the same workflow from `AGENTS.md`. Because the repository is public, the latest compact input is directly readable at `https://raw.githubusercontent.com/pkpardeepkumar30/news/main/data/chatgpt-input/latest.json`.

For a manual ChatGPT pass, ask it to produce JSON conforming to the schema and save the result as `data/processed/latest.json`, then run:

```powershell
python scripts/publish.py
python scripts/validate.py
python scripts/build_static.py
```

For a fully automated local run, set `OPENAI_API_KEY` and run `.\run-pipeline.ps1`. `OPENAI_MODEL` is optional and defaults to `gpt-5.6-terra`.

The publisher treats each validated result as the complete live basket, capped at 150 stories. Previously live stories that are not selected in the new basket move into `data/archive/YYYY/MM.json`, so stale items cannot accumulate beyond the publication limit.

## Scheduled collection and publishing

`.github/workflows/collect.yml` runs at minute 17 every four hours and can also be started manually. It prepares up to 200 dynamically ranked and source-balanced reports in 40-item parts, reserving 12 discovery candidates for each broad category before the 200-report cutoff. The final portfolio contains up to 150 stories with at least five well-supported stories per category, then validates, publishes and commits the live feed. Candidate reservation uses broad taxonomy signals and source-section hints rather than named incidents or regions; final classification remains an editorial decision. Unsupported individual candidates are filtered by source URL and replaced from the valid surplus instead of stopping the complete batch. If the remaining evidence cannot support a required category or source-diversity minimum, publication preserves the last validated feed. The optional API path processes parts separately to avoid losing a large structured response at an output-token limit. The Cloudflare site reads the public website files from `main`, so a successful content commit becomes live without a separate deployment credential.

Add an Actions repository secret named `OPENAI_API_KEY` to enable automatic distillation. Without it, scheduled runs still save fresh crawler output for a manual ChatGPT pass but leave the last validated live feed online. An optional Actions variable named `OPENAI_MODEL` can override the default model.

## Deployment

The production site is `https://nazar-india.pages.dev`. Its Cloudflare worker serves only the public website paths and refreshes content from the repository's `main` branch, while retaining the last deployed build as a fallback if GitHub is temporarily unavailable.

`python scripts/build_static.py` writes the Cloudflare output to `dist/`. In addition to the application assets, the build creates `dist/sitemap.xml` and one stable page under `dist/stories/` for every current or archived story. Cloudflare Pages must use that command as its build command and `dist` as its output directory.

To request Google indexing, add `https://nazar-india.pages.dev/` as a URL-prefix property in Google Search Console, complete Google's ownership verification, submit `https://nazar-india.pages.dev/sitemap.xml`, and use URL Inspection to request indexing for the homepage. Search Console verification requires access to the site's Google account and is not performed by the build.

## Editorial controls

- Do not infer truth from source popularity or repetition.
- Attribute official claims and political statements.
- Distinguish eyewitness material from independent corroboration.
- Treat social engagement as evidence of attention, not evidence that a claim is true.
- Publish reader-facing text entirely in English and reject output that retains non-Latin-script copy.
- Keep a strict majority of published stories rooted in independent, local or social discovery; established-media-origin stories may never exceed half of the portfolio.
- Treat the first listed story source as its discovery source. Social-origin stories require at least one distinct non-social corroborating source before publication.
- Use named independent reporters and public-interest creators as discovery leads, not trusted authorities or a fixed editorial checklist.
- Reject portfolios built from repeated headline, summary, significance or evidence templates; each story must use fact-specific editorial language.
- Synthesize and rephrase source material; reject copied headlines and long verbatim passages.
- Do not publish unsupported criminal accusations, private personal data, graphic imagery or unverifiable identifying claims.
- Preserve source links and corrections.
- Treat repeated high-reach coverage as a prominence signal, not independent corroboration. Routine saturated stories may be excluded; retained stories are visibly flagged as widely covered.
- Never infer reliability, bias or story value solely from a publisher's ownership.
- Add human editorial review before treating the feed as definitive reporting.
