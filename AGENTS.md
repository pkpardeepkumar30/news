# Nazar India agent workflow

When asked to process the latest news collection, read these files in order:

1. `data/chatgpt-input/latest.json` — the balanced collection index. When it lists `parts`, read every listed part before selecting stories.
2. `prompts/process-news.md` — the editorial and safety rules.
3. `schema/processed-news.schema.json` — the exact output contract.

Write the resulting JSON to `data/processed/latest.json` as UTF-8 without a byte-order mark (BOM). Never invent a source, quotation, date, image, engagement figure or verification step. Keep uncertainty and attribution explicit. Review all supplied parts, dynamically identify consequential events from the available evidence, merge duplicate events, and aim for 60–100 well-supported stories when the collection supports that range; never fill the target with weak items. Do not maintain incident-specific or region-specific priority lists. Explicitly review major protests, governance and administration, Sports, and International & Geopolitics. Treat social engagement as an attention signal rather than verification. In `data/chatgpt-input/latest.json`, `input_count` is the total collected before selection; `supplied_count` (or, for older bundles, the length of `items`) is the number supplied for processing.

After writing processed output, run:

```text
python scripts/publish.py
python scripts/validate.py
python scripts/build_static.py
```

Do not overwrite or hand-edit `data/inbox/latest.json`; it is collection evidence. The scheduled GitHub workflow owns new collection files and automatic publication.
