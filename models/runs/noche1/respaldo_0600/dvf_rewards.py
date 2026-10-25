"""
Recompensas del equipo DVF para el entrenamiento PPO (Deep Learning).

Origen: copia LITERAL de la celda de recompensa de "Soccer DeepLearning.ipynb" (2026-10-17),
para poder entrenar desde scripts/train_dl.py (los workers en paralelo necesitan importar
la función desde un módulo). Cada cambio posterior se marca con "DVF (fecha):" y se
registra en CHANGELOG.md.

    compute_reward = base_reward (dado por la cátedra) + refine_reward (nuestro ejercicio)

Cambios DVF (2026-10-17), verificados con una auditoría (políticas conocidas jugando como
agente) y casos sintéticos; detalle en CHANGELOG.md, sesión (8):
  1. FIX orientación: el frente del jugador es (sin a, -cos a). W_FACE_BALL y W_SHOOT_ALIGN
     usaban el eje lateral y premiaban ponerse de costado.
  2. W_FACE_BALL y W_SHOOT_ALIGN escalados por la velocidad propia (FACE_SPEED_REF), y
     W_SHOOT_ALIGN solo detrás de la pelota: antes un delantero QUIETO cobraba más que
     NormalTeam.
  3. KEEPER_STANDOFF 90 -> 160: el punto ideal del arquero quedaba dentro del arco.
  4. refine 2 (anti-freeze striker), refine 6 (esquinas) y refine 8 (trayectoria del keeper).
"""
import math

from game.keras_core import FIELD_W, FIELD_H   # en el notebook venían de "from setup_dl_notebook import *"

# ✏️ Reward weights — safe to change the magnitudes.
# The reward is split into two functions:
#   • base_reward   — the proven core (GIVEN, fully implemented). Trains a working team on its own.
#   • refine_reward — optional shaping (YOUR EXERCISE). Each term is a shell with a one-line hint;
#                     implement the ones you want, retrain, and watch the training curve.
#   • compute_reward = base_reward + refine_reward  (this is what training calls).

# --- Sparse goal signal (large, so scoring/conceding dominate everything else) ---
STRIKER_GOAL        = 20.0   # striker scores
KEEPER_SCORE_REW    = 3.0    # keeper's small share of a team goal
# No goal-conceded malus: a concede fires long after the mistake that caused it, on events the
# agent often can't control (high-variance, delayed credit assignment). Defence is learned from the
# keeper's positioning/save/intercept shaping instead; attack from the striker's shaping.

# --- Striker dense shaping (BASE; small weights so the goal reward stays dominant) ---
W_DRIBBLE     = 0.004  # be on the own-goal side of the ball (behind it) and close
W_FACE_BALL   = 0.001  # face the ball
W_SHOOT_ALIGN = 0.002  # face the enemy goal when near the ball
W_APP_DELTA   = 0.02   # got CLOSER to the ball this step (a delta, so it can't be farmed)
W_ADV_DELTA   = 0.5    # ball moved toward the enemy goal while striker near (position-based)
W_KICK_FWD    = 0.45   # a GENUINE forward strike (see the speed gate in the code)

# --- Keeper dense shaping (BASE) ---
W_KEEPER_LINE        = 0.8   # potential-based shot-line positioning (the keeper's main signal)
W_DANGER             = 0.008 # ball deep in our own zone
W_KEEPER_DEFLECT     = 1.0   # a GENUINE save (the keeper's main positive signal)
W_KEEPER_DEFLECT_FWD = 0.5   # bonus: the save also cleared the ball upfield

# --- Geometry constants ---
PROX_RADIUS    = 300.0  # striker dribble/advancement reward decays to 0 beyond this (px)
DRIBBLE_MARGIN = 200.0  # dribble reward caps at this distance behind the ball (px)
SHOOT_RADIUS   = 200.0  # shot-alignment bonus active only within this range (px)
GOAL_BLUE_X    = 31.0   # own goal x (blue / left team)
GOAL_CENTER_Y  = 442.0  # blue goal mouth centre — opening y ∈ [215, 669]
# DVF (2026-10-17): 90 -> 160. Con 90 el punto ideal quedaba en x = 31+90 = 121, DENTRO del
# arco (línea de gol x=127, gol con la pelota en x<117): enseñaba a pararse sobre la línea.
# Con 160 queda en x≈191 (≈65 px delante de la línea), cerca de donde se paran los arqueros
# rule-based, y el arco de radio 160 se mantiene entre los postes (y 282..602).
KEEPER_STANDOFF = 160.0  # px the keeper sits in front of the goal on the ball→goal line
DANGER_X       = 250.0  # ball x below this is dangerously close to our own goal
MAX_DIST       = 1649.0 # field diagonal — normalises distance deltas to [0, 1]
FACE_SPEED_REF = 200.0  # DVF: W_FACE_BALL paga completo recién a esta velocidad (px/s)


