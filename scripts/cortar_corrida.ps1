# Corta UNA corrida justo después de un guardado, sin tocar las demás (DVF, sesión 37).
#
#   1. frena su evaluador automático (si tiene uno), para que no arranque al morir el supervisor;
#   2. espera a que se vuelva a escribir models/runs/<Run>/keeper.npz (se guardan los dos .npz
#      juntos cada 20 iteraciones), espera 0,8 s más;
#   3. mata su supervisor, su train_dl.py (línea de comando con "--run <Run> ") y SUS workers
#      (los que llevan "parent_pid=<PID de train_pid.txt>").
#
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\cortar_corrida.ps1 -Run corrida2

param([Parameter(Mandatory = $true)][string]$Run, [int]$EsperaMaxMin = 5)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$salidas = "models\runs\_salidas"
$runDir = "models\runs\$Run"

$evFile = "$salidas\$($Run)_evaluador_pid.txt"
if (Test-Path $evFile) { Stop-Process -Id ([int](Get-Content $evFile)) -Force -ErrorAction SilentlyContinue; "evaluador de $Run frenado" }

$f = "$runDir\keeper.npz"
$t0 = (Get-Item $f).LastWriteTime
$lim = (Get-Date).AddMinutes($EsperaMaxMin)
while ((Get-Item $f).LastWriteTime -eq $t0 -and (Get-Date) -lt $lim) { Start-Sleep -Milliseconds 300 }
Start-Sleep -Milliseconds 800

$supFile = "$salidas\$($Run)_supervisor_pid.txt"
if (Test-Path $supFile) { Stop-Process -Id ([int](Get-Content $supFile)) -Force -ErrorAction SilentlyContinue }
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'"
$train = $procs | Where-Object { $_.CommandLine -like '*train_dl*' -and $_.CommandLine -like "*--run $Run *" }
$workers = @()
if (Test-Path "$runDir\train_pid.txt") {
	$tp = (Get-Content "$runDir\train_pid.txt").Trim()
	$workers = $procs | Where-Object { $_.CommandLine -like "*spawn_main(parent_pid=$tp,*" }
}
($train + $workers) | Where-Object { $_ } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
"$Run cortada: guardado $((Get-Item $f).LastWriteTime.ToString('HH:mm:ss')), corte $(Get-Date -Format 'HH:mm:ss'), $(@($train).Count) train_dl + $(@($workers).Count) workers"
