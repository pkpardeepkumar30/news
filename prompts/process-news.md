# Nazar India processing prompt

Read `data/chatgpt-input/latest.json`, every file listed in its `parts` array, and `schema/processed-news.schema.json` as the exact output contract.

Produce `data/processed/latest.json`.

Rules:

1. Discover importance from the complete supplied collection. Do not use a permanent list of named incidents, institutions, people, regions or keywords as an editorial priority list. Consider likely public impact, number and independence of reports, affected population, duration, institutional response, consequences, geographic reach and observed social attention.
2. Cluster reports about the same event into one story. Syndicated copies, embedded copies and repeated posts are not independent confirmation.
3. Preserve direct links to every source used. Never invent a source, quotation, date, image, engagement number or verification step.
4. Treat government, police, political-party and corporate material as attributed claims unless supported by primary records or independent evidence.
5. Treat Instagram Reels, YouTube videos, X posts, Facebook posts and other public social material as discovery leads or eyewitness evidence. Engagement may show that an issue is receiving attention; it does not establish that the post or its claims are true. State what can and cannot be verified.
6. A confidence label evaluates the evidence available in the input, not whether a claim is absolutely true. Use `High` only when important claims are supported by primary documents or genuinely independent corroboration. Use `Low` when identity, date, location or core claims remain unresolved.
7. Assign the best-fit category from the story's substance, not its source, location, a source hint or a prior example. Use the broad taxonomy in the schema. The final publication must contain at least five well-supported stories in every category. If the supplied evidence cannot support that minimum, stop publication and report the shortfall rather than inventing or misclassifying stories.
8. Use `Protests` when sustained or consequential collective action is the central development in India or abroad: demonstrations, marches, strikes, sit-ins, blockades, occupations or comparable movements. Prioritise material scale, duration, public impact, coercive response, negotiations or policy consequences over routine symbolic events. Report participants' demands and authorities' responses with attribution.
9. Use `Governance & Administration` for consequential bills, enacted laws, regulations, major central or state policy decisions, senior bureaucratic appointments or transfers, public audits, raids, investigations, enforcement action, institutional failures and other significant administration of public power. Distinguish a proposal, introduction, passage, assent, notification and implementation.
10. Use `Politics & Elections` for party competition, campaigns, elections and legislative politics when public administration or a protest is not the central subject. Use `States & Local` for important regional developments that do not fit a more specific beat. A story about a local protest still belongs in `Protests`; a state audit still belongs in `Governance & Administration`.
11. Prefer consequential, underreported public-interest reporting, including credible single-source local reporting. Attribute uncertainty instead of silently dropping a story merely because national outlets have not covered it.
12. Write neutral summaries of 45–90 words and a separate `why_it_matters` paragraph of 25–60 words.
13. Choose a relevant source image URL when one is provided. Otherwise use the matching fallback under `assets/images/`, including `protests.svg`, `governance.svg` and `international.svg`.
14. Exclude private personal data, graphic imagery, doxxing, unsupported accusations and content that cannot be responsibly contextualised.
15. Use a stable, URL-derived lowercase story ID so later batches update the same event instead of creating duplicates.
16. Across the complete supplied collection, aim for 60–100 stories and never return more than 100. Review every supplied part before final selection. Reserve at least five positions for each broad category, then allocate remaining positions dynamically by importance. Preserve geographic and subject diversity without using fixed incident or regional quotas.
17. Use ISO 8601 timestamps. When a timestamp is ambiguous, preserve it conservatively and lower confidence rather than inventing precision.
18. Return only the JSON object required by the schema; do not wrap it in Markdown. Save the file as UTF-8 without a byte-order mark (BOM), preserving Unicode punctuation, currency symbols and names without re-encoding them.
19. Write all reader-facing fields in plain editorial language. Refer to "available source material", "available reporting" or the specific evidence; never expose internal terms such as crawler, crawl batch, bundle, prompt, schema, model or processing pipeline.
20. Set `coverage.status` from evidence in the supplied collection: `widely_covered` only when the same event appears across several distinct high-reach reports or the supplied evidence establishes saturation; `underreported` when coverage is limited despite clear public value; `developing` for a fast-moving event; otherwise `unknown`. Count distinct source desks in `coverage.source_count` and explain the assessment briefly.
21. Exclude routine, repetitive widely covered stories unless there is a material new fact, accountability angle, public-safety consequence or undercovered local impact. When such a story is retained, flag it as `widely_covered` and normally keep its underreported score at 35 or below.
22. Never infer truth, bias, saturation or story value solely from corporate ownership. Ownership is context, not evidence. Apply the same verification standards to every publisher and base prominence decisions on observable reporting and evidence.
