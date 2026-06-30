# ============================================================================
# Create and provision the GPU virtual environment (venv_gpu) on Windows.
#   PowerShell:  .\scripts\setup_gpu.ps1
# Requires Python 3.10-3.12 and an NVIDIA GPU with a recent driver.
# ============================================================================

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "venv_gpu")) {
    Write-Host "Creating venv_gpu ..." -ForegroundColor Cyan
    python -m venv venv_gpu
}

Write-Host "Installing GPU dependencies ..." -ForegroundColor Cyan
& ".\venv_gpu\Scripts\python.exe" -m pip install --upgrade pip
& ".\venv_gpu\Scripts\python.exe" -m pip install -r requirements-gpu.txt

Write-Host "Verifying CUDA ..." -ForegroundColor Cyan
& ".\venv_gpu\Scripts\python.exe" -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

Write-Host "`nDone. Activate with:  .\venv_gpu\Scripts\activate" -ForegroundColor Green
