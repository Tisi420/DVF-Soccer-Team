# Lanza UNA corrida del DL bajo el supervisor, oculta y con la salida redirigida (DVF, sesión 37).
# Es la versión genérica de lanzar_corrida2.ps1 (que queda como registro): sirve para correr varias
# corridas en paralelo, cada una con sus workers.
#
#   -Run       nombre de la corrida (models/runs/<Run>/)
#   -InitFrom  carpeta con striker.npz/keeper.npz para arrancar si la corrida todavía no los tiene
#              (si ya los tiene, la corrida CONTINÚA desde los suyos)
#   -Workers   simulaciones en paralelo (default 4)
#   -StrikerEntropy / -KeeperEntropy   exploración (default 0.01 / 0.01)
#   -Opponents rivales con PESOS: train_dl reparte la lista por turno entre los workers
#              (worker i -> lista[i % largo]); default v2.3 x2, v1 x1, NormalTeam x1 por cada 4.
#   -Hasta     hora límite (default lunes 07:00)
#
# Prioridad baja (los workers la heredan) y no lanza si el reloj de Windows está desfasado más de
# 5 min ni si esta corrida ya está corriendo. Las demás corridas no se tocan.
#
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\lanzar_corrida.ps1 -Run corrida3 -InitFrom models\runs\corrida2\respaldo_antes_clon -Workers 4
# Lanzarlo en segundo plano (si no, la terminal queda esperando: el supervisor hereda la salida).

param([Parameter(Mandatory = $true)][string]$Run,
	[string]$InitFrom = "models\runs\noche1",
	[int]$Workers = 4, [string]$StrikerEntropy = "0.01", [string]$KeeperEntropy = "0.01",
	[string[]]$Opponents = @("DVF_v2", "DVF", "DVF_v2", "NormalTeam", "DVF_v2", "DVF", "DVF_v2", "NormalTeam"),
	[string]$Hasta = "2026-10-19T07:00",
	# Sesión 59: tasa de aprendizaje de PPO (vacío = la de train_dl, 3e-4).
	[string]$Lr = "",
	# Sesión 50: -Desacoplado crea el supervisor por WMI (Win32_Process.Create), FUERA del árbol de
	# procesos de quien lo lanza. La noche del 19/10 a las 05:12 murieron a la vez entrenamiento,
	# supervisor, monitor y evaluadores sin apagón: lo más probable es que se cerró la app que los
	# había lanzado y se llevó a sus procesos hijos. Desacoplado, eso no los toca.
	[switch]$Desacoplado)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$salidas = "models\runs\_salidas"
New-Item -ItemType Directory -Force $salidas | Out-Null

$vivos = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
	Where-Object { $_.CommandLine -like '*praktikum-soccer*' -and $_.CommandLine -like '*train_dl*' -and $_.CommandLine -like "*--run $Run *" }
if ($vivos) { throw "La corrida $Run ya está corriendo (PID $($vivos.ProcessId -join ', ')). No lanzo otra." }

# Reloj: compara con time.windows.com (si no hay internet, sigue con un aviso).
$sync = w32tm /stripchart /computer:time.windows.com /samples:1 /dataonly 2>&1 | Select-String '([+-][\d.]+)s$'
if ($sync) {
	$off = [double]$sync.Matches[0].Groups[1].Value
	if ([math]::Abs($off) -gt 300) {
		throw "El reloj de Windows está desfasado $([math]::Round($off / 3600, 2)) h. Sincronizalo y volvé a lanzar."
	}
} else { Write-Warning "No pude comparar el reloj con internet; sigo igual." }

$n = 1
while (Test-Path "$salidas\$($Run)_parte$($n)_stdout.txt") { $n++ }
$py = (Resolve-Path "env\Scripts\python.exe").Path
if ($Desacoplado) {
	$argv = @('scripts\supervisar_entrenamiento.py', '--run', $Run, '--until', $Hasta, '--init-from', $InitFrom,
		'--phase-steps', '1500000', '--opponents') + $Opponents +
		@('--workers', "$Workers", '--striker-entropy', $StrikerEntropy, '--keeper-entropy', $KeeperEntropy) +
		$(if ($Lr) { @('--lr', $Lr) } else { @() })
	$out = (Join-Path $root "$salidas\$($Run)_parte$($n)_stdout.txt"); $err = (Join-Path $root "$salidas\$($Run)_parte$($n)_stderr.txt")
	$cmdLine = "cmd.exe /c `"`"$py`" $($argv -join ' ') > `"$out`" 2> `"$err`"`""
	# PriorityClass 16384 = BelowNormal (cmd, el supervisor y los workers la heredan); ShowWindow 0 = oculto
	$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384; ShowWindow = [uint16]0 }
	$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmdLine; CurrentDirectory = $root; ProcessStartupInformation = $si }
	if ($r.ReturnValue -ne 0) { throw "Win32_Process.Create falló (código $($r.ReturnValue))" }
	$sup = $null
	for ($i = 0; $i -lt 20 -and -not $sup; $i++) {
		Start-Sleep -Milliseconds 500
		$sup = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
			Where-Object { $_.CommandLine -like '*supervisar_entrenamiento*' -and $_.CommandLine -like "*--run $Run *" } |
			Select-Object -First 1
	}
	if (-not $sup) { throw "No encontré el supervisor de $Run después de lanzarlo." }
	Set-Content "$salidas\$($Run)_supervisor_pid.txt" $sup.ProcessId -Encoding ascii
	"$Run lanzada DESACOPLADA (parte $n), supervisor PID $($sup.ProcessId), $Workers workers, entropía $StrikerEntropy / $KeeperEntropy, desde $InitFrom, hasta $Hasta"
	return
}
$p = Start-Process -FilePath $py -WorkingDirectory $root -WindowStyle Hidden -PassThru `
	-RedirectStandardOutput "$salidas\$($Run)_parte$($n)_stdout.txt" `
	-RedirectStandardError "$salidas\$($Run)_parte$($n)_stderr.txt" `
	-ArgumentList (@('scripts\supervisar_entrenamiento.py', '--run', $Run, '--until', $Hasta,
		'--init-from', $InitFrom, '--phase-steps', '1500000', '--opponents') + $Opponents +
		@('--workers', "$Workers", '--striker-entropy', $StrikerEntropy, '--keeper-entropy', $KeeperEntropy) +
		$(if ($Lr) { @('--lr', $Lr) } else { @() }))
$p.PriorityClass = 'BelowNormal'      # train_dl y sus workers la heredan
Set-Content "$salidas\$($Run)_supervisor_pid.txt" $p.Id -Encoding ascii
"$Run lanzada (parte $n), supervisor PID $($p.Id), $Workers workers, entropía $StrikerEntropy / $KeeperEntropy, desde $InitFrom, hasta $Hasta"
