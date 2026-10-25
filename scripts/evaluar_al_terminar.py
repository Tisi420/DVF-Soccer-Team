#!/usr/bin/env python3
"""
Evalúa una corrida sola cuando termina el entrenamiento (DVF, sesión 30).

Espera a que muera el supervisor indicado y entonces, con casi todos los núcleos:
  1. evaluar_corrida.py <run> --puntos N: fines de fase repartidos en toda la corrida + el final;
  2. evaluar_corrida.py <run> --strikers ... --keepers ...: combinaciones pedidas (por ejemplo el
     candidato de las 16:45 = ciclo 12 de corrida2);
  3. analizar_fases.py;
  4. eval/mejor.txt: ranking de todos los puntos por el neto promedio contra v1 y v2.3 (NormalTeam
     se muestra pero no decide: el DL ya encontró trucos que solo sirven contra él).
Todo contra NormalTeam, v1 y v2.3, ambos lados, ruido 3 y con la corrección del violeta
(soccer_team_DVF_DL.py la trae activada por defecto).

    python scripts/evaluar_al_terminar.py --esperar-pid 12345 --run corrida2 --combos-strikers 12 final --combos-keepers 12 final
"""
import argparse
import datetime as dt
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RIVALES = ["soccer_team_NormalTeam", "soccer_team_DVF", "soccer_team_DVF_v2"]


def _vivo(pid):
	ps = (f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\"; "
	      "if ($p -and $p.CommandLine -like '*supervisar_entrenamiento*') { 'SI' } else { 'NO' }")
	out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
	return out.stdout.strip() == "SI"


def _ranking(eval_dir):
	"""Lee resumen.md y resumen_combos.md -> [(neto promedio, punto, netos por rival)]."""
	filas = []
	for nombre in ("resumen.md", "resumen_combos.md"):
		f = eval_dir / nombre
		if not f.exists():
			continue
		for line in f.read_text(encoding="utf-8").splitlines():
			m = re.match(r"\| (\S+) \| [\d.]+ \| (.+) \|$", line)
			if not m:
				continue
			netos = [float(x.split("±")[0]) for x in m.group(2).split(" | ") if "±" in x]
			if len(netos) == len(RIVALES):
				# Criterio: promedio contra v1 y v2.3 (los rivales fuertes). Contra NormalTeam el DL
				# ya encontró trucos que solo le sirven a ese rival (+84 en noche1): no debe decidir.
				filas.append(((netos[1] + netos[2]) / 2, m.group(1), netos))
	return sorted(filas, reverse=True)


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--esperar-pid", type=int, required=True)
	ap.add_argument("--run", default="corrida2")
	ap.add_argument("--puntos", type=int, default=10)
	ap.add_argument("--seeds", type=int, default=4)
	ap.add_argument("--workers", type=int, default=14)
	ap.add_argument("--combos-strikers", nargs="*", default=[])
	ap.add_argument("--combos-keepers", nargs="*", default=[])
	args = ap.parse_args()
	run_dir = ROOT / "models" / "runs" / args.run
	eval_dir = run_dir / "eval"
	eval_dir.mkdir(parents=True, exist_ok=True)
	log = eval_dir / "auto.log"

	def _log(t):
		with open(log, "a", encoding="utf-8") as f:
			f.write(f"{dt.datetime.now():%Y-%m-%dT%H:%M:%S} {t}\n")

	_log(f"esperando a que termine el supervisor PID {args.esperar_pid}")
	while _vivo(args.esperar_pid):
		time.sleep(60)
	time.sleep(30)                                  # que terminen de cerrarse los workers
	_log("supervisor terminado: empiezo la evaluación")
	base = [sys.executable, str(ROOT / "scripts" / "evaluar_corrida.py"), args.run, "--vs", *RIVALES,
	        "--seeds", str(args.seeds), "--jitter", "3", "--workers", str(args.workers)]
	pasos = [base + ["--puntos", str(args.puntos)]]
	if args.combos_strikers and args.combos_keepers:
		pasos.append(base + ["--strikers", *args.combos_strikers, "--keepers", *args.combos_keepers])
	for cmd in pasos:
		r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
		_log(f"{' '.join(cmd[2:4])} ... -> código {r.returncode}")
		with open(log, "a", encoding="utf-8") as f:
			f.write(r.stdout[-3000:] + r.stderr[-1500:] + "\n")
	subprocess.run([sys.executable, str(ROOT / "scripts" / "analizar_fases.py")], cwd=ROOT,
	               capture_output=True, text=True)

	filas = _ranking(eval_dir)
	txt = [f"Ranking de {args.run} ({dt.datetime.now():%Y-%m-%d %H:%M}) por neto promedio por partido contra v1 y v2.3",
	       f"(ruido 3, {args.seeds} semillas por lado, corrección violeta activa). Columnas: criterio | NormalTeam  v1  v2.3.",
	       "Los puntos S<c>_K<c> son combinaciones por ciclo; los demás, fines de fase (etiqueta del checkpoint).", ""]
	for prom, punto, netos in filas:
		txt.append(f"{prom:+7.1f}  {punto:40}  " + "  ".join(f"{n:+6.1f}" for n in netos))
	(eval_dir / "mejor.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
	_log(f"listo: {len(filas)} puntos rankeados en eval/mejor.txt")


if __name__ == "__main__":
	main()
