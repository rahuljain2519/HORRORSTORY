<#
.SYNOPSIS
    Guides you through generating all 4 secrets for the horror story agent.
.DESCRIPTION
    Run this script on your Windows machine. It will:
    1. Open Google Cloud Console for YouTube OAuth setup
    2. Open Google AI Studio for Gemini API key
    3. Run the YouTube OAuth flow locally
    4. Push all secrets to GitHub via browser
.NOTES
    Sign in with the SAME Google account that owns your YouTube channel
    @HORROR-GPAY before running this script.
#>
param(
    [string]$ChannelEmail = "YOUR_YOUTUBE_GOOGLE_EMAIL"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath "$PSScriptRoot"

Write-Host ""
Write-Host "================================================" -ForegroundColor Magenta
Write-Host "   HORROR STORY AGENT - SECRET GENERATOR" -ForegroundColor Magenta
Write-Host "   Channel: @HORROR-GPAY" -ForegroundColor Magenta
Write-Host "================================================" -ForegroundColor Magenta
Write-Host ""

# ------------------------------------------------------------------
# STEP 1: Google Cloud Project + YouTube OAuth Credentials
# ------------------------------------------------------------------
Write-Host "[STEP 1/4] GOOGLE CLOUD PROJECT + YOUTUBE OAUTH" -ForegroundColor Yellow
Write-Host "---------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "A new browser tab will open. Sign in with the Google account" -ForegroundColor White
Write-Host "that OWNS the YouTube channel @HORROR-GPAY." -ForegroundColor White
Write-Host ""

Start-Sleep -Seconds 2
Start-Process "https://console.cloud.google.com/projectcreate?project=horror-story-agent"

Write-Host ""
Write-Host "  a) Project name: horror-story-agent" -ForegroundColor Cyan
Write-Host "  b) Click CREATE" -ForegroundColor Cyan
Write-Host "  c) Wait for project creation, then:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  NEXT: Enable YouTube Data API v3" -ForegroundColor Green
Start-Sleep -Seconds 1
Start-Process "https://console.cloud.google.com/apis/library/youtube.googleapis.com?project=horror-story-agent"

Write-Host ""
Write-Host "  d) Click ENABLE" -ForegroundColor Cyan
Write-Host "  e) Go back to project dashboard" -ForegroundColor Cyan
Write-Host ""
Write-Host "  NEXT: Create OAuth Consent Screen" -ForegroundColor Green
Start-Sleep -Seconds 1
Start-Process "https://console.cloud.google.com/apis/credentials/consent?project=horror-story-agent"

Write-Host ""
Write-Host "  f) User type: External" -ForegroundColor Cyan
Write-Host "  g) App name: Horror Story Agent" -ForegroundColor Cyan
Write-Host "  h) User support email: your email" -ForegroundColor Cyan
Write-Host "  i) Developer contact: your email" -ForegroundColor Cyan
Write-Host "  j) Save & Continue" -ForegroundColor Cyan
Write-Host ""
Write-Host "  k) On 'Scopes' page: click ADD OR REMOVE SCOPES" -ForegroundColor Cyan
Write-Host "  l) Search: youtube.upload" -ForegroundColor Cyan
Write-Host "  m) Check: https://www.googleapis.com/auth/youtube.upload" -ForegroundColor Cyan
Write-Host "  n) Click UPDATE -> SAVE AND CONTINUE (x3)" -ForegroundColor Cyan
Write-Host ""

Write-Host "  NEXT: Create OAuth Client ID" -ForegroundColor Green
Start-Sleep -Seconds 1
Start-Process "https://console.cloud.google.com/apis/credentials?project=horror-story-agent"

Write-Host ""
Write-Host "  o) Click CREATE CREDENTIALS -> OAuth client ID" -ForegroundColor Cyan
Write-Host "  p) Application type: Desktop app" -ForegroundColor Cyan
Write-Host "  q) Name: Horror Story Agent" -ForegroundColor Cyan
Write-Host "  r) Click CREATE" -ForegroundColor Cyan
Write-Host ""
Write-Host "  s) COPY the Client ID and Client Secret" -ForegroundColor Cyan
Write-Host ""

Write-Host ""
Write-Host "  --> Paste your CLIENT ID here:" -ForegroundColor White
$CLIENT_ID = Read-Host "Client ID"
Write-Host "  --> Paste your CLIENT SECRET here:" -ForegroundColor White
$CLIENT_SECRET = Read-Host "Client Secret"

if (-not $CLIENT_ID -or -not $CLIENT_SECRET) {
    Write-Host "ERROR: Client ID and Secret are required!" -ForegroundColor Red
    exit 1
}

# Save to .env
@"
STORY_API_MODE=gemini
GOOGLE_AI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
YOUTUBE_CLIENT_ID=$CLIENT_ID
YOUTUBE_CLIENT_SECRET=$CLIENT_SECRET
YOUTUBE_REFRESH_TOKEN=
YOUTUBE_PRIVACY=private
VIDEO_ORIENTATION=vertical
"@ | Set-Content ".env" -Encoding UTF8

Write-Host "  -> Saved to .env" -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------------
# STEP 2: Gemini API Key (free)
# ------------------------------------------------------------------
Write-Host "[STEP 2/4] GEMINI API KEY (FREE - NO COST)" -ForegroundColor Yellow
Write-Host "---------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Start-Process "https://aistudio.google.com/apikey"
Write-Host "  a) Sign in with the same Google account" -ForegroundColor Cyan
Write-Host "  b) Click 'Create API Key'" -ForegroundColor Cyan
Write-Host "  c) Select any project or create new" -ForegroundColor Cyan
Write-Host "  d) COPY the API key" -ForegroundColor Cyan
Write-Host ""

Write-Host "  --> Paste your GEMINI API KEY here:" -ForegroundColor White
$GEMINI_KEY = Read-Host "Gemini API Key"

if ($GEMINI_KEY) {
    $env_content = Get-Content ".env" -Raw
    $env_content = $env_content -replace "^GOOGLE_AI_API_KEY=$", "GOOGLE_AI_API_KEY=$GEMINI_KEY"
    $env_content | Set-Content ".env" -Encoding UTF8
    Write-Host "  -> Saved to .env" -ForegroundColor Green
}
Write-Host ""

# ------------------------------------------------------------------
# STEP 3: YouTube OAuth Refresh Token
# ------------------------------------------------------------------
Write-Host "[STEP 3/4] YOUTUBE REFRESH TOKEN (browser flow)" -ForegroundColor Yellow
Write-Host "---------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Running auth_helper.py -- this opens a browser window." -ForegroundColor White
Write-Host "Sign in with the YouTube channel's Google account and APPROVE." -ForegroundColor White
Write-Host ""
Start-Sleep -Seconds 2
python src\auth_helper.py

Write-Host ""
Write-Host "  --> If you see a REFRESH TOKEN above, paste it below." -ForegroundColor White
$REFRESH_TOKEN = Read-Host "Refresh Token"

if ($REFRESH_TOKEN) {
    $env_content = Get-Content ".env" -Raw
    $env_content = $env_content -replace "^YOUTUBE_REFRESH_TOKEN=$", "YOUTUBE_REFRESH_TOKEN=$REFRESH_TOKEN"
    $env_content | Set-Content ".env" -Encoding UTF8
    Write-Host "  -> Saved to .env" -ForegroundColor Green
}
Write-Host ""

# ------------------------------------------------------------------
# STEP 4: Push secrets to GitHub
# ------------------------------------------------------------------
Write-Host "[STEP 4/4] PUSH SECRETS TO GITHUB" -ForegroundColor Yellow
Write-Host "---------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Your 4 secrets:" -ForegroundColor White
Write-Host "  1. GOOGLE_AI_API_KEY = $GEMINI_KEY" -ForegroundColor Cyan
Write-Host "  2. YOUTUBE_CLIENT_ID = $CLIENT_ID" -ForegroundColor Cyan
Write-Host "  3. YOUTUBE_CLIENT_SECRET = $CLIENT_SECRET" -ForegroundColor Cyan
Write-Host "  4. YOUTUBE_REFRESH_TOKEN = $REFRESH_TOKEN" -ForegroundColor Cyan
Write-Host ""
Write-Host "Adding to GitHub..." -ForegroundColor White

# Use GitHub API if gh CLI available
$ghPath = Get-Command gh -ErrorAction SilentlyContinue
if ($ghPath) {
    Write-Host "Using gh CLI..." -ForegroundColor Green
    echo $GEMINI_KEY | gh secret set GOOGLE_AI_API_KEY --repo rahuljain2519/HORRORSTORY
    echo $CLIENT_ID | gh secret set YOUTUBE_CLIENT_ID --repo rahuljain2519/HORRORSTORY
    echo $CLIENT_SECRET | gh secret set YOUTUBE_CLIENT_SECRET --repo rahuljain2519/HORRORSTORY
    echo $REFRESH_TOKEN | gh secret set YOUTUBE_REFRESH_TOKEN --repo rahuljain2519/HORRORSTORY
    echo "private" | gh variable set YOUTUBE_PRIVACY --repo rahuljain2519/HORRORSTORY
    Write-Host "All secrets pushed to GitHub!" -ForegroundColor Green
} else {
    Write-Host "gh CLI not found. Opening GitHub repo secrets page..." -ForegroundColor Yellow
    Write-Host "Add these manually:" -ForegroundColor White
    Start-Process "https://github.com/rahuljain2519/HORRORSTORY/settings/secrets/actions"
    Write-Host ""
    Write-Host "  For each NEW REPOSITORY SECRET:" -ForegroundColor Cyan
    Write-Host "    Name: GOOGLE_AI_API_KEY   Value: $GEMINI_KEY" -ForegroundColor White
    Write-Host "    Name: YOUTUBE_CLIENT_ID    Value: $CLIENT_ID" -ForegroundColor White
    Write-Host "    Name: YOUTUBE_CLIENT_SECRET Value: $CLIENT_SECRET" -ForegroundColor White
    Write-Host "    Name: YOUTUBE_REFRESH_TOKEN Value: $REFRESH_TOKEN" -ForegroundColor White
    Write-Host ""
    Write-Host "  Also add a REPOSITORY VARIABLE:" -ForegroundColor Cyan
    Write-Host "    Name: YOUTUBE_PRIVACY  Value: private" -ForegroundColor White
    Write-Host ""
    Write-Host "  Press any key after adding secrets..." -ForegroundColor White
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "   ALL SECRETS CONFIGURED!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT: Run the first pipeline!" -ForegroundColor White
Write-Host "  -> GitHub: Actions tab -> 'Daily Horror Story Pipeline' -> Run workflow" -ForegroundColor Cyan
Write-Host "  -> Local:  python src\pipeline.py" -ForegroundColor Cyan
Write-Host ""