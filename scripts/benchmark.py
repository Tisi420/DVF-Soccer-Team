#!/usr/bin/env python3
"""
Banco de pruebas headless para equipos de soccer (equipo DVF, 2026-10-17).

Juega muchos partidos sin ventana, en AMBOS lados de la cancha, con semillas fijas y
un pequeño ruido en la posición de la pelota en cada saque, y resume el resultado.

    python scripts/benchmark.py soccer_team_DVF_v2 --vs soccer_team_DVF
    python scripts/benchmark.py soccer_team_DVF_v2 --vs soccer_team_DVF soccer_team_NormalTeam --seeds 16
    python scripts/benchmark.py soccer_team_DVF_v2 --vs soccer_team_DVF --kickoff-trials 200

Por qué así (ver CHANGELOG.md, sesiones 2 y 3):
  * El saque es caótico: los dos delanteros llegan casi a la vez y unos píxeles deciden
    el resultado. Sin ruido, cada saque da siempre lo mismo y las conclusiones engañan.
  * Un equipo puede rendir distinto en cada lado, así que se juega siempre en los dos.
  * Cada partido corre en un proceso nuevo: el estado de los módulos (instancias
    striker/keeper, atributos de clase) no se arrastra entre partidos.

Documentación completa: docs/BENCHMARK.md
"""
import argparse
import importlib.util
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # raíz del proyecto (donde está run.py)
FPS = 60
BALL_CENTER = (697.5, 440.0)                     # punto de saque (screen 1395x880 / 2)
KICKOFF_GOAL_S = 5.0                             # gol "de saque" = antes de 5 s del reinicio
KICKOFF_TRIAL_S = 3.0                            # duración de cada prueba de saque aislado
RESULT_TAG = "@@RESULT "                         # marca de la línea JSON del proceso hijo
FIELD_X0, FIELD_X1, FIELD_Y0, FIELD_Y1 = 127, 1272, 59, 825   # campo sin los huecos de los arcos
CORNER_MARGIN = 150                              # px desde ambos bordes = esquina
CORNER_SLOW = 60                                 # px/s: pelota "quieta"


# ---------------------------------------------------------------------------
# Proceso hijo: un partido (o una prueba de saque)
# ---------------------------------------------------------------------------

def _resolve_team(team: str) -> Path:
	"""Acepta un nombre de módulo (soccer_team_DVF) o una ruta a un .py."""
	p = Path(team)
	if p.suffix != ".py":
		p = ROOT / f"{team}.py"
	elif not p.is_absolute():
		p = (Path.cwd() / p).resolve()
	if not p.is_file():
		raise SystemExit(f"No encuentro el equipo '{team}' ({p})")
	return p


def _load_team(path: Path, alias: str):
	"""Carga el archivo como módulo nuevo con nombre propio.

	Así un equipo puede jugar contra sí mismo (partido espejo) sin compartir instancias.
	"""
	spec = importlib.util.spec_from_file_location(alias, path)
	module = importlib.util.module_from_spec(spec)
	sys.modules[alias] = module
	spec.loader.exec_module(module)
	return module


