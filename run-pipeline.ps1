$ErrorActionPreference = "Stop"
python scripts/scrape.py
python scripts/prepare_bundle.py
if ($env:OPENAI_API_KEY) {
  python scripts/distill.py
  python scripts/publish.py
  python scripts/validate.py
  python scripts/build_static.py
} else {
  Write-Host "Crawler output is ready at data/chatgpt-input/latest.json."
  Write-Host "Set OPENAI_API_KEY to distil and publish it automatically."
}
