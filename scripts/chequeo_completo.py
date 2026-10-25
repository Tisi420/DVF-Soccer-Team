#!/usr/bin/env python3
"""
Chequeo completo de una corrida DL (DVF, sesión 60) — todo en un comando y un informe.

  1. Copia FIJA del par striker/keeper del momento → models/runs/<run>/chequeos/<fecha>_*.npz
     (lo que se evalúa es exactamente ese par, aunque el entrenamiento siga guardando).
  2. Curva: todas las fases de run.json (rol, exploración, entropía, goles por actualización, %).
  3. Formato torneo: benchmark de 1 min con gol de oro (--seeds60 por lado) y de 3 min, la final,
     también con gol de oro (--seeds180), contra NormalTeam, v1 y v2.3. Neto, G-E-P y goles.
  4. Carrera de espaldas del striker (sonda_espaldas): contra NormalTeam y v2.3, 2 semillas.
  5. Saques (sonda_saque): quién toca primero, dónde está el keeper, goles de saque.
  6. Informe → models/runs/<run>/chequeos/<fecha>.md, con las referencias del punto de partida.

Conviene lanzarlo con prioridad baja (los procesos hijos la heredan):
    python scripts/chequeo_completo.py --run corrida5 --workers 10
    python scripts/chequeo_completo.py --striker a.npz --keeper b.npz --nombre prueba
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
CORTO = {"soccer_team_NormalTeam": "NormalTeam", "soccer_team_DVF": "v1", "soccer_team_DVF_v2": "v2.3"}
# Referencias de la sesión 59 (1 min + gol de oro, 16 semillas por lado; G-E-P en 32 partidos)
REFERENCIAS = {
	"equipo clonado (inicio de corrida5)": {"NormalTeam": "23-0-9 (+2,1)", "v1": "9-0-23 (−1,1)", "v2.3": "4-3-25 (−2,4)"},
	"DL elegido (entrega/red_DL)": {"NormalTeam": "15-0-17 (−0,1)", "v1": "5-0-27 (−2,1)", "v2.3": "1-0-31 (−2,5)"},
	"rule-based v2.3": {"NormalTeam": "30-0-2 (+2,3)", "v1": "27-0-5 (+1,6)", "v2.3": "13-6-13 (0,0)"},
}
FILA = re.compile(r"(soccer_team_\w+)\s+(\d+)\+(\d+)\s+\|\s+([\d.]+)\s+-\s+([\d.]+)\s+\|\s+([\d.]+)\s+-\s+([\d.]+)\s+\|"
                  r"\s+([+-][\d.]+)\s+±\s+([\d.]+)\s+\|\s+(\d+-\d+-\d+)\s+\|\s+([\d.]+)\s+-\s+([\d.]+)")


def _benchmark(striker, keeper, seeds, duracion, workers):
	env = dict(os.environ, DVF_DL_STRIKER=str(striker), DVF_DL_KEEPER=str(keeper), PYTHONIOENCODING="utf-8")
	env.pop("DVF_DL_RUN", None)
	cmd = [sys.executable, str(ROOT / "scripts" / "benchmark.py"), "soccer_team_DVF_DL", "--vs", *RIVALES,
	       "--seeds", str(seeds), "--jitter", "3", "--workers", str(workers), "--duration", str(duracion),
	       "--gol-de-oro"]
	out = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
	                     errors="replace").stdout
	filas, oro = {}, ""
	for line in out.splitlines():
		m = FILA.match(line)
		if m:
			g = m.groups()
			filas[CORTO.get(g[0], g[0])] = {"izq": f"{g[3]}-{g[4]}", "der": f"{g[5]}-{g[6]}", "neto": float(g[7]),
			                                 "ic": float(g[8]), "gep": g[9], "saque": f"{g[10]}-{g[11]}"}
		if "gol de oro" in line and line.startswith("Partidos"):
			oro = line.strip()
	return filas, oro


def _espaldas(striker, keeper):
	sys.path.insert(0, str(ROOT / "scripts" / "sondas"))
	import sonda_espaldas as SE
	env = {"DVF_DL_STRIKER": str(striker), "DVF_DL_KEEPER": str(keeper)}
	tot = {"adelante": 0, "costado": 0, "espaldas": 0}; hac = dict(tot); q = n = 0
	for rival in ("soccer_team_NormalTeam", "soccer_team_DVF_v2"):
		for seed in (1, 2):
			c, h, quieto, total, _ = SE.medir("chequeo", "soccer_team_DVF_DL.py", env, rival, seed, seg=120)
			for k in tot:
				tot[k] += c[k]; hac[k] += h[k]
			q += quieto; n += total
	for k in ("DVF_DL_STRIKER", "DVF_DL_KEEPER"):
		os.environ.pop(k, None)
	mov = max(1, sum(tot.values()))
	return {k: 100 * v / mov for k, v in tot.items()}, 100 * hac["espaldas"] / max(1, sum(hac.values()))


def _saques(striker, keeper):
	out = []
	for rival in ("soccer_team_DVF_v2", "soccer_team_DVF"):
		r = subprocess.run([sys.executable, str(ROOT / "scripts" / "sondas" / "sonda_saque.py"), str(striker), str(keeper),
		                    rival, "300", "1"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
		                   env=dict(os.environ, PYTHONIOENCODING="utf-8"))
		out += [l for l in r.stdout.splitlines() if l.strip() and not l.startswith(("pygame", "Hello", "Blue:"))]
	return out


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--run")
	ap.add_argument("--striker", type=Path)
	ap.add_argument("--keeper", type=Path)
	ap.add_argument("--nombre", default="")
	ap.add_argument("--seeds60", type=int, default=16)
	ap.add_argument("--seeds180", type=int, default=8)
	ap.add_argument("--workers", type=int, default=10)
	ap.add_argument("--sin-sondas", action="store_true", help="solo benchmark (más rápido)")
	args = ap.parse_args()
	t0 = time.time()
	tag = dt.datetime.now().strftime("%Y%m%d_%H%M")
	if args.run:
		run_dir = ROOT / "models" / "runs" / args.run
		out_dir = run_dir / "chequeos"; out_dir.mkdir(parents=True, exist_ok=True)
		striker, keeper = out_dir / f"{tag}_striker.npz", out_dir / f"{tag}_keeper.npz"
		shutil.copy2(run_dir / "striker.npz", striker); shutil.copy2(run_dir / "keeper.npz", keeper)
		titulo = f"Chequeo de {args.run} — {dt.datetime.now():%d/%m %H:%M}"
	else:
		run_dir = None
		striker, keeper = args.striker.resolve(), args.keeper.resolve()
		out_dir = ROOT / "models" / "runs" / "_analisis" / "chequeos"; out_dir.mkdir(parents=True, exist_ok=True)
		titulo = f"Chequeo de {args.nombre or striker.stem} — {dt.datetime.now():%d/%m %H:%M}"
	md = [f"# {titulo}", "", f"Par evaluado: `{striker.relative_to(ROOT) if striker.is_relative_to(ROOT) else striker}` + `_keeper`.", ""]

	if run_dir is not None:
		meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
		md += [f"## Curva del entrenamiento ({meta.get('total_hours', 0):.2f} h, {len(meta.get('phases', []))} fases)", "",
		       "| ciclo | rol | exploración | entropía | a favor / act. | en contra / act. | % a favor |", "|---|---|---|---|---|---|---|"]
		for p in meta.get("phases", []):
			s = p.get("stats", {}); gf, gc = s.get("gf_per_upd", 0), s.get("gc_per_upd", 0)
			md.append(f"| {p['cycle']} | {p['role']} | {p.get('entropy_coef', '')} | {s.get('ent_mean', '')} | {gf} | {gc} | "
			          f"{100 * gf / (gf + gc) if gf + gc else 0:.0f} % |")
		md.append("")
		print("curva lista", flush=True)

	for seeds, dur, nombre in ((args.seeds60, 60, "1 minuto (formato torneo)"), (args.seeds180, 180, "3 minutos (final)")):
		if seeds <= 0:
			continue
		filas, oro = _benchmark(striker, keeper, seeds, dur, args.workers)
		md += [f"## Partidos de {nombre}, gol de oro — {seeds} semillas por lado ({2 * seeds} partidos por rival)", "",
		       "| rival | G-E-P | neto por par | goles como izq. | goles como der. | goles de saque a favor-en contra |",
		       "|---|---|---|---|---|---|"]
		for r in ("NormalTeam", "v1", "v2.3"):
			f = filas.get(r)
			md.append(f"| {r} | **{f['gep']}** | {f['neto']:+.1f} ± {f['ic']:.1f} | {f['izq']} | {f['der']} | {f['saque']} |"
			          if f else f"| {r} | (sin datos) | | | | |")
		if oro:
			md.append(f"\n{oro}")
		md.append("")
		print(f"benchmark {dur} s listo ({time.time() - t0:.0f} s)", flush=True)

	if dur and args.seeds60 > 0:
		md += ["Referencias (1 min + gol de oro, 32 partidos por rival, G-E-P y neto):", "",
		       "| equipo | NormalTeam | v1 | v2.3 |", "|---|---|---|---|"]
		for k, v in REFERENCIAS.items():
			md.append(f"| {k} | {v['NormalTeam']} | {v['v1']} | {v['v2.3']} |")
		md.append("")

	if not args.sin_sondas:
		pct, hacia = _espaldas(striker, keeper)
		md += ["## Carrera de espaldas del striker (contra NormalTeam y v2.3, 4 partidos de 120 s)", "",
		       f"- en movimiento: **{pct['espaldas']:.0f} % de espaldas**, {pct['adelante']:.0f} % de frente, "
		       f"{pct['costado']:.0f} % de costado; yendo hacia la pelota, {hacia:.0f} % de espaldas",
		       "- referencias: clon de partida 5 %, DL elegido 92 %, rule-based v2.3 28 % (solo para destrabarse)", ""]
		print("espaldas listo", flush=True)
		md += ["## Saques (sonda_saque, 300 s contra v2.3 y contra v1)", "", "```"] + _saques(striker, keeper) + ["```", ""]
		print("saques listo", flush=True)

	md.append(f"_Chequeo hecho en {(time.time() - t0) / 60:.1f} min con {args.workers} procesos._")
	informe = out_dir / f"{tag}.md"
	informe.write_text("\n".join(md) + "\n", encoding="utf-8")
	print("\n".join(md))
	print(f"\nInforme: {informe}")


if __name__ == "__main__":
	main()
