#!/usr/bin/env python3
"""
Evalúa una corrida de DL con el benchmark: varios checkpoints contra varios rivales (DVF, 2026-10-17).

Para cada punto elegido (fin de fase de la corrida + el modelo final) lanza scripts/benchmark.py
con soccer_team_DVF_DL y las variables DVF_DL_STRIKER / DVF_DL_KEEPER apuntando a ese par de
.npz, en ambos lados, con y sin ruido en el saque. Guarda los JSONL crudos en
models/runs/<run>/eval/ y escribe eval/resumen.md con la diferencia de gol neta por partido
(promedio ± ~95 %) de cada punto contra cada rival. Es el paso "Domingo a la mañana" de
PLAN_ENTREGA.md en un solo comando.

Usa muchos núcleos: correrlo cuando el entrenamiento ya terminó (o bajar --workers).

    python scripts/evaluar_corrida.py noche1 --dry-run        # ver qué puntos evaluaría
    python scripts/evaluar_corrida.py noche1                  # 5 puntos, 4 semillas, ruido 3 y 0
    python scripts/evaluar_corrida.py noche1 --puntos 3 --seeds 8 --jitter 3
"""
import argparse
import datetime as dt
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAM = "soccer_team_DVF_DL"
# Nombre de checkpoint de train_dl.py: striker_<fecha>_<hora>_IT0100_s1433600_<rol de la fase>.npz
CKPT_RE = re.compile(r"^striker_(\d{8}_\d{6})_IT(\d{4})_s(\d+)_(striker|keeper)\.npz$")


def _fin_de_fases(ckpt_dir):
	"""Último checkpoint (striker, keeper) de cada fase, en orden cronológico."""
	fases = {}
	for p in ckpt_dir.glob("striker_*.npz"):
		m = CKPT_RE.match(p.name)
		if not m:
			continue
		tag, it, role = m.group(1), int(m.group(2)), m.group(4)
		keeper = p.with_name("keeper_" + p.name[len("striker_"):])
		if keeper.is_file() and it >= fases.get(tag, (-1,))[0]:
			fases[tag] = (it, role, p, keeper)
	return [(tag, *fases[tag]) for tag in sorted(fases)]


def _ultimo_por_ciclo(run_dir, fases):
	"""{ciclo: (striker.npz, keeper.npz)} con el último checkpoint de cada ciclo de run.json.

	La etiqueta del checkpoint es la hora de inicio de la fase; un checkpoint pertenece al ciclo
	cuya primera fase empezó antes que él (cubre también fases cortadas por un crash). Como el
	keeper entrena después del striker, el último par del ciclo tiene a los dos ya entrenados.
	"""
	meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
	# La etiqueta se toma ~1 s después del "start" de run.json, así que se aparea con tolerancia.
	# Las fases cortadas por un crash y la fase en curso no figuran en run.json: quedan afuera.
	inicios = [(dt.datetime.fromisoformat(f["start"]), f["cycle"]) for f in meta.get("phases", [])]
	out = {}
	for tag, it, role, s, k in fases:            # ya vienen en orden cronológico
		t = dt.datetime.strptime(tag, "%Y%m%d_%H%M%S")
		for t0, c in inicios:
			if abs((t - t0).total_seconds()) <= 10:
				out[c] = (s, k)
	return out


def _elegir(puntos, n):
	"""n puntos repartidos parejo (siempre incluye el primero y el último)."""
	if n >= len(puntos):
		return puntos
	idx = sorted({round(i * (len(puntos) - 1) / (n - 1)) for i in range(n)}) if n > 1 else [len(puntos) - 1]
	return [puntos[i] for i in idx]


def _neto(rows, opp):
	"""Diferencias de gol (DL − rival) por partido, de los dos lados."""
	out = []
	for r in rows:
		if r.get("error"):
			continue
		if (r["left"], r["right"]) == (TEAM, opp):
			out.append(r["score"][0] - r["score"][1])
		elif (r["left"], r["right"]) == (opp, TEAM):
			out.append(r["score"][1] - r["score"][0])
	return out


