#!/usr/bin/env python3
"""
Monitor nocturno de una corrida (DVF, sesión 47): cada N minutos guarda el estado en un archivo,
para leerlo a la mañana sin que nadie haya estado mirando.

En cada chequeo agrega a models/runs/<run>/monitoreo.md:
  - las fases nuevas de run.json (rol, entropía de la política, goles a favor/en contra por
    actualización y % a favor);
  - una evaluación en partidos del modelo actual con scripts/benchmark.py (soccer_team_DVF_DL con
    DVF_DL_RUN=<run>, contra NormalTeam, v1 y v2.3, ambos lados, ruido 3, corrección violeta):
    neto por par de partidos y G-E-P;
  - una copia del par striker/keeper evaluado en models/runs/<run>/monitoreo/<hora>_*.npz, para
    poder elegirlo después aunque el entrenamiento siga.
Termina solo cuando muere el supervisor indicado.

    python scripts/monitorear.py --run corrida3 --esperar-pid 25248 --cada-min 60 --seeds 8 --workers 3
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
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


def _evaluar(striker, keeper, seeds, workers, duracion, oro):
	# PYTHONIOENCODING + encoding="utf-8": por un pipe en Windows el "±" del resumen llegaba roto
	# (cp1252) y la expresión regular no encontraba las filas.
	# Sesión 59: se evalúa el PAR FIJO copiado en este chequeo (DVF_DL_STRIKER/KEEPER). Con
	# DVF_DL_RUN cada partido cargaba los .npz al arrancar y mezclaba guardados de varios minutos.
	env = dict(os.environ, DVF_DL_STRIKER=str(striker), DVF_DL_KEEPER=str(keeper), PYTHONIOENCODING="utf-8")
	env.pop("DVF_DL_RUN", None)
	cmd = [sys.executable, str(ROOT / "scripts" / "benchmark.py"), "soccer_team_DVF_DL", "--vs", *RIVALES,
	       "--seeds", str(seeds), "--jitter", "3", "--workers", str(workers), "--duration", str(duracion)]
	if oro:
		cmd.append("--gol-de-oro")
	out = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
	                     errors="replace").stdout
	filas = {}
	for line in out.splitlines():
		m = re.match(r"(soccer_team_\w+)\s+\d+\+\d+\s+\|.*\|\s+([+-][\d.]+)\s+±\s+([\d.]+)\s+\|\s+(\d+-\d+-\d+)", line)
		if m:
			filas[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
	return filas


def _espaldas(striker, keeper):
	"""Sesión 59: % del tiempo en movimiento que el striker va de espaldas / de frente."""
	try:
		sys.path.insert(0, str(ROOT / "scripts" / "sondas"))
		import sonda_espaldas as SE
		c, _, _, _, _ = SE.medir("monitor", "soccer_team_DVF_DL.py",
		                         {"DVF_DL_STRIKER": str(striker), "DVF_DL_KEEPER": str(keeper)},
		                         "soccer_team_DVF_v2", 1, seg=120)
		mov = max(1, sum(c.values()))
		return 100 * c["espaldas"] / mov, 100 * c["adelante"] / mov
	except Exception:
		return None


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--run", required=True)
	ap.add_argument("--esperar-pid", type=int, required=True)
	ap.add_argument("--cada-min", type=float, default=60)
	ap.add_argument("--seeds", type=int, default=8)
	ap.add_argument("--workers", type=int, default=3)
	# Sesión 59: formato torneo (partidos de 1 min con gol de oro)
	ap.add_argument("--duracion", type=float, default=300, help="segundos por partido (torneo: 60)")
	ap.add_argument("--gol-de-oro", action="store_true")
	args = ap.parse_args()
	run_dir = ROOT / "models" / "runs" / args.run
	md = run_dir / "monitoreo.md"
	copias = run_dir / "monitoreo"
	copias.mkdir(exist_ok=True)
	if not md.exists():
		md.write_text(f"# Monitoreo de {args.run}\n\nNeto por par de partidos (uno de cada lado), "
		              f"{args.seeds} semillas por lado, partidos de {args.duracion:.0f} s"
		              f"{' con gol de oro' if args.gol_de_oro else ''}, ruido 3, corrección violeta. "
		              "Criterio = promedio contra v1 y v2.3.\n", encoding="utf-8")
	vistas = 0
	while True:
		time.sleep(args.cada_min * 60)
		if not _vivo(args.esperar_pid):
			with open(md, "a", encoding="utf-8") as f:
				f.write(f"\n{dt.datetime.now():%H:%M} — el supervisor terminó: fin del monitoreo.\n")
			return
		hora = dt.datetime.now()
		meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
		fases = meta.get("phases", [])
		nuevas = fases[vistas:] if vistas else fases[-4:]
		vistas = len(fases)
		tag = f"{hora:%H%M}"
		for rol in ("striker", "keeper"):           # copia del par que se evalúa
			shutil.copy2(run_dir / f"{rol}.npz", copias / f"{tag}_{rol}.npz")
		ev = _evaluar(copias / f"{tag}_striker.npz", copias / f"{tag}_keeper.npz", args.seeds, args.workers,
		              args.duracion, args.gol_de_oro)
		esp = _espaldas(copias / f"{tag}_striker.npz", copias / f"{tag}_keeper.npz")
		lines = [f"\n## {hora:%Y-%m-%d %H:%M} · {meta.get('total_hours', 0):.2f} h, {len(fases)} fases",
		         "", "| ciclo | rol | exploración | entropía | a favor/act. | en contra/act. | % a favor |",
		         "|---|---|---|---|---|---|---|"]
		for p in nuevas:
			s = p.get("stats", {})
			gf, gc = s.get("gf_per_upd", 0), s.get("gc_per_upd", 0)
			pct = 100 * gf / (gf + gc) if gf + gc else 0
			lines.append(f"| {p['cycle']} | {p['role']} | {p.get('entropy_coef', '')} | {s.get('ent_mean', '')} | "
			             f"{gf} | {gc} | {pct:.0f} % |")
		if ev:
			lines += ["", "| rival | neto | ± | G-E-P |", "|---|---|---|---|"]
			for r in RIVALES:
				if r in ev:
					lines.append(f"| {r.replace('soccer_team_', '')} | {ev[r][0]:+.1f} | {ev[r][1]:.1f} | {ev[r][2]} |")
			if "soccer_team_DVF" in ev and "soccer_team_DVF_v2" in ev:
				crit = (ev["soccer_team_DVF"][0] + ev["soccer_team_DVF_v2"][0]) / 2
				lines.append(f"\n**Criterio: {crit:+.1f}** · par guardado en `monitoreo/{tag}_striker.npz` + `_keeper.npz`")
		else:
			lines.append("\n(la evaluación no devolvió resultados)")
		if esp is not None:
			lines.append(f"\nStriker en movimiento: **{esp[0]:.0f} % de espaldas**, {esp[1]:.0f} % de frente "
			             "(1 partido de 120 s contra v2.3).")
		with open(md, "a", encoding="utf-8") as f:
			f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
	main()
