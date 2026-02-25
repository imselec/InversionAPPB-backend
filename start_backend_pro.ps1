# Backend PRO Windows Stable

$venvName = "venv_pro"

if (!(Test-Path ".\$venvName")) {
    python -m venv $venvName
    Write-Host "Entorno virtual creado."
}

.\$venvName\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install uvicorn fastapi watchdog

if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
}

Write-Host "Iniciando supervisor backend..."
python backend_supervisor.py
