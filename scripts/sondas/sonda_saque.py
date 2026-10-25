"""Sonda de saques (sesión 20): ¿por qué el equipo DL recibe goles de saque?

Juega el equipo DL (azul, izquierda) contra un rival headless y, en cada saque, mide quién toca
primero la pelota, dónde está nuestro keeper a 0,5 / 1 / 2 s y si el saque termina en gol en
menos de 3 s (a favor o en contra).

Uso: python scripts/sondas/sonda_saque.py <striker.npz> <keeper.npz> <rival> [segundos] [semilla]
     rival = nombre del módulo (soccer_team_DVF_v2, soccer_team_DVF, soccer_team_NormalTeam)
"""
import math, os, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
os.environ["DVF_DL_STRIKER"], os.environ["DVF_DL_KEEPER"] = sys.argv[1], sys.argv[2]
rival = sys.argv[3]
dur = float(sys.argv[4]) if len(sys.argv) > 4 else 300
seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
import numpy as np
import benchmark as B
random.seed(seed); np.random.seed(seed)
from game.engine import GameEngine
left = B._load_team(ROOT / "soccer_team_DVF_DL.py", "sl")
right = B._load_team(ROOT / f"{rival}.py", "sr")
eng = GameEngine(team_left=left, team_right=right, fps=B.FPS, match_duration_s=dur, headless=True)
pg = eng.playground
F = B.FPS
saques = []                              # uno por saque
cur = {}

def nuevo():
    cur.clear(); cur.update(t=0, first=None, k={}, s_dist1=None, gol=None)
    saques.append(cur.copy())

orig_reset = pg._apply_reset
def rst():
    orig_reset()
    if saques:
        saques[-1] = dict(cur)
    nuevo()
    j = 3.0                               # mismo ruido que el benchmark
    pg.ball.set_pos((B.BALL_CENTER[0] + random.uniform(-j, j), B.BALL_CENTER[1] + random.uniform(-j, j)))
pg._apply_reset = rst
rst()
orig_goal = pg.goalCallback
def on_goal(team):
    if cur["gol"] is None and cur["t"] < 3 * F:
        cur["gol"] = "favor" if team == "blue" else "contra"
    orig_goal(team)
pg.goalCallback = on_goal

players = {"nuestro striker": pg.striker_blue, "nuestro keeper": pg.keeper_blue,
           "su striker": pg.striker_purple, "su keeper": pg.keeper_purple}
while eng.running:
    eng.update_state()
    if not eng.is_blocked:
        pg.loop(); eng.space.step(1.0 / F)
        cur["t"] += 1
        bx, by = pg.ball.body.position; bv = pg.ball.body.velocity
        if cur["first"] is None and math.hypot(bv.x, bv.y) > 50:
            cur["first"] = min(players, key=lambda n: math.hypot(players[n].body.position.x - bx,
                                                                  players[n].body.position.y - by))
        for s in (0.5, 1.0, 2.0):
            if cur["t"] == int(s * F):
                cur["k"][s] = round(pg.keeper_blue.body.position.x)
        if cur["t"] == F:
            sp = pg.striker_blue.body.position
            cur["s_dist1"] = round(math.hypot(sp.x - bx, sp.y - by))
    eng.render(); eng.tick()
saques[-1] = dict(cur)
saques = [s for s in saques if s["t"] >= 3 * F or s["gol"]]
n = len(saques)
contra = [s for s in saques if s["gol"] == "contra"]
favor = [s for s in saques if s["gol"] == "favor"]
def cuenta(lst):
    out = {}
    for s in lst:
        out[s["first"]] = out.get(s["first"], 0) + 1
    return out
def med(lst, key):
    v = [s["k"].get(key) for s in lst if s["k"].get(key) is not None]
    return round(float(np.median(v))) if v else None
print(f"{rival}: {n} saques | gol en <3 s a favor {len(favor)}, en contra {len(contra)}")
print(f"  primer toque (todos): {cuenta(saques)}")
print(f"  primer toque (goles en contra): {cuenta(contra)}")
print(f"  keeper x mediana a 0,5/1/2 s: todos {med(saques, 0.5)}/{med(saques, 1.0)}/{med(saques, 2.0)}"
      f" | goles en contra {med(contra, 0.5)}/{med(contra, 1.0)}/{med(contra, 2.0)}  (spawn 418, línea de gol 127)")
d = [s["s_dist1"] for s in saques if s["s_dist1"] is not None]
print(f"  distancia striker-pelota a 1 s: mediana {np.median(d):.0f} px")
