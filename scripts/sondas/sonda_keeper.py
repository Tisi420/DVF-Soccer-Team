"""Sonda: ¿qué hace el keeper DL en partido? Posición, 'atajadas' según dvf_rewards, goles.

Uso: python probe_keeper.py <striker.npz> <keeper.npz> [segundos]
Juega DL (azul, izquierda) vs NormalTeam headless y mide el keeper azul.
"""
import math, os, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent   # sesión 19: scripts/sondas/ -> raíz
os.chdir(ROOT); sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
os.environ["DVF_DL_STRIKER"], os.environ["DVF_DL_KEEPER"] = sys.argv[1], sys.argv[2]
dur = float(sys.argv[3]) if len(sys.argv) > 3 else 180
import numpy as np
import benchmark as B
random.seed(1); np.random.seed(1)
from game.engine import GameEngine
left = B._load_team(ROOT / "soccer_team_DVF_DL.py", "pl")
right = B._load_team(ROOT / "soccer_team_NormalTeam.py", "pr")
eng = GameEngine(team_left=left, team_right=right, fps=B.FPS, match_duration_s=dur, headless=True)
pg = eng.playground
k = pg.keeper_blue
xs, far, saves, saves_far, frames = [], 0, 0, 0, 0
since = {"t": 0}
kick_x = []
orig = pg._apply_reset
def rst():
    orig(); since["t"] = 0
pg._apply_reset = rst
prev_v = None
while eng.running:
    eng.update_state()
    if not eng.is_blocked:
        pg.loop(); eng.space.step(1.0 / B.FPS)
        frames += 1; since["t"] += 1
        kx, ky = k.body.position; bx, by = pg.ball.body.position
        bv = pg.ball.body.velocity
        xs.append(kx)
        if kx > 400: far += 1
        if since["t"] == 2 * B.FPS: kick_x.append(kx)
        if prev_v is not None and math.hypot(bx - kx, by - ky) < 80 and prev_v[0] < -80:
            ps, cs = math.hypot(*prev_v), math.hypot(bv.x, bv.y)
            if bv.x > 0 or cs < ps - 30:
                saves += 1
                if kx > 400: saves_far += 1
        prev_v = (bv.x, bv.y)
    eng.render(); eng.tick()
xs = np.array(xs)
print(f"marcador DL {pg.goal_counter_blue} - {pg.goal_counter_purple} NT | keeper x: mediana {np.median(xs):.0f}, "
      f"p90 {np.percentile(xs, 90):.0f}, lejos(x>400) {100 * far / frames:.0f}% | 'atajadas' {saves} "
      f"({saves_far} lejos del arco) | keeper x a 2 s del saque: {np.median(kick_x) if kick_x else float('nan'):.0f}")
