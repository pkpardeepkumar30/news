# Nazar India agent workflow

When asked to process the latest news crawl, read these files in order:

1. `data/chatgpt-input/latest.json` — the compact, balanced crawler output.
2. `prompts/process-news.md` — editorial and safety rules.
3. `schema/processed-news.schema.json` — the exact output contract.

Write the resulting JSON to `data/processed/latest.json`. Never invent a source, quotation, date, image or verification step. Keep uncertainty and attribution explicit, and prefer fewer well-supported stories over filling a quota.

After writing processed output, run:

```text
python scripts/publish.py
python scripts/validate.py
python scripts/build_static.py
```

Do not overwrite or hand-edit `data/inbox/latest.json`; it is crawler evidence. The scheduled GitHub workflow owns new crawl files and automatic publication.
