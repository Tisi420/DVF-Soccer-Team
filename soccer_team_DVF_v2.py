"""
================================================================================
Robotic Soccer - Rule-Based Agent: DVF v2 (Optimized Version)
================================================================================
Team Members: Diego, Valentino, Fernando
Course: Robotic Motions / Machine Learning Soccer Tournament
University: Reutlingen University

Overview:
    Optimized rule-based soccer team building upon the original DVF state-machine.
    Implements targeted mechanical and tactical improvements designed to eliminate
    common failure modes in simulated 2v2 physics:
    
Key Optimizations:
    1. Anti-Autogol with Wall Awareness (Striker):
       Prevents rushing forward toward own net when friendly goal is in FRONT
       or enemy goal is in BACK. Selects lateral detour based on Y coordinates
       relative to top/bottom walls (FIELD_H = 880 px) to avoid wall trapping.
    2. Post-Bound Goalkeeping (Keeper):
       Restricts lateral strafing strictly within goal posts (Y in [265, 615] px),
       preventing the keeper from wandering off to corner flags.
    3. Reactive Stall Escape (Striker):
       Instantly aborts multi-phase escape maneuvers if ball distance changes by
       >75 px (indicating the ball was cleared or freed).
    4. Goal Line Protection (Keeper):
       Eliminates dangerous blind backpedaling when ball is near or behind goal line.
    5. Adaptive Kickoff Defense (_TeamTactics):
       Monitors quick concession loops (<4s per goal) and triggers emergency
       repositioning at kickoff: keeper retreats instantly to center goal mouth,
       striker blocks direct center shooting lane.

Changelog:
    - v2.0.0: Optimized version (items 1-5 above).
    - v2.1.0 (2026-10-17): FIX side-dependent movement.
        * Keeper: lateral tracking used absolute up/down moves, which assumed
          "ball in left sectors" == -Y. True only for blue; the purple keeper
          strafed AWAY from the ball. Now tracks with relative move_left/right
          (like v1) and applies the post limits per real heading.
        * move_upfield/move_downfield now use the real body angle instead of
          the team color, so the striker's anti-autogol detour and kickoff
          defense move in the intended direction after turning.
    - (2026-10-17) Tried and REVERTED: keeper "kickoff guard" (center on the
      goal at every kickoff). It made kickoff concessions worse in jittered
      tests (39/200 vs 22/200 as blue). Details in CHANGELOG.md. Do not retry
      without a new idea.
    - v2.2.0 (2026-10-17): FIX striker "hanging" in the enemy half.
        * The anti-autogol check ran BEFORE the "ball far -> run at it" step and at
          any distance. With the ball between the striker and its own goal (time
          to defend) it refused to move forward and only strafed, sometimes
          oscillating at Y=220 (17-25 episodes of >=3 s per match -> 0).
        * Now: ball far -> run at it; anti-autogol only near the ball, orbiting it
          (strafe + approach to FORWARD_MIN_DIST) with a wall-aware side
          (_orbit_side, WALL_MARGIN, ORBIT_LOCK_TICKS) instead of fixed Y rules.
    - v2.3.0 (2026-10-17): Kickoff play (Striker._kickoff_play).
        * Without noise the kickoff is a deterministic race that the right side
          always won. At every kickoff the striker now turns to face the enemy goal
          centre and strafes onto the ball line (Y=440) while running forward,
          hitting the ball square. It ends when the ball moves away (contact).
        * Kickoff goals conceded: 2.4 -> 0.2 per match (noise), 100% -> 0% as left
          side (no noise). Net vs v1 +2.1 -> +5.6, vs v2.2 +3.4. Note: it has
          priority over the striker part of the "defense after quick goal" mode.
    - (2026-10-17) Tried, NOT adopted: v2.4 "wall play" (push the ball along the
      side wall near corners). Corner-stall time did not drop (remaining stalls are
      balls wedged by wall + chamfer + enemy keeper); head-to-head vs v2.3 was a tie.
      Kept in experimentos/soccer_team_DVF_v24_banda.py. Details in CHANGELOG.md.
================================================================================
"""

import math
from game.player import Player

