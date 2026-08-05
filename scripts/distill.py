#!/usr/bin/env python3
"""Distil the crawler bundle with the OpenAI Responses API.

The script uses only the Python standard library. Set OPENAI_API_KEY before
running it; OPENAI_MODEL may override the balanced default model.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://api.openai.com/v1/responses"


def extract_output_text(response: dict) -> str:
    if response.get("status") == "incomplete":
        reason = response.get("incomplete_details", {}).get("reason", "unknown reason")
        raise RuntimeError(f"Model response was incomplete: {reason}")
    chunks = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                chunks.append(content["text"])
            if content.get("type") == "refusal":
                raise RuntimeError(f"Model refused the batch: {content.get('refusal', 'no reason supplied')}")
    if not chunks:
        raise RuntimeError("The API response did not contain output text.")
    return "".join(chunks)


def distil_part(*, bundle: dict, schema: dict, prompt: str, model: str,
                 api_key: str, part_number: int, part_count: int,
                 story_limit: int) -> dict:
    request_body = {
        "model": model,
        "store": False,
        "reasoning": {"effort": "medium"},
        "instructions": prompt,
        "input": [{
            "role": "user",
            "content": [{
                "type": "input_text",
                "text": (
                    f"Distil collection part {part_number} of {part_count}. Return no more than "
                    f"{story_limit} strongest stories from this part; final merging happens after all parts.\n\n"
                    + json.dumps(bundle, ensure_ascii=False)
                ),
            }],
        }],
        "text": {
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "nazar_india_processed_news",
                "strict": True,
                "schema": schema,
            },
        },
        "max_output_tokens": 20000,
    }
    request = Request(
        API_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "NazarIndiaPipeline/0.2",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=300) as result:
            response = json.loads(result.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise SystemExit(f"OpenAI API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise SystemExit(f"OpenAI API request failed: {exc.reason}") from exc
    return json.loads(extract_output_text(response))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/chatgpt-input/latest.json")
    parser.add_argument("--output", default="data/processed/latest.json")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-5.6-terra"))
    parser.add_argument("--chunk-size", type=int, default=40)
    parser.add_argument("--max-stories", type=int, default=100)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for automated distillation.")

    bundle = json.loads((ROOT / args.input).read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schema/processed-news.schema.json").read_text(encoding="utf-8"))
    schema.pop("$schema", None)
    schema.pop("title", None)
    prompt = (ROOT / "prompts/process-news.md").read_text(encoding="utf-8")

    items = bundle.get("items", [])
    if not items:
        raise SystemExit("The prepared collection contains no items.")
    chunks = [items[index:index + args.chunk_size] for index in range(0, len(items), args.chunk_size)]
    per_chunk_limit = min(20, max(1, (args.max_stories + len(chunks) - 1) // len(chunks)))
    stories_by_id = {}
    for index, items_part in enumerate(chunks, start=1):
        part_bundle = {key: value for key, value in bundle.items() if key not in {"items", "parts"}}
        part_bundle.update({"part": index, "part_count": len(chunks), "items": items_part})
        processed_part = distil_part(
            bundle=part_bundle, schema=schema, prompt=prompt, model=args.model,
            api_key=api_key, part_number=index, part_count=len(chunks),
            story_limit=per_chunk_limit
        )
        for story in processed_part.get("stories", []):
            if len(stories_by_id) >= args.max_stories:
                break
            stories_by_id[story["id"]] = story
        print(f"Distilled part {index}/{len(chunks)}: {len(processed_part.get('stories', []))} stories")
    processed = {"stories": list(stories_by_id.values())[:args.max_stories]}
    if not processed["stories"]:
        raise SystemExit("Model output contained no stories; the live feed was not changed.")

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(processed, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Distilled {len(processed['stories'])} stories from {len(chunks)} parts with {args.model}: {output}")


if __name__ == "__main__":
    try:
        main()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"Distillation output was invalid: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
