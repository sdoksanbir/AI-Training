$ErrorActionPreference = "Stop"

Write-Host "EduCoach training ortami kuruluyor..." -ForegroundColor Cyan

Set-Location $PSScriptRoot

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".venv-training")) {
    Write-Host "Sanal ortam olusturuluyor..."
    python -m venv .venv-training
}

Write-Host "Sanal ortam aktif ediliyor..."
& ".\.venv-training\Scripts\Activate.ps1"

Write-Host "pip guncelleniyor..."
python -m pip install --upgrade pip

Write-Host "Egitim paketleri kuruluyor..."
pip install -r ".\training\requirements-training.txt"

Write-Host ""
Write-Host "Kurulum tamamlandi." -ForegroundColor Green
Write-Host "Sanal ortam: .venv-training"