# Entitäten-Dictionary
obj_dict = {
	"ball": 0,
	"goal_friendly": 1,
	"goal_enemy": 2,
	"wall": 3,
	"player_friendly": 4,
	"player_enemy_striker": 5,
	"player_enemy_keeper": 6
}

# Sichtfelder (10 Sektoren, 3 = genau vorne, 8 = genau hinten)
LEFT = [0, 1, 2]
RIGHT = [4, 5, 6]
FRONT = [2, 3, 4]
BACK = [7, 8, 9]

# Dimensiones de la cancha y arco para límites seguros
FIELD_H = 880.0
POST_TOP_Y = 265.0      # Límite superior del arco (con margen de seguridad)
POST_BOTTOM_Y = 615.0   # Límite inferior del arco
LATERAL_MIN_DY = 0.3    # v2.1: por debajo de esto un paso lateral no mueve al jugador en Y


class _Sensors:
	"""Gemeinsame Sensor-Helfer für Striker und Keeper."""

	def sector_of(self, entity):
		"""Sektor (0-9), in dem die Entität gesehen wird (None = nicht gesehen)."""
		for i in range(10):
			if self.view_field[i][obj_dict[entity]] > 0:
				return i
		return None

	def dist_of(self, entity):
		"""Distanz in px zur Entität (1000000 = nicht gesehen)."""
		for i in range(10):
			d = self.view_field[i][obj_dict[entity]]
			if d > 0:
				return d
		return 1000000

	def ball_sector(self):
		return self.sector_of("ball")

	def ball_dist(self):
		return self.dist_of("ball")

	def own_goal_sector(self):
		return self.sector_of("goal_friendly")

	def own_goal_dist(self):
		return self.dist_of("goal_friendly")

	def enemy_goal_sector(self):
		return self.sector_of("goal_enemy")

	def enemy_goal_dist(self):
		return self.dist_of("goal_enemy")

	def turn_towards(self, sector):
		"""Dreht den Spieler so, dass 'sector' nach vorne (3) wandert."""
		if sector is None or sector == 3:
			return
		if sector in (0, 1, 2, 9):      # links
			self.turn_left()
		elif sector in (4, 5, 6):       # rechts
			self.turn_right()
		elif sector in (7, 8):          # hinten rechts / hinten
			self.turn_right()

	# FIX v2.1 (2026-10-17): antes move_downfield/move_upfield elegían move_right/move_left
	# según el color del equipo, lo que solo es correcto con la orientación inicial
	# (azul mirando +X, violeta mirando -X). Ahora se calcula con el ángulo real del cuerpo
	# (solo lectura, el anti-exploit no lo revierte).
	def _strafe_dy(self, side):
		"""Componente Y (mundo) de un paso lateral 'right'/'left' con la orientación actual.

		move_right empuja sobre el eje +x local, que en el mundo es (cos a, sin a).
		Devuelve un valor en [-1, 1]: >0 = el paso baja en pantalla (+Y), <0 = sube (-Y).
		"""
		dy = math.sin(self.body.angle)
		return dy if side == "right" else -dy

	def _move_world_y(self, sign):
		"""Paso lateral hacia +Y (sign=+1) o -Y (sign=-1) en coordenadas de la cancha."""
		dy = self._strafe_dy("right")
		if abs(dy) < LATERAL_MIN_DY:
			return  # mirando a lo largo del eje Y: un paso lateral casi no cambia Y
		if dy * sign > 0:
			self.move_right()
		else:
			self.move_left()

	def move_downfield(self):
		"""Mueve al jugador hacia +Y (abajo en la pantalla), según su orientación real."""
		self._move_world_y(+1)

	def move_upfield(self):
		"""Mueve al jugador hacia -Y (arriba en la pantalla), según su orientación real."""
		self._move_world_y(-1)

	@staticmethod
	def get_team_appearance() -> dict:
		"""Color dorado/ambar para diferenciar a la v2 en el partido de prueba."""
		return {
			"color": (1.00, 0.80, 0.10),   # Gold / Amber
			"label": "V2",
			"shape": "cone",
			"height": 52.0,
			"radius": 24.0,
		}


