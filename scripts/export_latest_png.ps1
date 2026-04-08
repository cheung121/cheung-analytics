param(
  [string]$BrowserPath = ""
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$IndexPath = Join-Path $Root "site\generated\index.json"

if (-not (Test-Path $IndexPath)) {
  throw "No generated index found. Run: py scripts\generate_draft.py --season 2026"
}

if (-not $BrowserPath) {
  $Candidates = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
  )
  $BrowserPath = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $BrowserPath -or -not (Test-Path $BrowserPath)) {
  throw "Could not find Edge or Chrome. Install optional Python dependency instead: pip install -r requirements.txt"
}

$Index = Get-Content $IndexPath -Raw | ConvertFrom-Json
$SvgPath = Join-Path (Join-Path $Root "site") $Index.latest.graphic
$SvgPath = Resolve-Path $SvgPath
$PngPath = [System.IO.Path]::ChangeExtension($SvgPath.Path, ".png")
$UserDataDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cheung-analytics-headless-" + [guid]::NewGuid().ToString())
$SvgUri = (New-Object System.Uri($SvgPath.Path)).AbsoluteUri

New-Item -ItemType Directory -Force -Path $UserDataDir | Out-Null

$Args = @(
  "--headless=new",
  "--disable-gpu",
  "--hide-scrollbars",
  "--user-data-dir=$UserDataDir",
  "--screenshot=$PngPath",
  "--window-size=1600,900",
  $SvgUri
)

try {
  & $BrowserPath @Args | Out-Null
} finally {
  if (Test-Path $UserDataDir) {
    Remove-Item -LiteralPath $UserDataDir -Recurse -Force -ErrorAction SilentlyContinue
  }
}

if (-not (Test-Path $PngPath)) {
  throw "Browser export failed. Expected PNG was not created: $PngPath"
}

Write-Host "Exported PNG: $PngPath"
