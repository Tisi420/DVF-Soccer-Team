"""Sonda de recompensa del KEEPER (sesión 28): ¿por qué no vuelve al arco?

Parte 1 — qué decide cada red de keeper en el saque (keeper azul en su spawn x≈418, mirando a +x;
  para volver al arco tiene que ir ATRÁS y un poco a la DERECHA = hacia +y).
Parte 2 — cuánto cobra el keeper con dvf_rewards.compute_reward según cómo juegue, en el entorno
  de entrenamiento (azul, action_repeat 4), con nuestro striker = la red de corrida2:
  al azar, quieto en el spawn, "volver y cubrir" (script: ir al punto ideal entre pelota y arco,
  mirando la pelota) y el keeper rule-based v2.3. Separa la parte densa de la de goles (−5 por gol
  recibido) y mide dónde pasa el tiempo (mediana de x).

Uso: python scripts/sondas/sonda_keeper_recompensa.py [segundos por prueba] [rival]
"""
import math, os, random, sys, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
os.environ.setdefault("DVF_DL_RUN", "corrida2")
import numpy as np
import setup_dl_notebook as S
import dvf_rewards as R
from game.keras_core import build_observation
import importlib.util

SEG = float(sys.argv[1]) if len(sys.argv) > 1 else 240
RIVAL = sys.argv[2] if len(sys.argv) > 2 else "soccer_team_DVF_v2"
AR = 4


def _mod(path, alias):
	spec = importlib.util.spec_from_file_location(alias, ROOT / path)
	m = importlib.util.module_from_spec(spec); sys.modules[alias] = m; spec.loader.exec_module(m)
	return m

DL = _mod("soccer_team_DVF_DL.py", "dl_kprobe")


def _pesos(p):
	w = np.load(p); return {k: w[k] for k in w.files}


def parte1():
	redes = {"noche1 05:59 (v1)": ROOT / "models/runs/noche1/respaldo_0600/keeper.npz",
	         "noche1 final (v2)": ROOT / "models/runs/noche1/keeper.npz",
	         "corrida2 ahora (v3)": ROOT / "models/runs/corrida2/keeper.npz"}
	gt = S.GoalTracker()
	pg, space, ks, kk, os_, ok = S.create_simulation(_mod(f"{RIVAL}.py", "kr1"), gt)
	pg.update_view_fields()
	obs = build_observation(kk)
	print("PARTE 1 · keeper azul en su spawn (x≈418), pelota en el centro")
	print("  lo ideal para volver al arco: ATRÁS (y algo a la DERECHA = hacia abajo)")
	nombres = (("quieto", "adelante", "atrás"), ("nada", "derecha", "izquierda"), ("nada", "giro izq", "giro der"))
	for nombre, p in redes.items():
		if not p.exists():
			continue
		probs = DL._infer(_pesos(p), obs)
		ent = -sum(float((q * np.log(q + 1e-12)).sum()) for q in probs)
		txt = " | ".join(", ".join(f"{n} {100 * v:.0f}%" for n, v in zip(nn, q)) for nn, q in zip(nombres, probs))
		print(f"  {nombre:22} entropía {ent:.2f}/3.30 · {txt}")


def _volver(pl, ball):
	"""Script: ir al punto ideal (sobre la línea pelota-arco, KEEPER_STANDOFF delante) mirando la pelota."""
	bx, by = ball.body.position.x, ball.body.position.y
	gx, gy = bx - R.GOAL_BLUE_X, by - R.GOAL_CENTER_Y
	gd = max(math.hypot(gx, gy), 1.0)
	tx, ty = R.GOAL_BLUE_X + R.KEEPER_STANDOFF * gx / gd, R.GOAL_CENTER_Y + R.KEEPER_STANDOFF * gy / gd
	a = pl.body.angle
	fx, fy = math.sin(a), -math.cos(a)
	rx, ry = math.cos(a), math.sin(a)
	dx, dy = tx - pl.body.position.x, ty - pl.body.position.y
	f, r = fx * dx + fy * dy, rx * dx + ry * dy
	bxl, byl = bx - pl.body.position.x, by - pl.body.position.y
	rb = rx * bxl + ry * byl; fb_ = fx * bxl + fy * byl
	turn = 0 if abs(rb) < 0.2 * max(abs(fb_), 1) else (2 if rb > 0 else 1)
	return [1 if f > 15 else (2 if f < -15 else 0), 1 if r > 15 else (2 if r < -15 else 0), turn]


def correr(modo, seed=1):
	random.seed(seed); np.random.seed(seed)
	gt = S.GoalTracker()
	pg, space, ks, kk, os_, ok = S.create_simulation(_mod(f"{RIVAL}.py", f"kr_{modo}"), gt)
	agente = kk
	if modo == "rule-based v2.3":
		v2 = _mod("soccer_team_DVF_v2.py", "v2kprobe")
		agente = v2.Keeper(); agente.set_team("blue")
		pg.init_players(os_, ok, ks, agente)
	sw = _pesos(ROOT / "models/runs/corrida2/striker.npz")
	pasos = int(SEG * S.FPS / AR)
	denso, gol_r, gf, gc, xs = 0.0, 0.0, 0, 0, []
	for _ in range(pasos):
		if modo == "al azar":
			act = [random.randrange(3) for _ in range(3)]
		elif modo == "quieto":
			act = [0, 0, 0]
		elif modo == "volver y cubrir":
			act = _volver(agente, pg.ball)
		else:
			act = None
		ps = DL._infer(sw, build_observation(ks))
		a_s = [int(np.random.choice(3, p=q)) for q in ps]
		pbp = (pg.ball.body.position.x, pg.ball.body.position.y); pbv = (pg.ball.body.velocity.x, pg.ball.body.velocity.y)
		pkp = (agente.body.position.x, agente.body.position.y)
		pdk = math.hypot(pbp[0] - pkp[0], pbp[1] - pkp[1])
		sc = cc = False
		for _ in range(AR):
			if act is None:
				agente.default()
			else:
				agente.action = list(act)
			ks.action = list(a_s)
			S.sim_step(pg, space, ks, agente, os_, ok, call_opponent_ai=True)
			ev = gt.pop()
			sc |= ev == "blue"; cc |= ev == "purple"
		r = R.compute_reward(sc, cc, "keeper", player=agente, ball=pg.ball, prev_ball_pos=pbp,
		                     prev_ball_vel=pbv, prev_dist=pdk, prev_player_pos=pkp)
		xs.append(agente.body.position.x)
		if sc or cc:
			gol_r += r; gf += sc; gc += cc
		else:
			denso += r
	return {"denso": denso, "goles": gol_r, "gf": gf, "gc": gc, "x": statistics.median(xs)}


def parte2():
	print(f"\nPARTE 2 · recompensa del keeper en {SEG:.0f} s contra {RIVAL} (entorno de entrenamiento, 2 semillas)")
	print(f"  {'forma de jugar':18} {'densa':>8} {'goles (−5 c/u)':>15} {'total':>8} {'a favor/en contra':>18} {'x mediana':>10}")
	for modo in ("al azar", "quieto", "volver y cubrir", "rule-based v2.3"):
		res = [correr(modo, s) for s in (1, 2)]
		m = lambda k: statistics.mean(x[k] for x in res)
		print(f"  {modo:18} {m('denso'):8.2f} {m('goles'):15.1f} {m('denso') + m('goles'):8.1f} "
		      f"{m('gf'):8.1f} / {m('gc'):<7.1f} {m('x'):10.0f}")


if __name__ == "__main__":
	parte1()
	parte2()
