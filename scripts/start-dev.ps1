$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if(-not (Test-Path '.env')){throw 'Create .env using .env.example.'}
if(-not (Test-Path '.venv/Scripts/python.exe')){throw 'Create the Python 3.12 venv and install backend/requirements.txt first.'}
New-Item -ItemType Directory -Path '.runtime' -Force | Out-Null
if(-not (Get-NetTCPConnection -LocalPort 55432 -State Listen -ErrorAction SilentlyContinue) -and (Test-Path '.runtime/pgdata/PG_VERSION')){
 $pg=Start-Process -FilePath (Resolve-Path '.runtime/pgsql/bin/pg_ctl.exe') -ArgumentList '-D',('"'+(Join-Path $PWD '.runtime/pgdata')+'"'),'-l',('"'+(Join-Path $PWD '.runtime/postgres.log')+'"'),'-o','"-p 55432 -h 127.0.0.1"','-w','start' -WindowStyle Hidden -Wait -PassThru
 if($pg.ExitCode -ne 0){throw 'PostgreSQL startup failed.'}
}
if(-not (Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue)){
 Start-Process -FilePath (Resolve-Path '.venv/Scripts/python.exe') -ArgumentList '-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port','8001' -WindowStyle Hidden -RedirectStandardOutput '.runtime/api.log' -RedirectStandardError '.runtime/api-error.log' | Out-Null
}
if(-not (Get-NetTCPConnection -LocalPort 5622 -State Listen -ErrorAction SilentlyContinue)){
 Start-Process -FilePath (Get-Command node).Source -ArgumentList 'node_modules/vite/bin/vite.js' -WorkingDirectory (Join-Path $PWD 'frontend') -WindowStyle Hidden -RedirectStandardOutput '.runtime/frontend.log' -RedirectStandardError '.runtime/frontend-error.log' | Out-Null
}
Write-Host 'Development preview: http://127.0.0.1:5622/ . Check /api/health to confirm readiness.'
