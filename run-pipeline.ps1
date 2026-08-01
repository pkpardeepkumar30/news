$ErrorActionPreference = "Stop"
python scripts/scrape.py
python scripts/prepare_bundle.py
Write-Host "Upload data/chatgpt-input/latest.json to ChatGPT with prompts/process-news.md."
Write-Host "Save the response as data/processed/latest.json, then run:"
Write-Host "python scripts/publish.py"
