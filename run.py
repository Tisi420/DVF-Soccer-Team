"""
Soccer Simulation — change the team imports below and run!

Controls:  F1 View  F2 PiP  F3 Reset  F4/F5 Camera  F6 Cinema  F7 Fullscreen  ESC Quit
"""

# =====================================================================
# TEAM SELECTION — change these imports to play your own team
import soccer_team_DVF as team_left          # left side (blue goal) - DVF Original (Turquesa)
import soccer_team_DVF_v2 as team_right     # right side (purple goal) - DVF v2 Optimizado (Dorado)

# DVF (2026-10-17): opcionalmente elegir los equipos por línea de comandos, sin editar este
# archivo (útil para jugar de los dos lados):
#   python run.py soccer_team_DVF_v2 soccer_team_DVF      -> izquierda, derecha
# Sin argumentos se usan los imports de arriba. No sirve para espejos (mismo módulo dos veces):
# para eso usar scripts/benchmark.py.
#
# DVF (2026-10-25, sesión 61): formato del torneo. Partidos de 1 min con GOL DE ORO si terminan
# empatados (la final, 3 min):
#   python run.py soccer_team_DVF_DL soccer_team_DVF_v2 --duracion 60 --gol-de-oro
#   python run.py soccer_team_DVF_DL soccer_team_DVF_v2 --duracion 180 --gol-de-oro   (final)
# Con --gol-de-oro, si al cumplirse --duracion hay empate, se sigue jugando hasta el próximo gol
# (tope --oro-max s, default 120). En la ventana el reloj solo corre con el juego activo: no cuenta
# celebraciones ni cuentas regresivas.
import sys, importlib, argparse, time
_ap = argparse.ArgumentParser(add_help=True)
_ap.add_argument("equipos", nargs="*", help="módulo izquierda y módulo derecha")
_ap.add_argument("--duracion", type=float, default=300, help="segundos de juego (default 300)")
_ap.add_argument("--gol-de-oro", action="store_true")
_ap.add_argument("--oro-max", type=float, default=120)
_args = _ap.parse_args()
if len(_args.equipos) == 2:
    team_left = importlib.import_module(_args.equipos[0])
    team_right = importlib.import_module(_args.equipos[1])

# =====================================================================
# MATCH SETTINGS
# =====================================================================
SCREEN_W, SCREEN_H = 1395, 880
FPS = 60
MATCH_DURATION_S = _args.duracion   # match length in seconds (0 = unlimited); DVF: --duracion
HEADLESS = False         # True = no window/sound, max-speed (for DL training)

# =====================================================================
# ENGINE SETUP (no need to modify below this line)
# =====================================================================
from game.engine import GameEngine
import pygame

engine = GameEngine(
    team_left=team_left,
    team_right=team_right,
    screen_size=(SCREEN_W, SCREEN_H),
    fps=FPS,
    match_duration_s=MATCH_DURATION_S,
    headless=HEADLESS,
)

# DVF (sesión 61): gol de oro. Mientras haya empate con el tiempo cumplido, se corre el final un
# segundo más en cada frame; con el primer gol vuelve la duración original y el motor termina el
# partido en ese mismo frame.
if _args.gol_de_oro and MATCH_DURATION_S > 0:
    _orig_tick = engine.tick
    _aviso = {"dado": False}

    def _tick_gol_de_oro():
        pg = engine.playground
        t = (engine._frame_count / FPS if HEADLESS
             else (time.time() - engine._start_time) - engine._match_time_offset)
        # +2 frames: el motor suma el frame y mira el reloj DESPUÉS de este chequeo
        if not engine._match_ended and t + 2.0 / FPS >= MATCH_DURATION_S:
            if pg.goal_counter_blue == pg.goal_counter_purple and t < MATCH_DURATION_S + _args.oro_max:
                if not _aviso["dado"]:
                    print(f"Empate {pg.goal_counter_blue}-{pg.goal_counter_purple} al terminar el tiempo: ¡GOL DE ORO!")
                    _aviso["dado"] = True
                engine._match_duration_s = t + 1.0
            else:
                engine._match_duration_s = MATCH_DURATION_S
        _orig_tick()

    engine.tick = _tick_gol_de_oro

# =====================================================================
# GAME LOOP
# =====================================================================
while engine.running:
    # 1. Handle keyboard & mouse input (F-keys, clicks, ESC)
    if not HEADLESS:
        for event in pygame.event.get():
            engine.handle_event(event)

    # 2. Advance game state machines (whistle countdown, celebrations, freeze)
    engine.update_state()

    # 3. Step physics + AI — skipped during countdowns and celebrations.
    #    YOUR TEAM CODE RUNS HERE: each player's default() is called,
    #    then pymunk resolves collisions and movement.
    if not engine.is_blocked:
        engine.playground.loop()        # calls striker.default() + keeper.default()
        engine.space.step(1.0 / FPS)    # pymunk physics step

    # 4. Render 3D scene, HUD, overlays → display
    engine.render()

    # 5. Cap framerate, check match duration
    engine.tick()

engine.cleanup()
