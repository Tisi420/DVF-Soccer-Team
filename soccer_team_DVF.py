"""
================================================================================
Robotic Soccer - Rule-Based Agent: DVF (Original Base Version)
================================================================================
Team Members: Diego, Valentino, Fernando
Course: Robotic Motions / Machine Learning Soccer Tournament
University: Reutlingen University

Description:
    State-machine rule-based soccer AI controlling a Striker and a Keeper.
    Uses 10 sensor sectors and distance thresholds to navigate, orbit the ball,
    and coordinate attacks while evading deadlocks.

Changelog:
    - v1.0.0: Initial rule-based implementation by DVF team.
    - v1.1.0: Added _TeamTactics module for adaptive kickoff defense to
              prevent consecutive kickoff goals from fast long-range shots.
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

	def move_downfield(self):
		"""Mueve al jugador hacia +Y (abajo en la pantalla), sin importar si es Blue o Purple."""
		if getattr(self, "team", "blue") == "blue":
			self.move_right()
		else:
			self.move_left()

	def move_upfield(self):
		"""Mueve al jugador hacia -Y (arriba en la pantalla), sin importar si es Blue o Purple."""
		if getattr(self, "team", "blue") == "blue":
			self.move_left()
		else:
			self.move_right()

	@staticmethod
	def get_team_appearance() -> dict:
		"""Team appearance in 3D view and HUD."""
		return {
			"color": (0.10, 0.85, 0.85),   # turquoise
			"label": "DFC",
			"shape": "cone",
			"height": 50.0,
			"radius": 24.0,
		}


ORBIT_DIST = 160        # erst unterhalb dieser Ballentfernung wird der Ball umkreist
FORWARD_MIN_DIST = 90   # beim Umkreisen des Balls erst ab diesem Abstand zusätzlich vorwärts
MATE_DIST = 130     # Abstand, ab dem der Striker dem Torwart ausweicht
STALL_TICKS = 90        # so lange ohne Fortschritt = Blockade (~1.5 s)
PUSH_STALL_TICKS = 120  # so lange gegen Wand/Ecke schieben = Blockade (~2 s)
BACK_TICKS = 40         # Phase 1 des Befreiungs-Manövers: zurücksetzen
DETOUR_TICKS = 50       # Phase 2: seitlich am Hindernis vorbei
CHARGE_TICKS = 60       # Phase 3: mit Anlauf auf den Ball
ESCAPE_TICKS = BACK_TICKS + DETOUR_TICKS + CHARGE_TICKS


import math

class _TeamTactics:
	quick_goals_conceded = 0
	play_ticks = 0
	defense_kickoff_ticks = 0
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
		else:
			cls.play_ticks += 1
			if cls.defense_kickoff_ticks > 0:
				cls.defense_kickoff_ticks -= 1

		cls.current_tick += 1

	@classmethod
	def is_defense_active(cls):
		return cls.defense_kickoff_ticks > 0


class Striker(_Sensors, Player):

	def __init__(self):
		super().__init__(task="striker")
		self._ball_hist = []    # letzte Ball-Distanzen (zum Erkennen von Blockaden)
		self._goal_hist = []    # letzte Distanzen zum gegnerischen Tor
		self._escape = 0        # Restdauer des Befreiungs-Manövers (in Ticks)
		self._escape_side = "right"

	def default(self):
		_TeamTactics.tick(self)
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
		# Befreiungs-Manöver (nach Blockade), drei Phasen:
		#  1) kurz zurücksetzen und zur Seite ausweichen
		#  2) seitlich am Hindernis (Wand/Gegner) vorbeilaufen
		#  3) mit Anlauf auf den Ball -> er prallt aus Wand/Ecke zurück ins Feld
		if self._escape > 0:
			self._escape -= 1
			self.turn_towards(self.ball_sector())
			if self._escape >= DETOUR_TICKS + CHARGE_TICKS:
				self.move_back()      # nur gerade zurück (seitlich könnte in der Wand klemmen)
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
		"""Wo steht der Torwart (links/rechts/vorne) und wie weit weg?"""
		return self.sector_of("player_friendly"), self.dist_of("player_friendly")

	def _strafe(self, side):
		"""Seitlich laufen, aber nicht in den eigenen Torwart hinein."""
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

	def _attack(self):
		ball = self.ball_sector()
		goal = self.enemy_goal_sector()

		if ball is None:
			self.turn_left()
			return

		# 1) Immer zum Ball ausrichten
		self.turn_towards(ball)

		# 2) Ball nicht vorne -> erst drehen (nicht rennen)
		if ball not in FRONT:
			return

		# 2b) Ball noch weit weg -> einfach geradeaus hinlaufen (Umkreisen erst in Ballnähe,
		#     sonst läuft der Striker einen großen Bogen und landet in Wand/Torraum)
		if self.ball_dist() > ORBIT_DIST:
			self.move_forward()
			return

		# 3) Ball vorne: ist das gegnerische Tor genau vorne? -> Schuss / Dribbling
		if goal == 3:
			if self.enemy_goal_dist() < 400 and self.ball_dist() < 120:
				_TeamTactics.shot_timer = 90  # Tiro real cerca del arco rival
			self.move_forward()
		# 3b) Tor leicht seitlich -> beim Laufen schon in Richtung Tor "einkurven",
		#     damit der Ball nicht schräg in Wand/Ecke geschoben wird
		elif goal == 2:
			self._strafe("right")
			self.move_forward()
		elif goal == 4:
			self._strafe("left")
			self.move_forward()
		# 4) Tor ist links -> um den Ball herum nach rechts laufen (und umgekehrt)
		elif goal in (0, 1, 9):
			self._strafe("right")
			if self.ball_dist() > FORWARD_MIN_DIST:
				self.move_forward()
		elif goal in (5, 6, 7):
			self._strafe("left")
			if self.ball_dist() > FORWARD_MIN_DIST:
				self.move_forward()
		else:
			# Tor hinten -> seitlich um den Ball herum
			self._strafe("right")
			if self.ball_dist() > FORWARD_MIN_DIST:
				self.move_forward()

	def _avoid_teammate(self):
		"""Nicht in den eigenen Torwart rennen (sonst blockieren sich beide)."""
		mate, mate_d = self._mate_side()
		if mate in FRONT and mate_d < MATE_DIST:
			if mate in (2, 3):
				self.move_right()
			else:
				self.move_left()

	def _watch_stall(self):
		"""Erkennt Blockaden: (a) wir kommen nicht näher an den Ball,
		(b) wir schieben den Ball gegen Wand/Ecke und bewegen uns nicht mehr."""
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
			# Seite bei jeder Blockade wechseln -> anderer Weg / anderer Anlaufwinkel
			self._escape_side = "left" if self._escape_side == "right" else "right"
			self._escape = ESCAPE_TICKS
			self._ball_hist = []
			self._goal_hist = []


class Keeper(_Sensors, Player):

	def __init__(self):
		super().__init__(task="keeper")

	def default(self):
		ball = self.ball_sector()
		goal = self.own_goal_sector()
		goal_d = self.own_goal_dist()

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
			py = self.body.position.y
			if py < 420:
				self.move_downfield()
			elif py > 460:
				self.move_upfield()
			return

		# 1) Eigenes Tor soll hinten (Sektor 8) bleiben -> Blick zum Spielfeld
		if goal is None or goal in (0, 1, 2, 3, 4, 5, 6):
			self.turn_right()
		elif goal == 7:
			self.turn_left()
		elif goal == 9:
			self.turn_right()

		# 2) Seitlich zum Ball mitgehen (auch wenn der Ball hinten gesehen wird)
		if ball in (0, 1, 2, 9):
			self.move_left()
		elif ball in (4, 5, 6, 7):
			self.move_right()

		# 3) Tiefe: Ball vorne -> angreifen/klären, sonst Abstand zum Tor halten
		if goal in BACK:
			if ball in FRONT and goal_d < CHARGE_DIST:
				self.move_forward()
			elif goal_d > HOME_DIST:
				self.move_back()
			elif goal_d < 120:
				self.move_forward()


# Tuning-Parameter des Torwarts
CHARGE_DIST = 300   # bis zu dieser Entfernung vom Tor darf er dem Ball entgegenlaufen
HOME_DIST = 220     # Grundposition: so weit vor dem eigenen Tor


striker = Striker()
keeper = Keeper()