def _play(job: dict) -> dict:
	"""Juega un partido headless y devuelve marcador + goles con tiempo desde el saque."""
	os.chdir(ROOT)
	sys.path.insert(0, str(ROOT))
	random.seed(job["seed"])          # orden de default() (random.shuffle) + ruido del saque
	try:                              # 2026-10-17: los equipos DL muestrean acciones con numpy
		import numpy as np
		np.random.seed(job["seed"])
	except ImportError:
		pass

	from game.engine import GameEngine

	left = _load_team(Path(job["left"]), "bench_left")
	right = _load_team(Path(job["right"]), "bench_right")
	kickoff_only = job["kickoff_only"]
	duration = KICKOFF_TRIAL_S if kickoff_only else job["duration"]
	# 2026-10-24 (sesión 59): gol de oro como en el torneo (partidos de 1 min). Si al cumplirse
	# `duration` el marcador está empatado, se sigue hasta el próximo gol (tope: oro_max s más).
	oro = bool(job.get("gol_de_oro")) and not kickoff_only
	oro_max = float(job.get("oro_max", 120.0))
	engine_s = duration + oro_max if oro else duration

	eng = GameEngine(team_left=left, team_right=right, fps=FPS,
	                 match_duration_s=engine_s, headless=True)
	pg = eng.playground

	# Cada reinicio (gol, pelota quieta mucho tiempo) es un saque: se reinicia el reloj del
	# saque y se mueve la pelota ±jitter px para muestrear el caos del saque.
	state = {"since": 0}
	orig_reset = pg._apply_reset

	def reset_with_jitter():
		orig_reset()
		state["since"] = 0
		j = job["jitter"]
		if j > 0:
			pg.ball.set_pos((BALL_CENTER[0] + random.uniform(-j, j),
			                 BALL_CENTER[1] + random.uniform(-j, j)))

	pg._apply_reset = reset_with_jitter
	reset_with_jitter()               # el saque inicial ya se hizo en GameEngine.__init__

	# Emulación del "stuck watch" del juego con ventana (game/engine.py::_update_stuck_watch),
	# que en headless no corre: pelota quieta (radio _STUCK_RADIUS) durante 3 s -> cuenta
	# regresiva 3-2-1 sobre juego vivo; si la pelota sigue ahí al terminar -> saque.
	# Sin esto, un partido trabado se queda así ~42 s (solo el MovementWatcher reinicia).
	try:
		from game.engine import _STUCK_RADIUS
		from game.renderer.whistle import COUNTDOWN_STEP
	except ImportError:                       # por si cambia el motor
		_STUCK_RADIUS, COUNTDOWN_STEP = 45, 0.8
	stuck = {"anchor": None, "dwell": 0, "countdown": -1, "resets": 0}

	def stuck_watch():
		bx, by = pg.ball.body.position
		a = stuck["anchor"]
		near = a is not None and (bx - a[0]) ** 2 + (by - a[1]) ** 2 <= _STUCK_RADIUS ** 2
		if stuck["countdown"] >= 0:           # cuenta regresiva en curso
			if not near:                      # la pelota se liberó -> se cancela
				stuck.update(anchor=None, dwell=0, countdown=-1)
				return
			stuck["countdown"] += 1
			if stuck["countdown"] >= int(COUNTDOWN_STEP * 3 * FPS):
				stuck.update(anchor=None, dwell=0, countdown=-1)
				stuck["resets"] += 1
				pg.request_reset("stuck")
			return
		if near:
			stuck["dwell"] += 1
			if stuck["dwell"] >= 3 * FPS:
				stuck.update(dwell=0, countdown=0)
		else:
			stuck.update(anchor=(bx, by), dwell=0)

	goals = []
	orig_goal_cb = pg.goalCallback

	def on_goal(team):
		# "blue" = equipo de la izquierda, "purple" = equipo de la derecha
		goals.append({"by": "left" if team == "blue" else "right",
		              "t": round(state["since"] / FPS, 2)})
		stuck.update(anchor=None, dwell=0, countdown=-1)   # el motor también lo reinicia
		orig_goal_cb(team)

	pg.goalCallback = on_goal

	# Métrica de esquinas (2026-10-17): frames con la pelota LENTA en una esquina del campo
	# (rectángulo x 127..1272, y 59..825; a menos de CORNER_MARGIN de ambos bordes).
	corner = {"TL": 0, "TR": 0, "BL": 0, "BR": 0}
	play_frames = 0

	while eng.running:
		eng.update_state()
		if not eng.is_blocked:
			pg.loop()
			eng.space.step(1.0 / FPS)
			state["since"] += 1
			play_frames += 1
			bx, by = pg.ball.body.position
			bv = pg.ball.body.velocity
			if math.hypot(bv.x, bv.y) < CORNER_SLOW:
				cx = "L" if bx < FIELD_X0 + CORNER_MARGIN else "R" if bx > FIELD_X1 - CORNER_MARGIN else None
				cy = "T" if by < FIELD_Y0 + CORNER_MARGIN else "B" if by > FIELD_Y1 - CORNER_MARGIN else None
				if cx and cy:
					corner[cy + cx] += 1
			if job["stuck_reset"]:
				stuck_watch()
		eng.render()
		eng.tick()
		if kickoff_only and goals:
			break
		# Gol de oro: con el tiempo cumplido, termina en cuanto el marcador no está empatado.
		if oro and eng._frame_count / FPS >= duration and pg.goal_counter_blue != pg.goal_counter_purple:
			break

	return {"left": job["left_name"], "right": job["right_name"], "seed": job["seed"],
	        "score": [pg.goal_counter_blue, pg.goal_counter_purple], "goals": goals,
	        "gol_de_oro": oro and eng._frame_count / FPS > duration + 1.0 / FPS,
	        "stuck_resets": stuck["resets"],
	        "corner_frac": {k: round(v / max(1, play_frames), 4) for k, v in corner.items()}}