ORBIT_DIST = 160        # erst unterhalb dieser Ballentfernung wird der Ball umkreist
FORWARD_MIN_DIST = 90   # beim Umkreisen des Balls erst ab diesem Abstand zusätzlich vorwärts
MATE_DIST = 130         # Abstand, ab dem der Striker dem Torwart ausweicht
STALL_TICKS = 90        # so lange ohne Fortschritt = Blockade (~1.5 s)
PUSH_STALL_TICKS = 120  # so lange gegen Wand/Ecke schieben = Blockade (~2 s)
BACK_TICKS = 40         # Phase 1 des Befreiungs-Manövers: zurücksetzen
DETOUR_TICKS = 50       # Phase 2: seitlich am Hindernis vorbei
CHARGE_TICKS = 60       # Phase 3: mit Anlauf auf den Ball
ESCAPE_TICKS = BACK_TICKS + DETOUR_TICKS + CHARGE_TICKS
WALL_MARGIN = 220       # v2.2: a menos de esto de un borde (Y) no orbitar hacia la pared
ORBIT_LOCK_TICKS = 60   # v2.2: tras cambiar de lado por la pared, mantenerlo ~1 s

# v2.3 (2026-10-17): jugada de saque del delantero (ver Striker._kickoff_play).
KICKOFF_PLAY_TICKS = 120          # duración máxima de la jugada (~2 s)
KICKOFF_AIM_Y = 440.0             # Y de la pelota en el saque = centro de la boca del arco
KICKOFF_ALIGN_TOL = 6.0           # px: tolerancia para considerarse alineado con la pelota
KICKOFF_TURN_TOL = math.radians(2)  # tolerancia de orientación hacia el arco rival
# Apuntar esta distancia (Y) lejos del spawn del arquero rival. Probado 0/80/130/180 px:
# 0 (centro) es lo mejor; con otros valores se pierden los goles de saque de violeta.
KICKOFF_SHOT_OFFSET = 0.0
ENEMY_GOAL_X = {"blue": 1368.0, "purple": 31.0}   # fondo del arco rival según el color


class _TeamTactics:
	quick_goals_conceded = 0
	play_ticks = 0
	defense_kickoff_ticks = 0
	kickoff_play_ticks = 0       # v2.3: >0 mientras dura la jugada de saque
	last_spawn_tick = -100
	current_tick = 0
	shot_timer = 0

	@classmethod
	def tick(cls, player):
		px = player.body.position.x
		py = player.body.position.y
		vx = player.body.velocity.x
		vy = player.body.velocity.y

		if cls.shot_timer > 0:
			cls.shot_timer -= 1

		# Detección de reinicio/saque en el centro
		is_spawn = (
			((abs(px - 418.5) < 12) and (abs(py - 528.0) < 12 or abs(py - 352.0) < 12)) or
			((abs(px - 976.5) < 12) and (abs(py - 528.0) < 12 or abs(py - 352.0) < 12))
		) and (math.hypot(vx, vy) < 10)

		if is_spawn and (cls.current_tick - cls.last_spawn_tick > 40):
			# Si la jugada duró menos de 4s (240 ticks):
			# Si nuestro delantero pateó al arco en los últimos instantes -> ¡GOL A FAVOR!
			# Si NO pateamos al arco -> ¡GOL EN CONTRA!
			we_scored = (cls.shot_timer > 0)
			if 0 < cls.play_ticks < 240 and not we_scored:
				cls.quick_goals_conceded += 1
			else:
				cls.quick_goals_conceded = 0

			cls.last_spawn_tick = cls.current_tick
			cls.play_ticks = 0
			cls.shot_timer = 0

			# Solo si nos metieron gol de salida en contra, activamos repliegue defensivo
			if cls.quick_goals_conceded >= 1:
				cls.defense_kickoff_ticks = 90  # 1.5s de bloqueo defensivo

			# v2.3: en cada saque el delantero ejecuta la jugada de saque
			cls.kickoff_play_ticks = KICKOFF_PLAY_TICKS
		else:
			cls.play_ticks += 1
			if cls.defense_kickoff_ticks > 0:
				cls.defense_kickoff_ticks -= 1
			if cls.kickoff_play_ticks > 0:
				cls.kickoff_play_ticks -= 1

		cls.current_tick += 1

	@classmethod
	def is_defense_active(cls):
		return cls.defense_kickoff_ticks > 0

	@classmethod
	def is_kickoff_play(cls):
		"""v2.3: True mientras dura la jugada de saque del delantero."""
		return cls.kickoff_play_ticks > 0

	@classmethod
	def end_kickoff_play(cls):
		cls.kickoff_play_ticks = 0


