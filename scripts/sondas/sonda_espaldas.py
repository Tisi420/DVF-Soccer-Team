"""Sonda (sesión 57): ¿cuánto corre DE ESPALDAS el striker?

Para cada striker juega partidos headless como azul (izquierda) y clasifica cada frame en que se
mueve (velocidad > MIN_SPEED) según el ángulo entre su velocidad y su frente (sin a, -cos a):
  adelante  cos > 0,5      de costado  |cos| <= 0,5      de espaldas  cos < -0,5
También separa "yendo hacia la pelota" (la distancia a la pelota baja) del resto.

Uso: python scripts/sondas/sonda_espaldas.py [segundos por partido]
"""
import math, os, random, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np
import benchmark as B
from game.engine import GameEngine

SEG = 120.0   # se cambia con el primer argumento (ver main)
MIN_SPEED = 60.0
RIVALES = ["soccer_team_NormalTeam", "soccer_team_DVF_v2"]
M = ROOT / "models"
EQUIPOS = {   # nombre -> (archivo del equipo, variables de entorno para el DL)
	"DL elegido (corrida3 23:36)": ("soccer_team_DVF_DL.py", {}),
	"DL noche1 05:59 (v1)": ("soccer_team_DVF_DL.py", {"DVF_DL_STRIKER": str(M / "runs/noche1/respaldo_0600/striker.npz"),
	                                                   "DVF_DL_KEEPER": str(M / "runs/noche1/respaldo_0600/keeper.npz")}),
	"DL clon de v2.3 (imitación)": ("soccer_team_DVF_DL.py", {"DVF_DL_STRIKER": str(M / "imitacion/striker_clon.npz"),
	                                                        "DVF_DL_KEEPER": str(M / "DVF_keeper.npz")}),
	"rule-based v2.3": ("soccer_team_DVF_v2.py", {}),
}


def medir(nombre, archivo, env, rival, seed, seg=None):
	for k in ("DVF_DL_STRIKER", "DVF_DL_KEEPER", "DVF_DL_RUN"):
		os.environ.pop(k, None)
	os.environ.update(env)
	random.seed(seed); np.random.seed(seed)
	left = B._load_team(ROOT / archivo, f"L_{abs(hash((nombre, rival, seed)))}")
	right = B._load_team(ROOT / f"{rival}.py", f"R_{abs(hash((nombre, rival, seed)))}")
	eng = GameEngine(team_left=left, team_right=right, fps=B.FPS, match_duration_s=seg or SEG, headless=True)
	pg = eng.playground; s = pg.striker_blue
	c = {"adelante": 0, "costado": 0, "espaldas": 0}
	hacia = {"adelante": 0, "costado": 0, "espaldas": 0}
	quieto = total = 0
	prev_d = None
	while eng.running:
		eng.update_state()
		if not eng.is_blocked:
			pg.loop(); eng.space.step(1.0 / B.FPS)
			total += 1
			vx, vy = s.body.velocity; sp = math.hypot(vx, vy)
			bx, by = pg.ball.body.position; px, py = s.body.position
			d = math.hypot(bx - px, by - py)
			if sp < MIN_SPEED:
				quieto += 1
			else:
				a = s.body.angle
				cos = (vx * math.sin(a) - vy * math.cos(a)) / sp
				k = "adelante" if cos > 0.5 else ("espaldas" if cos < -0.5 else "costado")
				c[k] += 1
				if prev_d is not None and d < prev_d - 0.5:
					hacia[k] += 1
			prev_d = d
		eng.render(); eng.tick()
	return c, hacia, quieto, total, (pg.goal_counter_blue, pg.goal_counter_purple)


def main():
	global SEG
	if len(sys.argv) > 1:
		SEG = float(sys.argv[1])
	print(f"{'striker':30} {'rival':24} {'quieto':>7} {'adelante':>9} {'costado':>8} {'ESPALDAS':>9} | {'hacia la pelota: espaldas':>26} | marcador")
	for nombre, (archivo, env) in EQUIPOS.items():
		tot = {"adelante": 0, "costado": 0, "espaldas": 0}; hac = dict(tot); q = n = 0
		for rival in RIVALES:
			for seed in (1, 2):
				c, h, quieto, total, m = medir(nombre, archivo, env, rival, seed)
				mov = max(1, sum(c.values()))
				print(f"{nombre:30} {rival:24} {100 * quieto / total:6.0f}% {100 * c['adelante'] / mov:8.0f}% "
				      f"{100 * c['costado'] / mov:7.0f}% {100 * c['espaldas'] / mov:8.0f}% | "
				      f"{100 * h['espaldas'] / max(1, sum(h.values())):25.0f}% | {m[0]}-{m[1]}", flush=True)
				for k in tot:
					tot[k] += c[k]; hac[k] += h[k]
				q += quieto; n += total
		mov = max(1, sum(tot.values()))
		print(f"{'  = TOTAL ' + nombre:55} {100 * q / n:6.0f}% {100 * tot['adelante'] / mov:8.0f}% {100 * tot['costado'] / mov:7.0f}% "
		      f"{100 * tot['espaldas'] / mov:8.0f}% | {100 * hac['espaldas'] / max(1, sum(hac.values())):25.0f}%\n", flush=True)


if __name__ == "__main__":
	main()
