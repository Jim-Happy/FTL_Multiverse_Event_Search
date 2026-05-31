param(
    [switch]$NoClean
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not $NoClean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $projectRoot 'build')
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $projectRoot 'dist')
}

Write-Host 'Building FTLSearch with PyInstaller...' -ForegroundColor Cyan
uv run pyinstaller --noconfirm --clean (Join-Path $projectRoot 'FTLSearch.spec')

Write-Host 'Build complete. Output: dist\FTLSearch.exe' -ForegroundColor Green