class Striker(_Sensors, Player):

	def __init__(self):
		super().__init__(task="striker")
		self._ball_hist = []
		self._goal_hist = []
		self._escape = 0
		self._escape_side = "right"
		self._escape_start_dist = 0
		self._orbit_lock = 0                # v2.2: ticks restantes con el lado de órbita fijo
		self._orbit_locked_side = "right"
		self._kick_prev_d = None            # v2.3: distancia a la pelota en el tick anterior

	def default(self):
		_TeamTactics.tick(self)
		# v2.3: jugada de saque. Tiene prioridad sobre el repliegue defensivo de saque.
		if _TeamTactics.is_kickoff_play():
			d = self.ball_dist()
			if self._kick_prev_d is not None and d > self._kick_prev_d + 3:
				# La pelota se aleja: ya hubo contacto (nuestro o del rival) -> juego normal
				_TeamTactics.end_kickoff_play()
				self._kick_prev_d = None
			else:
				self._kick_prev_d = d
				self._kickoff_play()
				return
		else:
			self._kick_prev_d = None
		if _TeamTactics.is_defense_active():
			# Reposicionamiento defensivo en kickoff: cortar la línea de tiro central
			self.turn_towards(self.ball_sector())
			self.move_forward()
			py = self.body.position.y
			if py > 460:
				self.move_upfield()
			elif py < 420:
				self.move_downfield()
			return
		# OPTIMIZACIÓN 3: Desatasco reactivo.
		# Si la pelota se movió bruscamente (alguien la pateó o rebotó lejos), abortamos el escape inmediatamente.
		if self._escape > 0:
			curr_d = self.ball_dist()
			if abs(curr_d - self._escape_start_dist) > 75.0:
				self._escape = 0  # Pelota liberada -> volver a jugar ya mismo
			else:
				self._escape -= 1
				self.turn_towards(self.ball_sector())
				if self._escape >= DETOUR_TICKS + CHARGE_TICKS:
					self.move_back()
				elif self._escape >= CHARGE_TICKS:
					self.move_forward()
					self._strafe(self._escape_side)
				else:
					self.move_forward()
				return

		self._attack()
		self._avoid_teammate()
		self._watch_stall()

	def _mate_side(self):
		return self.sector_of("player_friendly"), self.dist_of("player_friendly")

	def _strafe(self, side):
		mate, mate_d = self._mate_side()
		if mate_d < MATE_DIST:
			if side == "right" and mate in (4, 5, 6):
				side = "left"
			elif side == "left" and mate in (0, 1, 2):
				side = "right"
		if side == "right":
			self.move_right()
		else:
			self.move_left()

	def _kickoff_play(self):
		"""v2.3: jugada de saque — llegar a la pelota mirando al centro del arco rival.

		Sin ruido el saque es una carrera determinista: los dos delanteros llegan casi a la
		vez y gana siempre el mismo lado. v1/v2.2 avanzan en línea recta (la pelota está en
		el sector 3, ~17° fuera del eje) y después frenan para girar, en una curva lenta.
		Acá, en cambio:
		  1) se gira hasta mirar exactamente al centro del arco rival (x de fondo, Y=440);
		     el frente del cuerpo empuja la pelota en esa dirección;
		  2) mientras se avanza a fondo, paso lateral hasta quedar en la línea de la pelota
		     (Y=440), así se la golpea de frente y sale derecho al arco.
		La pelota del saque está siempre en (697.5, 440); la orientación se calcula con
		body.position / body.angle (solo lectura).
		"""
		px, py = self.body.position
		team = getattr(self, "team", "blue")
		gx = ENEMY_GOAL_X.get(team, 1368.0)
		# Punto de tiro: lejos de donde arranca el arquero rival (el motor lo pone en Y=528 si
		# es violeta y en Y=352 si es azul), para que un tiro al centro no le pegue de frente.
		aim_y = KICKOFF_AIM_Y - KICKOFF_SHOT_OFFSET if team == "blue" else KICKOFF_AIM_Y + KICKOFF_SHOT_OFFSET
		# 1) Orientación: el frente del jugador es body.angle - 90°
		face = math.atan2(aim_y - py, gx - px)
		err = (face + math.pi / 2 - self.body.angle + math.pi) % (2 * math.pi) - math.pi
		if err > KICKOFF_TURN_TOL:
			self.turn_right()           # turn_right aumenta body.angle
		elif err < -KICKOFF_TURN_TOL:
			self.turn_left()
		# 2) Alinearse con la línea de la pelota mientras se avanza
		dy = KICKOFF_AIM_Y - py
		if abs(dy) > KICKOFF_ALIGN_TOL:
			self._move_world_y(1 if dy > 0 else -1)
		self.move_forward()

	def _orbit_side(self, goal):
		"""v2.2: lado ('left'/'right') para rodear la pelota sin ir contra la pared.

		Por defecto se elige según dónde está el arco rival, como en el resto del ataque.
		Si ese paso lateral lleva hacia una pared cercana (WALL_MARGIN), se cambia de lado y
		se mantiene ORBIT_LOCK_TICKS para no oscilar en el borde (antes se trababa en Y=220).
		"""
		if self._orbit_lock > 0:
			return self._orbit_locked_side
		side = "left" if goal in (5, 6, 7) else "right"
		dy = self._strafe_dy(side)
		py = self.body.position.y
		if (py < WALL_MARGIN and dy < 0) or (py > FIELD_H - WALL_MARGIN and dy > 0):
			side = "left" if side == "right" else "right"
			self._orbit_locked_side = side
			self._orbit_lock = ORBIT_LOCK_TICKS
		return side

	def _attack(self):
		ball = self.ball_sector()
		goal = self.enemy_goal_sector()
		if self._orbit_lock > 0:
			self._orbit_lock -= 1

		if ball is None:
			self.turn_left()
			return

		# 1) Orientarse a la pelota
		self.turn_towards(ball)

		# 2) Si la pelota no está al frente, priorizar girar
		if ball not in FRONT:
			return

		# 3) Pelota lejos -> avanzar directo.
		# FIX v2.2 (2026-10-17): este paso iba DESPUÉS del anti-autogol, que se aplicaba a
		# cualquier distancia. Con la pelota entre el delantero y su propio arco (justo
		# cuando hay que volver a defender) se negaba a avanzar y solo se movía de costado,
		# a veces oscilando en Y=220: 17-25 episodios de >=3 s "colgado" por partido.
		if self.ball_dist() > ORBIT_DIST:
			self.move_forward()
			return

		# OPTIMIZACIÓN 1: Prevención de Autogol con consciencia de paredes.
		# Si el arco enemigo está atrás (sectores 7, 8) o el arco propio está adelante,
		# NUNCA empujamos la pelota hacia adelante (sería autogol directo).
		# v2.2: solo cerca de la pelota; se la rodea (órbita) para quedar del lado correcto,
		# acercándose hasta FORWARD_MIN_DIST sin tocarla. El lado lo elige _orbit_side().
		if goal in (7, 8) or self.own_goal_sector() in FRONT:
			self._strafe(self._orbit_side(goal))
			if self.ball_dist() > FORWARD_MIN_DIST:
				self.move_forward()
			return

		# 4) En distancia de tiro / órbita:
		if goal == 3:
			if self.enemy_goal_dist() < 400 and self.ball_dist() < 120:
				_TeamTactics.shot_timer = 90  # Tiro real cerca del arco rival
			self.move_forward()
		elif goal == 2:
			self._strafe("right")
			self.move_forward()
		elif goal == 4:
			self._strafe("left")
			self.move_forward()
		elif goal in (0, 1, 9):
			self._strafe("right")
			if self.ball_dist() > FORWARD_MIN_DIST:
				self.move_forward()
		elif goal in (5, 6, 7):
			self._strafe("left")
			if self.ball_dist() > FORWARD_MIN_DIST:
				self.move_forward()
		else:
			self._strafe("right")
			if self.ball_dist() > FORWARD_MIN_DIST:
				self.move_forward()

	def _avoid_teammate(self):
		mate, mate_d = self._mate_side()
		if mate in FRONT and mate_d < MATE_DIST:
			if mate in (2, 3):
				self.move_right()
			else:
				self.move_left()

	def _watch_stall(self):
		d = self.ball_dist()
		gd = self.enemy_goal_dist()
		self._ball_hist.append(d)
		self._goal_hist.append(gd)
		if len(self._ball_hist) > PUSH_STALL_TICKS:
			self._ball_hist.pop(0)
			self._goal_hist.pop(0)

		far_stall = (d > 100 and len(self._ball_hist) >= STALL_TICKS
					 and max(self._ball_hist[-STALL_TICKS:]) - min(self._ball_hist[-STALL_TICKS:]) < 15)
		push_stall = (d <= 100 and len(self._goal_hist) == PUSH_STALL_TICKS
					  and max(self._goal_hist) - min(self._goal_hist) < 10)

		if far_stall or push_stall:
			self._escape_side = "left" if self._escape_side == "right" else "right"
			self._escape = ESCAPE_TICKS
			self._escape_start_dist = d
			self._ball_hist = []
			self._goal_hist = []


