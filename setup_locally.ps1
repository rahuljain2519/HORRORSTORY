# Horror Story Agent - Local Windows setup and run
# Run once to install dependencies.

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "==> Installing Python dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host ""
Write-Host "Done! Missing pieces for FULL runs:" -ForegroundColor Yellow
Write-Host " 1. ffmpeg        ->  winget install Gyan.FFmpeg  (then restart terminal)"
Write-Host " 2. Ollama (local storygen) ->  ollama.com  then:  ollama pull llama3.2"
Write-Host " 3. Devanagari font -> put a .ttf into assets\fonts\ (e.g. Nirmala.ttf)"
Write-Host "    (copy from C:\Windows\Fonts\Nirmala.ttf)"
Write-Host " 4. Background horror music -> drop any royalty-free mp3 into assets\bg_music\"
Write-Host " 5. Copy .env.example -> .env and fill YouTube creds if you want uploads"
Write-Host ""
Write-Host "Test:  python src\pipeline.py"