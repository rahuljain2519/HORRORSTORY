# Horror Story Agent - run the full pipeline locally (uses local Ollama + free APIs)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

python src\pipeline.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pipeline failed. Check errors above." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "Done! Videos are in output\full_videos and output\shorts" -ForegroundColor Green