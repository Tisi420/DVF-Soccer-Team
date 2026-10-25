"""Sonda de recompensa (sesión 24): ¿el striker no va a la pelota por la RED o por la RECOMPENSA?

Parte 1 — qué decide cada red de striker en el saque: probabilidades de sus 3 controles
  (adelante/atrás, derecha/izquierda, giro) y entropía (3,30 = totalmente al azar, 0 = siempre
  lo mismo).
Parte 2 — cuánto cobra cada FORMA DE JUGAR con dvf_rewards.compute_reward, en el mismo entorno
  del entrenamiento (setup_dl_notebook, action_repeat 4, jugando de azul): al azar, quieto,
  "perseguir la pelota" (script simple) y el striker rule-based v2.3. Separa la parte densa
  (lo que paga cada paso) de la de goles (+20 / -1), que es la que mete ruido.
  Si "perseguir" no cobra claramente más que "al azar" en la parte densa, el problema está en
  los PESOS de la recompensa; si cobra más, el problema es que la señal se pierde en el ruido.

Uso: python scripts/sondas/sonda_recompensa.py [segundos por prueba] [rival]
"""
import math, os, random, sys, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
os.environ.setdefault("DVF_DL_RUN", "corrida2")        # keeper propio = el de corrida2
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

DL = _mod("soccer_team_DVF_DL.py", "dl_probe")


def _pesos(p):
	w = np.load(p); return {k: w[k] for k in w.files}


# ---------------------------------------------------------------- parte 1
def parte1():
	redes = {"noche1 05:59 (v1, ciclo 28)": ROOT / "models/runs/noche1/respaldo_0600/striker.npz",
	         "noche1 final (v2)": ROOT / "models/runs/noche1/striker.npz",
	         "corrida2 ahora (v3)": ROOT / "models/runs/corrida2/striker.npz"}
	gt = S.GoalTracker()
	pg, space, ks, kk, os_, ok = S.create_simulation(_mod(f"{RIVAL}.py", "rv1"), gt)
	pg.update_view_fields()
	obs = build_observation(ks)
	print("PARTE 1 · striker azul en su spawn, pelota en el centro (adelante y un poco a la izquierda)")
	print("  lo ideal: casi siempre ADELANTE, algo a la IZQUIERDA, poco giro")
	nombres = (("quieto", "adelante", "atrás"), ("nada", "derecha", "izquierda"), ("nada", "giro izq", "giro der"))
	for nombre, p in redes.items():
		if not p.exists():
			continue
		probs = DL._infer(_pesos(p), obs)
		ent = -sum(float((q * np.log(q + 1e-12)).sum()) for q in probs)
		txt = " | ".join(", ".join(f"{n} {100 * v:.0f}%" for n, v in zip(nn, q)) for nn, q in zip(nombres, probs))
		print(f"  {nombre:28} entropía {ent:.2f}/3.30 · {txt}")


# ---------------------------------------------------------------- parte 2
def _perseguir(pl, ball):
	"""Script simple: girar hacia la pelota y avanzar (moviéndose de costado para corregir)."""
	a = pl.body.angle
	fx, fy = math.sin(a), -math.cos(a)            # frente
	rx, ry = math.cos(a), math.sin(a)             # derecha
	dx, dy = ball.body.position.x - pl.body.position.x, ball.body.position.y - pl.body.position.y
	f, r = fx * dx + fy * dy, rx * dx + ry * dy
	turn = 0 if abs(r) < 0.15 * max(abs(f), 1) else (2 if r > 0 else 1)
	return [1 if f > 0 else 2, 1 if r > 30 else (2 if r < -30 else 0), turn]


def correr(modo, seed=1):
	random.seed(seed); np.random.seed(seed)
	gt = S.GoalTracker()
	pg, space, ks, kk, os_, ok = S.create_simulation(_mod(f"{RIVAL}.py", f"rv_{modo}"), gt)
	agente = ks
	if modo == "rule-based v2.3":
		v2 = _mod("soccer_team_DVF_v2.py", "v2probe")
		agente = v2.Striker(); agente.set_team("blue")
		pg.init_players(os_, ok, agente, kk)
	kw = DL._load_weights.__globals__["Keeper"]._weights or _pesos(ROOT / "models/runs/corrida2/keeper.npz")
	pasos = int(SEG * S.FPS / AR)
	denso, goles_r, gf, gc, carrera = 0.0, 0.0, 0, 0, 0.0
	for _ in range(pasos):
		if modo == "al azar":
			act = [random.randrange(3) for _ in range(3)]
		elif modo == "quieto":
			act = [0, 0, 0]
		elif modo == "perseguir":
			act = _perseguir(agente, pg.ball)
		else:
			act = None
		pk = DL._infer(kw, build_observation(kk))
		ak = [int(np.random.choice(3, p=q)) for q in pk]
		pbp = (pg.ball.body.position.x, pg.ball.body.position.y); pbv = (pg.ball.body.velocity.x, pg.ball.body.velocity.y)
		psp = (agente.body.position.x, agente.body.position.y)
		pds = math.hypot(pbp[0] - psp[0], pbp[1] - psp[1])
		en_saque = R._en_saque(pbp, pbv)
		sc = cc = False
		for _ in range(AR):
			if act is None:
				agente.default()                  # el rule-based decide cada frame
			else:
				agente.action = list(act)
			kk.action = list(ak)
			S.sim_step(pg, space, agente, kk, os_, ok, call_opponent_ai=True)
			ev = gt.pop()
			sc |= ev == "blue"; cc |= ev == "purple"
		r = R.compute_reward(sc, cc, "striker", player=agente, ball=pg.ball, prev_ball_pos=pbp,
		                     prev_ball_vel=pbv, prev_dist=pds, prev_player_pos=psp)
		if sc or cc:
			goles_r += r; gf += sc; gc += cc
		else:
			denso += r
			if en_saque:
				d = math.hypot(pg.ball.body.position.x - agente.body.position.x,
				               pg.ball.body.position.y - agente.body.position.y)
				carrera += R.W_KICKOFF_RACE * (pds - d) / R.MAX_DIST
		S.stuck_ball_step(pg, 0, 10 ** 9)
	return {"denso": denso, "goles": goles_r, "gf": gf, "gc": gc, "carrera": carrera}


def parte2():
	print(f"\nPARTE 2 · recompensa del striker en {SEG:.0f} s de juego contra {RIVAL} (entorno de entrenamiento)")
	print(f"  {'forma de jugar':18} {'densa total':>11} {'por minuto':>10} {'carrera saque':>13} {'goles a favor/en contra':>24} {'parte goles':>11}")
	for modo in ("al azar", "quieto", "perseguir", "rule-based v2.3"):
		res = [correr(modo, s) for s in (1, 2)]
		d = statistics.mean(x["denso"] for x in res); g = statistics.mean(x["goles"] for x in res)
		c = statistics.mean(x["carrera"] for x in res)
		gf = statistics.mean(x["gf"] for x in res); gc = statistics.mean(x["gc"] for x in res)
		print(f"  {modo:18} {d:11.2f} {60 * d / SEG:10.3f} {c:13.2f} {gf:11.1f} / {gc:<10.1f} {g:11.1f}")


if __name__ == "__main__":
	parte1()
	parte2()