# ---------------------------------------------------------------------------
# Proceso padre: reparte trabajos y resume
# ---------------------------------------------------------------------------

def _run_job(job: dict) -> dict:
	"""Lanza un proceso hijo nuevo para el trabajo (estado de módulos limpio)."""
	out = subprocess.run([sys.executable, __file__, "--_worker", json.dumps(job)],
	                     capture_output=True, text=True, cwd=ROOT)
	for line in out.stdout.splitlines():
		if line.startswith(RESULT_TAG):
			return json.loads(line[len(RESULT_TAG):])
	return {"left": job["left_name"], "right": job["right_name"], "seed": job["seed"],
	        "error": (out.stderr or out.stdout)[-800:]}


def _mean(xs):
	return statistics.mean(xs) if xs else 0.0


def _se(xs):
	"""Error estándar de la media (0 si hay menos de 2 datos)."""
	return statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0


def _side_stats(results, team, opp, side):
	"""Lista de (a_favor, en_contra, saque_favor, saque_contra) de `team` jugando en `side`."""
	rows = []
	for r in results:
		if (side == "left" and (r["left"], r["right"]) == (team, opp)) or \
		   (side == "right" and (r["left"], r["right"]) == (opp, team)):
			me = 0 if side == "left" else 1
			gf, ga = r["score"][me], r["score"][1 - me]
			kf = sum(1 for g in r["goals"] if g["by"] == side and g["t"] < KICKOFF_GOAL_S)
			ka = sum(1 for g in r["goals"] if g["by"] != side and g["t"] < KICKOFF_GOAL_S)
			rows.append((gf, ga, kf, ka))
	return rows