def base_reward(scored, conceded, role, player=None, ball=None, forward_sign=1.0,
                prev_ball_pos=None, prev_ball_vel=None, prev_dist=None, prev_player_pos=None):
    """
    BASE reward — sparse goal signal + bounded, non-farmable dense shaping. GIVEN, fully implemented.

    forward_sign    -- +1.0 for blue (enemy goal at +x), -1.0 for purple (enemy goal at -x).
    prev_ball_pos   -- (x, y) ball position at the start of this step  (delta rewards)
    prev_ball_vel   -- (vx, vy) ball velocity at the start of this step (save/strike detection)
    prev_dist       -- player-to-ball distance at the start of this step (approach delta)
    prev_player_pos -- (x, y) player position at the start of this step (keeper PBRS positioning)

    Why these terms are SAFE:
      • The two EVENT rewards (strike, save) fire only on the GENUINE event — a large speed jump
        toward goal, or a shot racing at our goal then stopped. They do NOT reward mere "contact":
        a "you touched the ball" bonus can be farmed by tapping the ball, which an agent will
        happily do instead of playing football.
      • Keeper positioning is POTENTIAL-BASED — it rewards the *reduction* in distance to the ideal
        spot, not the distance itself. That per-rollout sum telescopes to (start − end), so it is
        bounded and ~zero-mean: it guides behaviour without dumping a constant offset into value.
    """
    r = 0.0

    # --- Sparse goal signal ---
    if scored:   r += STRIKER_GOAL if role == 'striker' else KEEPER_SCORE_REW
    # (no goal-conceded malus — see the note above; defence/attack are learned from shaping)
    if scored or conceded:
        return r  # goal frames carry the sparse signal only — keep it clean

    r -= 0.001  # small time penalty — prefer shorter paths to a goal

    if player is None or ball is None:
        return r

    px   = player.body.position.x
    py   = player.body.position.y
    bx   = ball.body.position.x
    by   = ball.body.position.y
    ang  = player.body.angle
    dist = math.hypot(bx - px, by - py)

    if role == 'striker':

        # Get BEHIND the ball (own-goal side) and stay close — sets up controlled forward play.
        behind_margin = (bx - px) * forward_sign
        if behind_margin > 0.0 and dist < PROX_RADIUS:
            behind_factor = min(behind_margin / DRIBBLE_MARGIN, 1.0)
            r += W_DRIBBLE * behind_factor * (1.0 - dist / PROX_RADIUS)

        # DVF (2026-10-17) FIX: en este motor el FRENTE del jugador es (sin a, -cos a), es decir
        # body.angle - 90° (ver Playground.calc_single_entity_view: sector 3 = ángulo 0;
        # azul arranca con angle=90° mirando a +x). El original usaba (cos a, sin a), que es el
        # eje LATERAL derecho: pagaba con la pelota a la derecha (sector 7) y 0 con la pelota
        # adelante, y el bonus de tiro pagaba mirando hacia arriba (-y) y 0 mirando al arco.
        # Probado en scratch/reward_probe.py. Ambos términos enseñaban a ponerse de costado.
        fx, fy = math.sin(ang), -math.cos(ang)

        # Face the ball (dot of facing vector with direction-to-ball; only when positive).
        # DVF (2026-10-17): escalado por la velocidad propia. Ya corregido el frente, un
        # delantero QUIETO mirando la pelota cobraba 0.001/paso (+2.7 en 180 s, más que
        # NormalTeam en la auditoría): un atractor para "congelarse". Ahora paga correr
        # mirando la pelota.
        if dist > 1.0:
            align = (fx * (bx - px) + fy * (by - py)) / dist
            spd = math.hypot(player.body.velocity.x, player.body.velocity.y)
            r += W_FACE_BALL * max(0.0, align) * min(spd / FACE_SPEED_REF, 1.0)

        # Face the enemy goal when close enough to shoot.
        # DVF (2026-10-17): además, solo DETRÁS de la pelota (lado propio) y en movimiento. En la
        # auditoría era el término denso más grande y un delantero QUIETO cobraba +4.48 en 180 s
        # (v2.3: +4.78): bastaba con mirar al arco cuando la pelota pasaba cerca.
        if dist < SHOOT_RADIUS and behind_margin > 0.0:
            spd = math.hypot(player.body.velocity.x, player.body.velocity.y)
            r += W_SHOOT_ALIGN * max(0.0, fx * forward_sign) * min(spd / FACE_SPEED_REF, 1.0)

        # Approach delta — reward getting closer to the ball. A delta (not raw distance) so the
        # agent is rewarded for *pursuing*; it can't sit at a fixed radius to farm it.
        if prev_dist is not None:
            r += W_APP_DELTA * (prev_dist - dist) / MAX_DIST

        # Ball advancement — reward the ball actually moving toward the enemy goal while the
        # striker is near. Position-based, so rapid taps can't farm it: only net displacement counts.
        if prev_ball_pos is not None and dist < PROX_RADIUS:
            adv = (bx - prev_ball_pos[0]) * forward_sign / FIELD_W
            r += W_ADV_DELTA * max(0.0, adv)

        # GENUINE forward strike — a large single-step speed jump leaving the ball moving fast
        # toward the enemy goal. A series of small taps can't fake a big Δspeed, so this rewards
        # real kicks/shots, not dribble-farming.
        if prev_ball_vel is not None and dist < 80.0:
            prev_spd = math.hypot(prev_ball_vel[0], prev_ball_vel[1])
            curr_spd = math.hypot(ball.body.velocity.x, ball.body.velocity.y)
            if curr_spd > prev_spd + 150.0 and curr_spd > 200.0 and ball.body.velocity.x * forward_sign > 0.0:
                r += W_KICK_FWD

    else:  # keeper

        # POTENTIAL-BASED shot-line positioning. The ideal spot is on the line from the ball to the
        # goal centre, KEEPER_STANDOFF px in front of the goal mouth (Y-aware → covers angled shots).
        # We reward the REDUCTION in distance to that spot; the per-rollout sum telescopes to
        # (start_error − end_error): bounded and ~zero-mean.
        gx, gy = bx - GOAL_BLUE_X, by - GOAL_CENTER_Y
        gdist = math.hypot(gx, gy)
        if gdist > 1.0:
            ideal_px = GOAL_BLUE_X + KEEPER_STANDOFF * gx / gdist
            ideal_py = GOAL_CENTER_Y + KEEPER_STANDOFF * gy / gdist
        else:
            ideal_px, ideal_py = GOAL_BLUE_X + KEEPER_STANDOFF, GOAL_CENTER_Y
        pos_err = math.hypot(px - ideal_px, py - ideal_py)
        if prev_player_pos is not None and prev_ball_pos is not None:
            pgx, pgy = prev_ball_pos[0] - GOAL_BLUE_X, prev_ball_pos[1] - GOAL_CENTER_Y
            pgd = math.hypot(pgx, pgy)
            if pgd > 1.0:
                pip_x = GOAL_BLUE_X + KEEPER_STANDOFF * pgx / pgd
                pip_y = GOAL_CENTER_Y + KEEPER_STANDOFF * pgy / pgd
            else:
                pip_x, pip_y = GOAL_BLUE_X + KEEPER_STANDOFF, GOAL_CENTER_Y
            prev_pos_err = math.hypot(prev_player_pos[0] - pip_x, prev_player_pos[1] - pip_y)
            r += W_KEEPER_LINE * (prev_pos_err - pos_err) / MAX_DIST

        # Mild bounded penalty for the ball being deep in our own zone.
        if bx < DANGER_X:
            r -= W_DANGER * (1.0 - bx / DANGER_X)

        # GENUINE save — the ball was racing AT our goal, then got stopped or reversed after the
        # keeper made contact. Gated on the real event, so it can't be farmed by bumping the ball.
        if prev_ball_vel is not None and dist < 80.0:
            if (prev_ball_vel[0] * forward_sign) < -80.0:                # ball was racing at our goal
                prev_spd    = math.hypot(prev_ball_vel[0], prev_ball_vel[1])
                curr_spd    = math.hypot(ball.body.velocity.x, ball.body.velocity.y)
                curr_vx_fwd = ball.body.velocity.x * forward_sign
                if curr_vx_fwd > 0.0 or curr_spd < prev_spd - 30.0:     # reversed or killed
                    r += W_KEEPER_DEFLECT
                    if curr_vx_fwd > 0.0:
                        r += W_KEEPER_DEFLECT_FWD                       # cleared it back upfield

    return r


