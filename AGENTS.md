# Nazar India agent workflow

When asked to process the latest news collection, read these files in order:

1. `data/chatgpt-input/latest.json` — the balanced collection index. When it lists `parts`, read every listed part before selecting stories.
2. `prompts/process-news.md` — the editorial and safety rules.
3. `schema/processed-news.schema.json` — the exact output contract.

Write the resulting JSON to `data/processed/latest.json` as UTF-8 without a byte-order mark (BOM). Never invent a source, quotation, date, image, engagement figure or verification step. Keep uncertainty and attribution explicit. Write every reader-facing field entirely in natural English, translating or transliterating non-English reporting, and synthesize rather than copy source headlines or descriptions. Review all supplied parts, dynamically identify consequential events from the available evidence, merge duplicate events, and return no more than 150 well-supported stories. The final result must contain at least five well-supported stories in every schema category; if the evidence cannot support that minimum, report the shortfall and do not publish. Never fill the target by inventing or misclassifying weak items. The first source listed for each story must be its discovery source. More than half of the final stories must originate from independent, local or social sources, while no more than half may originate from established media. Any social-origin story requires a distinct non-social corroborating source and a source count of at least two. Never treat a named account, engagement or repeated reposts as verification. Treat story IDs as editorial identifiers rather than exact matches to collection raw IDs; verify support using source URLs. Remove unsupported sources or stories and refill from valid surplus candidates instead of aborting the complete publication for an individual bad selection. Do not maintain incident-specific or region-specific priority lists. Treat social engagement as an attention signal rather than verification. In `data/chatgpt-input/latest.json`, `input_count` is the total collected before selection; `supplied_count` (or, for older bundles, the length of `items`) is the number supplied for processing.

After writing processed output, run:

```text
python scripts/publish.py
python scripts/validate.py --min-per-category 5
python scripts/build_static.py
```

Do not overwrite or hand-edit `data/inbox/latest.json`; it is collection evidence. The scheduled GitHub workflow owns new collection files and automatic publication.
