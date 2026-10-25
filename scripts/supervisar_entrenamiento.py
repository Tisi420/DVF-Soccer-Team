#!/usr/bin/env python3
"""
Supervisor del entrenamiento DL (equipo DVF, 2026-10-17).

Motivo: en noche1 el proceso principal de scripts/train_dl.py murió a las 20:52 por un crash
NATIVO de Windows (python.exe, "access violation" 0xc0000005, sin traza de Python). Un error
así no lo puede atajar el propio proceso, así que este supervisor lo relanza:

  * corre scripts/train_dl.py con los argumentos dados (deben incluir --run y --until);
  * si termina con código 0 (llegó a la hora límite) o pasó la hora límite, termina;
  * si se cae, mata los workers que hayan quedado huérfanos, espera unos segundos y lo
    relanza: train_dl.py continúa la corrida desde el último guardado (resume de los .npz,
    que ahora se guardan de forma atómica) y run.json sigue acumulando fases;
  * deja registro de cada caída en models/runs/<run>/supervisor.log.

Uso (desde la raíz; con la salida redirigida, ver la cabecera de scripts/train_dl.py):

    python scripts/supervisar_entrenamiento.py --run noche1 --until 2026-10-18T07:00 --phase-steps 1500000
"""
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_REINICIOS = 30          # tope por si algo falla en cada arranque
ESPERA_S = 15               # pausa antes de relanzar


def _arg(args, name):
	return args[args.index(name) + 1] if name in args else None


def _log(path, text):
	line = f"{dt.datetime.now():%Y-%m-%dT%H:%M:%S} {text}"
	print(line, flush=True)
	with open(path, "a", encoding="utf-8") as f:
		f.write(line + "\n")


def _matar_huerfanos(run):
	"""Mata los workers de multiprocessing que dejó el train_dl.py caído de ESTA corrida.

	2026-10-18 (sesión 37): antes se mataban todos los workers del proyecto creados desde el inicio
	del intento, lo que con dos corridas en paralelo mataba también los de la otra. Ahora train_dl
	escribe su PID en models/runs/<run>/train_pid.txt y cada worker lleva "parent_pid=<ese PID>" en
	su línea de comando (multiprocessing spawn), así que se filtra por eso.
	"""
	pid_file = ROOT / "models" / "runs" / run / "train_pid.txt"
	if not pid_file.exists():
		return 0
	pid = pid_file.read_text(encoding="ascii").strip()
	ps = (
		"Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
		f"Where-Object {{ $_.CommandLine -like '*spawn_main(parent_pid={pid},*' }} | "
		"ForEach-Object { Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }"
	)
	out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
	return len([l for l in out.stdout.splitlines() if l.strip()])


def main():
	args = sys.argv[1:]
	run, until = _arg(args, "--run"), _arg(args, "--until")
	if not run or not until:
		raise SystemExit("Uso: supervisar_entrenamiento.py --run <nombre> --until <ISO> [otros args de train_dl.py]")
	limite = dt.datetime.fromisoformat(until)
	sup_log = ROOT / "models" / "runs" / run / "supervisor.log"
	sup_log.parent.mkdir(parents=True, exist_ok=True)
	_log(sup_log, f"=== supervisor: run={run} hasta {until} | args: {' '.join(args)} ===")
	until_file = ROOT / "models" / "runs" / run / "until.txt"
	for intento in range(1, MAX_REINICIOS + 1):
		# 2026-10-17: until.txt (si existe) manda sobre --until, igual que en train_dl.py
		if until_file.exists() and until_file.read_text(encoding="utf-8").strip():
			limite = dt.datetime.fromisoformat(until_file.read_text(encoding="utf-8").strip())
		if dt.datetime.now() >= limite:
			_log(sup_log, "hora límite alcanzada: fin")
			return
		_log(sup_log, f"intento {intento}: lanzando train_dl.py")
		rc = subprocess.run([sys.executable, str(ROOT / "scripts" / "train_dl.py"), *args], cwd=ROOT).returncode
		if rc == 0:
			_log(sup_log, "train_dl.py terminó bien (código 0): fin")
			return
		n = _matar_huerfanos(run)
		_log(sup_log, f"!!! train_dl.py se cayó (código {rc} = 0x{rc & 0xFFFFFFFF:08X}); "
		              f"workers huérfanos eliminados: {n}; relanzo en {ESPERA_S} s")
		time.sleep(ESPERA_S)
	_log(sup_log, f"!!! {MAX_REINICIOS} caídas: el supervisor se rinde")


if __name__ == "__main__":
	main()