# --- DVF (2026-10-17): pesos de los refine implementados (todos chicos frente al +20 del gol) ---
W_ANTI_FREEZE  = 0.0005  # refine 2: striker, por paso, proporcional a |v|/400 (no "estacionarse")
W_CORNER       = 0.003   # refine 6: striker, castigo por paso con pelota lenta en una esquina
CORNER_ZONE    = 160.0   # px desde ambos bordes = esquina (igual que ball_in_corner del entrenamiento)
CORNER_SLOW    = 60.0    # px/s: por debajo, la pelota "está quieta" en la esquina
W_KEEPER_TRAJ  = 0.8     # refine 8: keeper, potencial hacia el punto donde cruza el tiro
TRAJ_MIN_VX    = 80.0    # px/s hacia nuestro arco para considerar que es un tiro
GOAL_Y_TOP, GOAL_Y_BOT = 215.0, 669.0   # boca del arco (Playground.GOAL_Y_TOP/BOT)


def _shot_target(ball_pos, ball_vel, forward_sign):
    """refine 8: punto (x, y) donde un tiro hacia nuestro arco cruza la línea del arquero.

    None si la pelota no viene hacia el arco (vx hacia atrás < TRAJ_MIN_VX) o ya pasó la línea.
    Sin rebotes en las paredes; 'y' se recorta a la boca del arco (con margen del cuerpo).
    """
    bx, by = ball_pos
    vx, vy = ball_vel
    line_x = GOAL_BLUE_X + KEEPER_STANDOFF
    if vx * forward_sign > -TRAJ_MIN_VX or bx <= line_x:
        return None
    y = by + vy * (line_x - bx) / vx
    return line_x, min(max(y, GOAL_Y_TOP + 35.0), GOAL_Y_BOT - 35.0)


