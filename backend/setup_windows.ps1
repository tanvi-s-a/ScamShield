$ErrorActionPreference = "Stop"

Write-Host "Checking for Python 3.12..."
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python launcher not found. Install Python 3.12 (64-bit) from python.org, then rerun this script." -ForegroundColor Red
    exit 1
}

try {
    py -3.12 --version
} catch {
    Write-Host "Python 3.12 is not installed. Install Python 3.12 (64-bit), then rerun this script." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".venv")) {
    py -3.12 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe training\run_phase_1_to_3.py

Write-Host ""
Write-Host "Training complete. Start the backend with:" -ForegroundColor Green
Write-Host ".\.venv\Scripts\python.exe -m uvicorn app.main:app --reload"
