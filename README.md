# Nazar India

Nazar India is a dependency-free, source-transparent Indian news aggregator. It crawls selected public RSS feeds, keeps a compact audit bundle in the repository, uses the OpenAI Responses API for structured editorial distillation, validates the result, and publishes the static site.

## Included

- Responsive homepage with lead and category sections.
- Search, category and source-type filters.
- Story details with original sources, evidence status, disagreements and confidence rationale.
- Date-based archive and source-methodology views.
- Browser-based independent/social lead submission and JSON export.
- RSS collector, ChatGPT bundle generator, processed-output validator, publisher and archive scripts.
- Four-hour GitHub Actions crawl, distillation and publishing workflow.
- No JavaScript framework or package installation required.

## Run locally

```powershell
.\serve.ps1
```

Open `http://localhost:8080`.

## Configure sources

Edit `config/sources.json` to add, disable or update public RSS sources. Only enable feeds intended for automated consumption, and continue to respect each publisher's terms, robots policy and applicable law.

Instagram and similar platforms should not be scraped through login bypasses or unstable HTML automation. Add public URLs through the website's **Submit a lead** form, export `social_submissions.json`, and place it in `data/social_submissions.json`. A future version can use approved platform APIs.

## Manual or local processing

```powershell
python scripts/scrape.py
python scripts/prepare_bundle.py
```

The crawler output ChatGPT can read is always:

- `data/chatgpt-input/latest.json`
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

The publisher merges by permanent story ID and moves stories older than 14 days into `data/archive/YYYY/MM.json`.

## Scheduled collection and publishing

`.github/workflows/collect.yml` runs at minute 17 every four hours and can also be started manually. It commits the raw inbox and `data/chatgpt-input/latest.json`, calls OpenAI with strict structured output, validates and publishes the live feed, and commits the result. The Cloudflare site reads the public website files from `main`, so a successful content commit becomes live without a separate deployment credential.

Add an Actions repository secret named `OPENAI_API_KEY` to enable automatic distillation. Without it, scheduled runs still save fresh crawler output for a manual ChatGPT pass but leave the last validated live feed online. An optional Actions variable named `OPENAI_MODEL` can override the default model.

## Deployment

The production site is `https://nazar-india.pages.dev`. Its Cloudflare worker serves only the public website paths and refreshes content from the repository's `main` branch, while retaining the last deployed build as a fallback if GitHub is temporarily unavailable.

## Editorial controls

- Do not infer truth from source popularity or repetition.
- Attribute official claims and political statements.
- Distinguish eyewitness material from independent corroboration.
- Do not publish unsupported criminal accusations, private personal data, graphic imagery or unverifiable identifying claims.
- Preserve source links and corrections.
- Add human editorial review before treating the feed as definitive reporting.