def refine_reward(role, player=None, ball=None, forward_sign=1.0,
                  prev_ball_pos=None, prev_dist=None, opponent=None, prev_ball_vel=None,
                  prev_player_pos=None):
    """
    REFINE reward — YOUR EXERCISE. Optional shaping layered on top of the proven BASE. BASE already
    trains a working team; these refinements push it from "plays" to "strong".

    Implement the terms you want below (start with ONE, retrain, look at the training curve — entropy
    should keep falling, reward rising). Keep every weight SMALL relative to the +20 goal reward, and
    make each term either EVENT-BOUNDED (fires only on a genuine event) or a bounded delta — copy the
    pattern from the BASE event/potential terms above so nothing can be farmed by hovering or tapping.
    """
    if player is None or ball is None:
        return 0.0
    r = 0.0
    px = player.body.position.x;  py = player.body.position.y
    bx = ball.body.position.x;    by = ball.body.position.y
    dist = math.hypot(bx - px, by - py)

    if role == 'striker':
        # TODO (refine 1) CHASE — reward velocity pointed AT the ball: project the player's velocity
        #   onto the unit vector to the ball, keep only the positive part, normalise by max speed (400).
        # TODO (refine 2) ANTI-FREEZE — small reward proportional to the player's speed |velocity|,
        #   so the policy never settles into standing still.
        # TODO (refine 3) STANCE — bonus when BEHIND the ball (own-goal side) AND facing the enemy goal.
        # TODO (refine 4) ADVANCE-TO-CENTRE — reward the ball getting closer to the enemy-goal CENTRE
        #   (enemy-side x, mid field height); use a telescoping (prev_d - d) delta so it stays bounded.
        # TODO (refine 5) STRIKE-AT-CENTRE — BIG one-off reward for a genuine kick (large Δspeed, like
        #   W_KICK_FWD) aimed at that centre; scale by aim quality = cos(angle of ball velocity to centre).
        # TODO (refine 6) CORNER MALUS — small per-step penalty while a SLOW ball idles in a corner.

        # DVF (2026-10-17) refine 2 ANTI-FREEZE: el equipo DL tiende a "congelarse" y el delantero
        # rule-based ya tuvo ese bug (colgado). Por paso, acotado a W_ANTI_FREEZE: muy por debajo
        # del delta de acercamiento, así correr en círculos no compensa.
        spd = math.hypot(player.body.velocity.x, player.body.velocity.y)
        r += W_ANTI_FREEZE * min(spd / 400.0, 1.0)

        # DVF (2026-10-17) refine 6 CORNER MALUS: en la ventana los equipos se traban mucho en
        # las esquinas (sobre todo abajo a la derecha). En el entrenamiento una esquina trabada
        # solo reinicia la pelota a los ~3 s (stuck_ball_step) sin costo: acá pasa a costar.
        in_corner = ((bx < CORNER_ZONE or bx > FIELD_W - CORNER_ZONE) and
                     (by < CORNER_ZONE or by > FIELD_H - CORNER_ZONE))
        if in_corner and math.hypot(ball.body.velocity.x, ball.body.velocity.y) < CORNER_SLOW:
            r -= W_CORNER
    else:  # keeper
        # TODO (refine 7) INTERCEPT — reward closing the distance on a ball moving toward our goal
        #   (only when the ball's forward-velocity points at us; use a bounded distance delta).
        # TODO (refine 8) TRAJECTORY — predict where the incoming shot crosses the keeper's line
        #   (y at x = own_goal_x + standoff, from the ball velocity), then reward the REDUCTION in the
        #   keeper's distance to that point (a delta) — NOT raw proximity, or a parked keeper farms it.
        # TODO (refine 9) ANTI-FREEZE — small reward for the keeper keeping speed up (don't park).
        # TODO (refine 10) CLEARANCE — reward a genuine kick (big Δspeed) that sends the ball AWAY
        #   from our goal while it is in OUR OWN HALF (proactively clear danger upfield, not just save).

        # DVF (2026-10-17) refine 8 TRAJECTORY: con un tiro en camino, premiar la REDUCCIÓN de la
        # distancia al punto donde el tiro cruza la línea del arquero (potencial, como
        # W_KEEPER_LINE: la suma se telescopa, no se puede "farmear" quedándose quieto).
        # Solo si el tiro ya venía en el paso anterior y sigue viniendo (mismo evento).
        if prev_ball_pos is not None and prev_ball_vel is not None and prev_player_pos is not None:
            tgt_prev = _shot_target(prev_ball_pos, prev_ball_vel, forward_sign)
            tgt_now = _shot_target((bx, by), (ball.body.velocity.x, ball.body.velocity.y), forward_sign)
            if tgt_prev is not None and tgt_now is not None:
                err_prev = math.hypot(prev_player_pos[0] - tgt_prev[0], prev_player_pos[1] - tgt_prev[1])
                err_now = math.hypot(px - tgt_now[0], py - tgt_now[1])
                r += W_KEEPER_TRAJ * (err_prev - err_now) / MAX_DIST
    return r


def compute_reward(scored, conceded, role, player=None, ball=None, forward_sign=1.0,
                   prev_ball_pos=None, prev_ball_vel=None, prev_dist=None, prev_player_pos=None,
                   opponent=None):
    """Full reward = BASE + REFINE (your refinements). This is what training calls each step."""
    r = base_reward(scored, conceded, role, player, ball, forward_sign,
                    prev_ball_pos, prev_ball_vel, prev_dist, prev_player_pos)
    if scored or conceded:
        return r  # goal frames carry the sparse signal only
    # DVF (2026-10-17): también se pasa prev_player_pos (lo necesita el refine 8 del arquero)
    r += refine_reward(role, player, ball, forward_sign, prev_ball_pos, prev_dist, opponent, prev_ball_vel,
                       prev_player_pos)
    return r