class Keeper(_Sensors, Player):

	def __init__(self):
		super().__init__(task="keeper")

	def default(self):
		ball = self.ball_sector()
		goal = self.own_goal_sector()
		goal_d = self.own_goal_dist()
		py = self.body.position.y

		# Reposicionamiento defensivo en kickoff: repliegue urgente al arco y centro
		if _TeamTactics.is_defense_active():
			if goal is None or goal in (0, 1, 2, 3, 4, 5, 6):
				self.turn_right()
			elif goal == 7:
				self.turn_left()
			elif goal == 9:
				self.turn_right()
			if goal_d > 110:
				self.move_back()
			if py < 420:
				self.move_downfield()
			elif py > 460:
				self.move_upfield()
			return

		# 1) Orientación: Mantener arco propio a la espalda (Sektor 8)
		if goal is None or goal in (0, 1, 2, 3, 4, 5, 6):
			self.turn_right()
		elif goal == 7:
			self.turn_left()
		elif goal == 9:
			self.turn_right()

		# OPTIMIZACIÓN 2: Límite entre postes.
		# FIX v2.1 (2026-10-17): los sectores son RELATIVOS a la mirada del arquero, así que
		# "pelota a la izquierda" es -Y para el azul pero +Y para el violeta. Antes se usaba
		# move_upfield() para la izquierda y el arquero violeta se alejaba de la pelota.
		# Ahora sigue a la pelota con move_left/move_right (como v1) y solo frena si ese
		# paso lo saca de entre los postes.
		if ball in (0, 1, 2, 9):
			side = "left"
		elif ball in (4, 5, 6, 7):
			side = "right"
		else:
			side = None
		if side is not None:
			dy = self._strafe_dy(side)
			past_post = (dy < 0 and py <= POST_TOP_Y) or (dy > 0 and py >= POST_BOTTOM_Y)
			if not past_post:
				if side == "left":
					self.move_left()
				else:
					self.move_right()

		# OPTIMIZACIÓN 4: Manejo de peligro y profundidad
		if goal in BACK:
			# Si la pelota viene de frente y está cerca del arco, salir a despejar
			if ball in FRONT and goal_d < CHARGE_DIST:
				self.move_forward()
			# Si el arquero se alejó demasiado, retroceder a la línea base
			elif goal_d > HOME_DIST:
				self.move_back()
			# Si está demasiado pegado a la red, dar un paso al frente para tener rango
			elif goal_d < 120:
				self.move_forward()


# Tuning-Parameter des Torwarts
CHARGE_DIST = 300
HOME_DIST = 220

striker = Striker()
keeper = Keeper()
