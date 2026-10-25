#!/usr/bin/env python3
"""
Encadena una corrida de entrenamiento a otra SIN cortar la que está corriendo (DVF, 2026-10-17).

Espera a que termine el proceso supervisor indicado (--esperar-pid) y entonces lanza un
supervisor nuevo con los argumentos que vienen después de "--", oculto y con la salida
redirigida a models/runs/_salidas/<run>_parte<N>_*.txt. Como train_dl.py sigue la corrida
desde run.json y los .npz, la segunda parte continúa justo donde terminó la primera.

Uso (caso real: noche1 terminaba a las 07:15 y se extendió a las 10:30):

    python scripts/encadenar_corrida.py --esperar-pid 12736 -- --run noche1 --until 2026-10-18T10:30 --phase-steps 1500000
"""
import argparse
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _vivo(pid):
	"""¿Sigue vivo el supervisor? Se mira también la línea de comando para no confundirse si
	Windows reusara el mismo PID para otro proceso."""
	ps = (f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\"; "
	      "if ($p -and $p.CommandLine -like '*supervisar_entrenamiento*') { 'SI' } else { 'NO' }")
	out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
	return out.stdout.strip() == "SI"


def main():
	if "--" not in sys.argv:
		raise SystemExit("Uso: encadenar_corrida.py --esperar-pid PID -- <argumentos del supervisor>")
	cut = sys.argv.index("--")
	ap = argparse.ArgumentParser()
	ap.add_argument("--esperar-pid", type=int, required=True)
	args = ap.parse_args(sys.argv[1:cut])
	sup_args = sys.argv[cut + 1:]
	run = sup_args[sup_args.index("--run") + 1]
	salidas = ROOT / "models" / "runs" / "_salidas"
	salidas.mkdir(parents=True, exist_ok=True)
	log = ROOT / "models" / "runs" / run / "supervisor.log"

	def _log(text):
		with open(log, "a", encoding="utf-8") as f:
			f.write(f"{dt.datetime.now():%Y-%m-%dT%H:%M:%S} [encadenador] {text}\n")

	_log(f"esperando a que termine el supervisor PID {args.esperar_pid}; después: {' '.join(sup_args)}")
	while _vivo(args.esperar_pid):
		time.sleep(20)
	time.sleep(5)
	parte = 2
	while (salidas / f"{run}_parte{parte}_stdout.txt").exists():
		parte += 1
	out = open(salidas / f"{run}_parte{parte}_stdout.txt", "w")
	err = open(salidas / f"{run}_parte{parte}_stderr.txt", "w")
	p = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "supervisar_entrenamiento.py"), *sup_args],
	                     cwd=ROOT, stdout=out, stderr=err,
	                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
	(salidas / f"{run}_supervisor_pid.txt").write_text(str(p.pid), encoding="utf-8")
	_log(f"supervisor anterior terminado; lanzado supervisor nuevo (parte {parte}, PID {p.pid})")


if __name__ == "__main__":
	main()
