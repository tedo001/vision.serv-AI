#!/usr/bin/env bash
# ============================================================================
# Create and provision the GPU virtual environment (venv_gpu) on Linux/macOS.
#   bash scripts/setup_gpu.sh
# Requires Python 3.10-3.12 and an NVIDIA GPU with a recent driver.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d "venv_gpu" ]; then
    echo "Creating venv_gpu ..."
    python -m venv venv_gpu
fi

echo "Installing GPU dependencies ..."
./venv_gpu/bin/python -m pip install --upgrade pip
./venv_gpu/bin/python -m pip install -r requirements-gpu.txt

echo "Verifying CUDA ..."
./venv_gpu/bin/python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

echo ""
echo "Done. Activate with:  source venv_gpu/bin/activate"
