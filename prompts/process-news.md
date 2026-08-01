# Nazar India processing prompt

Read `data/chatgpt-input/latest.json` and use `schema/processed-news.schema.json` as the exact output contract.

Produce `data/processed/latest.json`.

Rules:

1. Cluster reports about the same event into one story. Syndicated copies and repeated posts are not independent confirmation.
2. Preserve direct links to every source used. Never invent a source, quotation, date, image or verification step.
3. Treat government and police material as attributed official claims unless supported by independent evidence.
4. Treat Instagram, YouTube, X, Facebook and other public posts as leads or eyewitness evidence. State what can and cannot be verified from the post.
5. A confidence label evaluates the evidence available in the input, not whether a claim is absolutely true.
6. Use `High` only when important claims are supported by primary documents or genuinely independent corroboration. Use `Low` when identity, date, location or core claims remain unresolved.
7. Prefer underreported public-interest stories. Do not increase importance merely because a story is sensational.
8. Write neutral summaries of 45–90 words and a separate `why_it_matters` paragraph of 25–60 words.
9. Choose a relevant source image URL when one is provided. Otherwise use the category fallback under `assets/images/`.
10. Exclude private personal data, graphic imagery, doxxing, unsupported accusations and content that cannot be responsibly contextualised.
11. Use a stable, URL-derived lowercase story ID so later batches update the same event instead of creating duplicates.
12. Return no more than 24 stories. Prefer public-interest value, geographic variety and evidence quality over filling a quota.
13. Use ISO 8601 timestamps. When an RSS timestamp is ambiguous, preserve it conservatively and lower confidence rather than inventing precision.
14. Return only the JSON object required by the schema; do not wrap it in Markdown.
