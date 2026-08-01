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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/chatgpt-input/latest.json")
    parser.add_argument("--output", default="data/processed/latest.json")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-5.6-terra"))
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for automated distillation.")

    bundle = json.loads((ROOT / args.input).read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schema/processed-news.schema.json").read_text(encoding="utf-8"))
    prompt = (ROOT / "prompts/process-news.md").read_text(encoding="utf-8")

    request_body = {
        "model": args.model,
        "store": False,
        "reasoning": {"effort": "medium"},
        "instructions": prompt,
        "input": [{
            "role": "user",
            "content": [{
                "type": "input_text",
                "text": "Distil this crawler batch into the required processed-news JSON:\n\n"
                        + json.dumps(bundle, ensure_ascii=False),
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

    processed = json.loads(extract_output_text(response))
    if not isinstance(processed.get("stories"), list) or not processed["stories"]:
        raise SystemExit("Model output contained no stories; the live feed was not changed.")

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(processed, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Distilled {len(processed['stories'])} stories with {args.model}: {output}")


if __name__ == "__main__":
    try:
        main()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"Distillation output was invalid: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