def _fmt(xs):
	if not xs:
		return "—"
	m = statistics.mean(xs)
	ci = 1.96 * statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0
	return f"{m:+.1f} ± {ci:.1f}"


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("run")
	ap.add_argument("--puntos", type=int, default=5, help="checkpoints de fin de fase a evaluar (+ el final)")
	ap.add_argument("--vs", nargs="+", default=["soccer_team_NormalTeam", "soccer_team_DVF", "soccer_team_DVF_v2"])
	ap.add_argument("--seeds", type=int, default=4, help="partidos por lado y rival")
	ap.add_argument("--jitter", type=float, nargs="+", default=[3.0, 0.0], help="ruido del saque (px)")
	ap.add_argument("--duration", type=float, default=300)
	ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
	ap.add_argument("--dry-run", action="store_true", help="solo listar los puntos")
	# Combinaciones (sesión 19): el mejor striker y el mejor keeper pueden ser de ciclos distintos.
	ap.add_argument("--strikers", nargs="+", metavar="CICLO",
	                help="ciclos del striker a combinar (ej. 14 26 27 final); requiere --keepers")
	ap.add_argument("--keepers", nargs="+", metavar="CICLO", help="ciclos del keeper a combinar")
	args = ap.parse_args()

	run_dir = ROOT / "models" / "runs" / args.run
	fases = _fin_de_fases(run_dir / "checkpoints")
	if args.strikers or args.keepers:
		if not (args.strikers and args.keepers):
			ap.error("--strikers y --keepers van juntos")
		por_ciclo = _ultimo_por_ciclo(run_dir, fases)
		def _red(c, rol):
			if c == "final":
				return run_dir / f"{rol}.npz"
			if int(c) not in por_ciclo:
				ap.error(f"no hay checkpoints del ciclo {c} (hay: {sorted(por_ciclo)})")
			s, k = por_ciclo[int(c)]
			return s if rol == "striker" else k
		puntos = [(f"S{cs}_K{ck}", _red(cs, "striker"), _red(ck, "keeper"))
		          for cs in args.strikers for ck in args.keepers]
	else:
		puntos = [(f"{tag}_IT{it:04d}_{role}", s, k) for tag, it, role, s, k in _elegir(fases, args.puntos)]
		puntos.append(("final", run_dir / "striker.npz", run_dir / "keeper.npz"))
	print(f"{args.run}: {len(fases)} fases con checkpoints; evalúo {len(puntos)} puntos "
	      f"vs {', '.join(args.vs)}, {args.seeds} semillas por lado, ruido {args.jitter}")
	for label, s, k in puntos:
		print(f"  {label:36} {s.name} + {k.name}")
	if args.dry_run:
		return

	eval_dir = run_dir / "eval"
	eval_dir.mkdir(exist_ok=True)
	tabla = {}                                   # (label, jitter) -> {rival: [netos]}
	t0 = time.time()
	for label, s, k in puntos:
		env = dict(os.environ, DVF_DL_STRIKER=str(s), DVF_DL_KEEPER=str(k))
		env.pop("DVF_DL_RUN", None)              # que mande el par explícito
		for j in args.jitter:
			out = eval_dir / f"{label}_j{j:g}.jsonl"
			cmd = [sys.executable, str(ROOT / "scripts" / "benchmark.py"), TEAM, "--vs", *args.vs,
			       "--seeds", str(args.seeds), "--jitter", str(j), "--duration", str(args.duration),
			       "--workers", str(args.workers), "--out", str(out)]
			res = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
			(eval_dir / f"{label}_j{j:g}.txt").write_text(res.stdout + res.stderr, encoding="utf-8")
			rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()] if out.exists() else []
			tabla[(label, j)] = {opp: _neto(rows, Path(opp).stem) for opp in args.vs}
			fallas = sum(1 for r in rows if r.get("error"))
			print(f"[{time.time() - t0:5.0f} s] {label} ruido {j:g}: " +
			      "  ".join(f"{Path(o).stem}={_fmt(v)}" for o, v in tabla[(label, j)].items()) +
			      (f"  ({fallas} fallas)" if fallas else ""), flush=True)

	head = "| punto | ruido | " + " | ".join(Path(o).stem for o in args.vs) + " |"
	lines = [f"# Evaluación de {args.run}", "",
	         f"Diferencia de gol neta por partido (DL − rival), promedio ± ~95 %, {args.seeds} partidos "
	         f"por lado de {args.duration:.0f} s. Generado por scripts/evaluar_corrida.py.", "",
	         head, "|" + "---|" * (2 + len(args.vs))]
	for (label, j), por_rival in tabla.items():
		lines.append(f"| {label} | {j:g} | " + " | ".join(_fmt(v) for v in por_rival.values()) + " |")
	nombre = "resumen_combos.md" if args.strikers else "resumen.md"   # no pisar una con la otra
	(eval_dir / nombre).write_text("\n".join(lines) + "\n", encoding="utf-8")
	print(f"\nResumen en {eval_dir / nombre}")


if __name__ == "__main__":
	main()