def _print_match_summary(results, team, opps):
	print(f"\nResultados de {team} (promedio por partido; izq = azul, der = violeta)")
	print(f"{'rival':24} {'n':>5} | {'como izq':>11} | {'como der':>11} | "
	      f"{'neto/2 part.':>14} | {'G-E-P':>8} | {'saque fav-contra':>16}")
	for opp in opps:
		L = _side_stats(results, team, opp, "left")
		R = _side_stats(results, team, opp, "right")
		if opp == team and L:
			# Espejo: no hay "nosotros" y "ellos"; lo que interesa es el sesgo de lado.
			dl = [gf - ga for gf, ga, _, _ in L]
			print(f"{opp + ' (espejo)':24} {len(L):>5} | izq {_mean([x[0] for x in L]):4.1f} - "
			      f"{_mean([x[1] for x in L]):4.1f} der | sesgo izq-der {_mean(dl):+5.1f} ± {2 * _se(dl):4.1f}")
			continue
		if not L or not R:
			print(f"{opp:24}  (sin datos)")
			continue
		dl = [gf - ga for gf, ga, _, _ in L]
		dr = [gf - ga for gf, ga, _, _ in R]
		net = _mean(dl) + _mean(dr)
		se = math.sqrt(_se(dl) ** 2 + _se(dr) ** 2)
		allds = dl + dr
		wdl = f"{sum(d > 0 for d in allds)}-{sum(d == 0 for d in allds)}-{sum(d < 0 for d in allds)}"
		both = L + R
		kick = f"{_mean([k[2] for k in both]):.1f} - {_mean([k[3] for k in both]):.1f}"
		verdict = "" if abs(net) > 2 * se else "  (dentro del ruido)"
		print(f"{opp:24} {len(L):>2}+{len(R):<2} | "
		      f"{_mean([x[0] for x in L]):4.1f} - {_mean([x[1] for x in L]):4.1f} | "
		      f"{_mean([x[0] for x in R]):4.1f} - {_mean([x[1] for x in R]):4.1f} | "
		      f"{net:+5.1f} ± {2 * se:4.1f} | {wdl:>8} | {kick:>16}{verdict}")
	print("\nneto/2 part. = (dif. de gol como izq) + (dif. de gol como der); ± = intervalo ~95 %.")
	print(f"Reinicios por pelota trabada: {_mean([r.get('stuck_resets', 0) for r in results]):.1f} por partido.")
	n_oro = sum(1 for r in results if r.get("gol_de_oro"))
	if n_oro:
		print(f"Partidos definidos por gol de oro (o empatados al tope): {n_oro} de {len(results)}.")
	# Esquinas, desde el punto de vista del equipo evaluado: "propias" = lado de su arco.
	own = []; enemy = []
	for r in results:
		cf = r.get("corner_frac")
		if not cf or (r["left"] == r["right"]):
			continue
		me_left = r["left"] == team
		o = cf["TL"] + cf["BL"] if me_left else cf["TR"] + cf["BR"]
		e = cf["TR"] + cf["BR"] if me_left else cf["TL"] + cf["BL"]
		own.append(o); enemy.append(e)
	if own:
		print(f"Pelota quieta en esquinas: {100 * (_mean(own) + _mean(enemy)):.1f}% del tiempo "
		      f"(de nuestro lado {100 * _mean(own):.1f}%, del lado rival {100 * _mean(enemy):.1f}%).")


def _print_kickoff_summary(results, team, opps):
	print(f"\nSaques aislados de {team} ({KICKOFF_TRIAL_S:.0f} s cada uno, pelota con ruido)")
	print(f"{'rival':24} | {'como izq: a favor / en contra':>30} | {'como der: a favor / en contra':>30}")
	for opp in opps:
		if opp == team:
			rows = _side_stats(results, team, opp, "left")
			n = max(1, len(rows))
			print(f"{opp + ' (espejo)':24} | gana izq {sum(x[0] for x in rows)}/{len(rows)} "
			      f"({100 * sum(x[0] for x in rows) / n:4.1f}%) | gana der {sum(x[1] for x in rows)}/{len(rows)} "
			      f"({100 * sum(x[1] for x in rows) / n:4.1f}%)")
			continue
		cells = []
		for side in ("left", "right"):
			rows = _side_stats(results, team, opp, side)
			n = len(rows)
			gf = sum(x[0] for x in rows)
			ga = sum(x[1] for x in rows)
			cells.append(f"{gf:>4}/{n} ({100 * gf / max(1, n):4.1f}%) / {ga:>4}/{n} ({100 * ga / max(1, n):4.1f}%)")
		print(f"{opp:24} | {cells[0]:>30} | {cells[1]:>30}")


