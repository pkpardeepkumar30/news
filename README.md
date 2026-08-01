# Nazar India

A dependency-free, GitHub Pages-ready MVP for source-transparent Indian news aggregation. It is designed around a manual ChatGPT processing step that can later be replaced with an API or another automation service.

## Included

- Responsive multi-column homepage with a lead story, category sections and image cards.
- Search, category and source-type filters.
- Story detail view with original sources, evidence status, disagreements and confidence rationale.
- Archive view organised by publication date.
- Source-methodology page.
- Browser-based independent/social lead submission and JSON export.
- RSS collector, compact ChatGPT bundle generator, processed-output validator, publisher and archive script.
- Four-hour GitHub Actions collection schedule and GitHub Pages deployment workflow.
- No JavaScript framework or package installation required.

The included stories and sources are explicitly marked as demo content. They are fictional examples and must not be presented as current reporting.

## Run locally

From the project directory:

```powershell
.\serve.ps1
```

Open `http://localhost:8080`.

## Configure sources

Edit `config/sources.json`. The entries are disabled placeholders. Set `enabled` to `true` only after replacing the URL and confirming that automated collection is permitted by the source's terms, robots policy and applicable law.

Instagram and similar platforms should not be scraped through login bypasses or unstable HTML automation. Add public URLs through the website's **Submit a lead** form, export `social_submissions.json`, and place it in `data/social_submissions.json`. A later version can use approved platform APIs.

## Manual processing workflow

```powershell
python scripts/scrape.py
python scripts/prepare_bundle.py
```

Upload these files to ChatGPT:

- `data/chatgpt-input/latest.json`
- `prompts/process-news.md`
- `schema/processed-news.schema.json`

Ask ChatGPT to produce JSON conforming to the schema. Save the result as:

```text
data/processed/latest.json
```

Publish it:

```powershell
python scripts/publish.py
python scripts/validate.py
```

The publisher merges by permanent story ID and moves stories older than 14 days into `data/archive/YYYY/MM.json`.

## Scheduled collection

`.github/workflows/collect.yml` runs every four hours and commits the latest raw and ChatGPT-ready files. This does not call ChatGPT automatically. A ChatGPT scheduled task can read a public raw file and return processed output, but the normal GitHub connection may not be able to commit the result. Keep the manual publish step for the MVP.

## Deployment

1. Create a GitHub repository and push this folder to its `main` branch.
2. In GitHub, open **Settings → Pages**.
3. Set **Source** to **GitHub Actions**.
4. Run the **Deploy static site** workflow.

## Editorial controls

- Do not infer truth from source popularity or repetition.
- Attribute official claims and political statements.
- Distinguish eyewitness material from independent corroboration.
- Do not publish unsupported criminal accusations, private personal data, graphic imagery or unverifiable identifying claims.
- Preserve source links and corrections.
- Add human editorial review before making the service public.
