# Lanza la corrida 2 del DL bajo el supervisor, oculta y con la salida redirigida (DVF, sesión 20).
#
#   - Arranca desde los modelos finales de noche1 (--init-from copia striker.npz/keeper.npz solo si
#     corrida2 todavía no los tiene: relanzar este script continúa la corrida, no la reinicia).
#   - Recompensa v3 (dvf_rewards.REWARD_VERSION): castigo por gol recibido + defensa del saque.
#   - Striker Y keeper contra NormalTeam, v1 y v2.3 (los rivales por defecto de train_dl.py): en
#     noche1 el striker entrenado solo contra NormalTeam le ganaba +84 por partido a NormalTeam
#     pero perdía −18 con v1 y −32 con v2.3.
#   - Entropía del keeper 0.02 hasta la sesión 29 (ahora 0.01). La del striker empezó en 0.02 (para que vuelva a explorar contra
#     rivales nuevos) y desde la sesión 25 es 0.01 (ver abajo).
#   - Hasta el lunes 07:00 (se puede mover sin cortar con models/runs/corrida2/until.txt).
#
#   - Sesión 22 (tras el apagado brusco del 18/10 ~12:55): -Workers (default 8 de 16 núcleos) y
#     prioridad "BelowNormal" para que la PC siga usable mientras entrena (los workers de
#     multiprocessing heredan la prioridad baja). Menos carga = menos temperatura.
#   - Sesión 25: -StrikerEntropy (default 0.01). Con 0.02 la red del striker volvió casi al azar
#     (entropía 3,13 de 3,30; ver sonda_recompensa.py); con 0.01 la de noche1 sí aprendió.
#   - Sesión 29: -KeeperEntropy (default 0.01). En el saque la red del keeper decidía al azar
#     (entropía ~3,14) aunque volver al arco paga ~80 puntos más (sonda_keeper_recompensa.py).
#   - Sesión 30: -Opponents con PESOS. train_dl reparte la lista por turno entre los workers
#     (worker i -> lista[i % largo]), así que los repetidos pesan más. Con NT/v1/v2.3 parejos y 8
#     workers quedaban 3/3/2 y el equipo se sobreajustó a NormalTeam (+6 contra NT, −91 contra v2.3).
#     Default: v2.3 x4, v1 x2, NormalTeam x2.
#   - No lanza si el reloj de Windows está desfasado más de 5 min (tras un corte de luz el reloj
#     quedó 13 h atrás): un salto de hora a mitad de fase arruinaría las horas de run.json.
#
# Uso (desde la raíz del proyecto):  powershell -ExecutionPolicy Bypass -File scripts\lanzar_corrida2.ps1 [-Workers 8] [-StrikerEntropy 0.01] [-KeeperEntropy 0.01]
# Ver cómo va:  Get-Content models\runs\corrida2\training.log -Tail 20 -Wait

param([int]$Workers = 8, [string]$StrikerEntropy = "0.01", [string]$KeeperEntropy = "0.01",
	[string[]]$Opponents = @("DVF_v2", "DVF", "DVF_v2", "NormalTeam", "DVF_v2", "DVF", "DVF_v2", "NormalTeam"))
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$hasta = "2026-10-19T07:00"
$salidas = "models\runs\_salidas"
New-Item -ItemType Directory -Force $salidas | Out-Null

$vivos = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
	Where-Object { $_.CommandLine -like '*praktikum-soccer*' -and $_.CommandLine -like '*train_dl*' }
if ($vivos) { throw "Ya hay un train_dl.py corriendo (PID $($vivos.ProcessId -join ', ')). No lanzo otro." }

# Reloj: compara con time.windows.com (si no hay internet, sigue con un aviso).
$sync = w32tm /stripchart /computer:time.windows.com /samples:1 /dataonly 2>&1 | Select-String '([+-][\d.]+)s$'
if ($sync) {
	$off = [double]$sync.Matches[0].Groups[1].Value
	if ([math]::Abs($off) -gt 300) {
		throw "El reloj de Windows está desfasado $([math]::Round($off / 3600, 2)) h. Sincronizalo (Configuración > Hora e idioma > Fecha y hora > Sincronizar ahora) y volvé a lanzar."
	}
} else { Write-Warning "No pude comparar el reloj con internet; sigo igual." }

$n = 1
while (Test-Path "$salidas\corrida2_parte$($n)_stdout.txt") { $n++ }
$py = (Resolve-Path "env\Scripts\python.exe").Path
$p = Start-Process -FilePath $py -WorkingDirectory $root -WindowStyle Hidden -PassThru `
	-RedirectStandardOutput "$salidas\corrida2_parte$($n)_stdout.txt" `
	-RedirectStandardError "$salidas\corrida2_parte$($n)_stderr.txt" `
	-ArgumentList (@('scripts\supervisar_entrenamiento.py', '--run', 'corrida2', '--until', $hasta,
		'--init-from', 'models\runs\noche1', '--phase-steps', '1500000', '--opponents') + $Opponents +
		@('--workers', "$Workers", '--striker-entropy', $StrikerEntropy, '--keeper-entropy', $KeeperEntropy))
$p.PriorityClass = 'BelowNormal'      # train_dl y sus workers la heredan
Set-Content "$salidas\corrida2_supervisor_pid.txt" $p.Id -Encoding ascii
"corrida2 lanzada (parte $n), supervisor PID $($p.Id), $Workers workers, entropía striker $StrikerEntropy / keeper $KeeperEntropy, rivales $($Opponents -join ','), prioridad baja, hasta $hasta"
