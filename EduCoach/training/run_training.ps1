$ErrorActionPreference = "Stop"

Write-Host "EduCoach QLoRA egitimi baslatiliyor..." -ForegroundColor Cyan

Set-Location $PSScriptRoot

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$venvActivate = ".\.venv-training\Scripts\Activate.ps1"

if (-not (Test-Path $venvActivate)) {
    Write-Host ""
    Write-Host "HATA: .venv-training bulunamadi." -ForegroundColor Red
    Write-Host "Once su dosyayi calistir:"
    Write-Host ".\training\setup_training_env.ps1"
    exit 1
}

Write-Host "Sanal ortam aktif ediliyor..."
& $venvActivate

Write-Host ""
Write-Host "GPU kontrol ediliyor..."

python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'YOK')"

if ($LASTEXITCODE -ne 0) {
    Write-Host "GPU kontrolu basarisiz." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Egitim basliyor..." -ForegroundColor Green
Write-Host ""

python ".\training\scripts\train_qwen3_4b_qlora.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "EGITIM HATA ILE DURDU." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "EGITIM TAMAMLANDI." -ForegroundColor Green
Write-Host "Ciktilari training\outputs klasorunde kontrol et."