#!/usr/bin/env python3
"""Stage only the public static site in dist/."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for name in ("index.html", "app.js", "styles.css"):
        shutil.copy2(ROOT / name, DIST / name)
    shutil.copy2(ROOT / "cloudflare-worker.js", DIST / "_worker.js")
    shutil.copytree(ROOT / "assets", DIST / "assets")
    (DIST / "data/archive").mkdir(parents=True)
    shutil.copy2(ROOT / "data/news.json", DIST / "data/news.json")
    archive = ROOT / "data/archive"
    for source in archive.rglob("*.json"):
        target = DIST / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(f"Static site staged: {DIST}")


if __name__ == "__main__":
    main()
