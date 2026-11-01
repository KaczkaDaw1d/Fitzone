$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot
$projectPython = Join-Path $projectDir '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Brak środowiska .venv. Wykonaj instalację z README.md.'
}
$env:DJANGO_DEBUG = '1'
Set-Location (Join-Path $projectDir 'backend')
& $projectPython manage.py migrate
if ($LASTEXITCODE -ne 0) { throw 'Migracja nie powiodła się.' }
& $projectPython manage.py seed_demo
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się przygotować przykładowych danych.' }
& $projectPython manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zebrać plików frontendu.' }
Write-Host 'Otwórz http://127.0.0.1:8000 — podgląd lokalny projektu FitZone.'
& $projectPython manage.py runserver 127.0.0.1:8000 --noreload