def main():
	# UTF-8 siempre: en consola Windows Python escribe vía UTF-16 igual, y al redirigir a un
	# archivo/tubería evita que ±, á... salgan como '�' (cp1252).
	sys.stdout.reconfigure(encoding="utf-8", errors="replace")

	ap = argparse.ArgumentParser(
		description="Banco de pruebas headless: ambos lados, semillas fijas, ruido en el saque.")
	ap.add_argument("team", nargs="?", help="equipo a evaluar (módulo o ruta .py)")
	ap.add_argument("--vs", nargs="+", default=["soccer_team_DVF"], metavar="RIVAL",
	                help="rivales (default: soccer_team_DVF). Usá el mismo equipo para un espejo.")
	ap.add_argument("--seeds", type=int, default=8, help="partidos por lado y rival (default 8)")
	ap.add_argument("--duration", type=float, default=300, help="segundos simulados por partido (default 300)")
	ap.add_argument("--gol-de-oro", action="store_true",
	                help="formato torneo: si al terminar hay empate, se sigue hasta el próximo gol")
	ap.add_argument("--oro-max", type=float, default=120, help="tope del gol de oro en s (default 120)")
	ap.add_argument("--jitter", type=float, default=3.0,
	                help="ruido ±px de la pelota en cada saque (default 3; 0 = determinista)")
	ap.add_argument("--no-stuck-reset", action="store_true",
	                help="no emular el reinicio por pelota trabada del juego con ventana "
	                     "(3 s quieta + 3-2-1). Por defecto se emula.")
	ap.add_argument("--kickoff-trials", type=int, default=0, metavar="N",
	                help="en vez de partidos, N saques aislados de 3 s por lado (mide solo el saque)")
	ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2),
	                help="procesos en paralelo (default: núcleos - 2)")
	ap.add_argument("--out", type=Path, help="guardar resultados crudos en JSONL")
	ap.add_argument("--_worker", help=argparse.SUPPRESS)
	args = ap.parse_args()

	if args._worker:                            # modo hijo: un partido y salir
		print(RESULT_TAG + json.dumps(_play(json.loads(args._worker))), flush=True)
		return
	if not args.team:
		ap.error("falta el equipo a evaluar")

	team_path = _resolve_team(args.team)
	team = team_path.stem
	opps = [(_resolve_team(o), _resolve_team(o).stem) for o in args.vs]
	kickoff_only = args.kickoff_trials > 0
	n = args.kickoff_trials if kickoff_only else args.seeds

	jobs = []
	for opp_path, opp in opps:
		# Espejo (mismo archivo en ambos lados): las dos orientaciones son el mismo partido,
		# así que se juega una sola vez por semilla.
		sides = [((team_path, team), (opp_path, opp))]
		if opp_path != team_path:
			sides.append(((opp_path, opp), (team_path, team)))
		for seed in range(n):
			for (lp, ln), (rp, rn) in sides:
				jobs.append({"left": str(lp), "right": str(rp), "left_name": ln, "right_name": rn,
				             "seed": seed, "duration": args.duration, "jitter": args.jitter,
				             "kickoff_only": kickoff_only, "stuck_reset": not args.no_stuck_reset,
				             "gol_de_oro": args.gol_de_oro, "oro_max": args.oro_max})

	kind = f"{n} saques" if kickoff_only else f"{n} partidos de {args.duration:.0f} s" + (" con gol de oro" if args.gol_de_oro else "")
	stuck_txt = "sin" if args.no_stuck_reset else "con"
	print(f"{team} vs {', '.join(o for _, o in opps)}: {kind} por lado, ruido ±{args.jitter} px, "
	      f"{stuck_txt} reinicio por pelota trabada, "
	      f"{len(jobs)} trabajos en {args.workers} procesos", flush=True)

	t0 = time.time()
	results, errors = [], []
	with ThreadPoolExecutor(args.workers) as ex:
		futures = [ex.submit(_run_job, j) for j in jobs]
		for i, fut in enumerate(as_completed(futures), 1):
			r = fut.result()
			(errors if "error" in r else results).append(r)
			if i % max(1, len(jobs) // 20) == 0 or i == len(jobs):
				print(f"\r  {i}/{len(jobs)}  ({time.time() - t0:.0f} s)", end="", flush=True)
	print()

	if args.out:
		with open(args.out, "w", encoding="utf-8") as f:
			for r in results + errors:
				f.write(json.dumps(r) + "\n")
		print(f"Resultados crudos en {args.out}")
	if errors:
		print(f"\n{len(errors)} trabajos fallaron. Primer error:\n{errors[0]['error']}")

	opp_names = [o for _, o in opps]
	if kickoff_only:
		_print_kickoff_summary(results, team, opp_names)
	else:
		_print_match_summary(results, team, opp_names)


if __name__ == "__main__":
	main()
