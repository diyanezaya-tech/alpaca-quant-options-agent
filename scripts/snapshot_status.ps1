# Snapshot de estado de Railway + cuenta PA3SQTOC6A22, para que Claude pueda
# chequear el agente sin acceso directo a Railway desde una sesión cloud.
#
# Uso: desde la carpeta del proyecto, correr:
#   powershell -File scripts\snapshot_status.ps1
#
# Sobrescribe railway_status.log y railway_account_status.json en la raíz
# del proyecto cada vez que se corre. Correlo de nuevo cuando Claude (o vos)
# necesiten un chequeo actualizado.

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$ProjectId     = "1496e6ba-2817-4512-930c-702a3b62a60d"   # stellar-blessing
$ServiceId     = "2f78b72e-3610-4c6a-ae5a-c9b17230ea1e"   # live-agent
$EnvironmentId = "2661c32a-2d3b-4bd3-b60a-42dd774128b9"   # production

Write-Host "Volcando logs de Railway a railway_status.log..."
# Ojo: no redirigir stderr aca (*> o 2>&1) -- en PowerShell 5.1 eso envuelve
# cada linea de stderr de un exe nativo en un ErrorRecord y frena el script
# si $ErrorActionPreference=Stop, aunque railway logs haya salido bien.
railway logs --project $ProjectId --service $ServiceId --environment $EnvironmentId --deployment --lines 150 > railway_status.log

Write-Host "Consultando cuenta y posiciones de PA3SQTOC6A22..."
$acc = Get-Content .env | Where-Object { $_ -match '^ALPACA_API_KEY=' } | ForEach-Object { $_ -replace '^ALPACA_API_KEY=', '' }
$sec = Get-Content .env | Where-Object { $_ -match '^ALPACA_SECRET_KEY=' } | ForEach-Object { $_ -replace '^ALPACA_SECRET_KEY=', '' }
$env:ALPACA_API_KEY = $acc
$env:ALPACA_SECRET_KEY = $sec

$account = & .\tools\alpaca.exe account get | Out-String
$positions = & .\tools\alpaca.exe position list | Out-String

$snapshot = @{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    account      = ($account | ConvertFrom-Json)
    positions    = ($positions | ConvertFrom-Json)
}
$snapshot | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 railway_account_status.json

Write-Host "Listo: railway_status.log y railway_account_status.json actualizados."
