# ============================================
# Script PowerShell – Limpieza y redeploy
# Para backend InversionAPPB
# ============================================

# 1️⃣ Detener cualquier proceso Python que esté corriendo
Write-Host "Deteniendo procesos python.exe..."
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# 2️⃣ Activar entorno virtual (opcional si usas venv)
# .\venv\Scripts\Activate.ps1

# 3️⃣ Eliminar archivos de base de datos locales
Write-Host "Eliminando .db locales..."
$DBfiles = @("app.db", "inversionapp.db", "investor.db")
foreach ($file in $DBfiles) {
    if (Test-Path $file) {
        Remove-Item $file -Force
        Write-Host "$file eliminado."
    }
}

# 4️⃣ Limpiar y actualizar git
Write-Host "Preparando commit final..."
git add .gitignore app/database.py app/main.py requirements.txt
git commit --amend --no-edit

# 5️⃣ Push forzado a GitHub
Write-Host "Push forzado a origin/main..."
git push --force-with-lease origin main

# 6️⃣ Local test de uvicorn (opcional)
Write-Host "Arrancando uvicorn localmente en 127.0.0.1:8080..."
Start-Process "python" "-m uvicorn app.main:app --reload --host 127.0.0.1 --port 8080"

Write-Host "✅ Flujo completado. Ahora haz redeploy en Render si no se hace automáticamente."