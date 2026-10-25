"""
================================================================================
Robotic Soccer - Deep Learning Agent: DVF (PPO)
================================================================================
Team Members: Diego, Valentino, Fernando
Course: Robotic Motions / Machine Learning Soccer Tournament
University: Reutlingen University

Basado en soccer_team_DeepLearning.py (plantilla del curso). Cambios DVF (2026-10-17):
  * De dónde se cargan los modelos:
      - por defecto: models/DVF_striker.npz y models/DVF_keeper.npz (los que se entregan);
      - con la variable de entorno DVF_DL_RUN=<run>: models/runs/<run>/striker.npz y
        keeper.npz, para evaluar una corrida de scripts/train_dl.py con el benchmark:
            $env:DVF_DL_RUN = "noche1"; python scripts/benchmark.py soccer_team_DVF_DL --vs ...
      - con DVF_DL_STRIKER y DVF_DL_KEEPER (rutas a .npz): un checkpoint puntual.
  * Apariencia propia (naranja, "DVF").
Entrenamiento: scripts/train_dl.py con la recompensa de dvf_rewards.py. Ver CHANGELOG.md.
================================================================================
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.player import Player
from game.keras_core import build_observation, N_ACTIONS

_ROOT = os.path.dirname(os.path.abspath(__file__))
_RUN = os.environ.get("DVF_DL_RUN", "").strip()
# Para evaluar un checkpoint puntual: rutas explícitas (relativas a la raíz del proyecto).
_S_FILE = os.environ.get("DVF_DL_STRIKER", "").strip()
_K_FILE = os.environ.get("DVF_DL_KEEPER", "").strip()
if _S_FILE and _K_FILE:
	MODEL_DIR = _ROOT
	STRIKER_MODEL = _S_FILE
	KEEPER_MODEL = _K_FILE
elif _RUN:
	MODEL_DIR = os.path.join(_ROOT, "models", "runs", _RUN)
	STRIKER_MODEL = "striker.npz"
	KEEPER_MODEL = "keeper.npz"
else:
	MODEL_DIR = os.path.join(_ROOT, "models")
	STRIKER_MODEL = "DVF_striker.npz"
	KEEPER_MODEL = "DVF_keeper.npz"


def _load_weights(model_file: str, role_name: str) -> dict:
	"""Carga los pesos desde un .npz (sin TensorFlow al jugar); ignora el estado del optimizador."""
	path = os.path.join(MODEL_DIR, model_file)
	if not os.path.exists(path):
		raise FileNotFoundError(f"[DVF_DL] {role_name}: no existe {path}")
	w = np.load(path)
	return {k: w[k] for k in w.files}


def _softmax(x: np.ndarray) -> np.ndarray:
	e = np.exp(x - x.max())
	return e / e.sum()


def _infer(w: dict, obs: np.ndarray):
	"""Observación de 78 valores -> (p_fb, p_lr, p_turn), cada una de 3 probabilidades."""
	h = np.maximum(0.0, obs @ w["h1_W"] + w["h1_b"])
	h = np.maximum(0.0, h @ w["h2_W"] + w["h2_b"])
	return (
		_softmax(h @ w["fb_W"] + w["fb_b"]),
		_softmax(h @ w["lr_W"] + w["lr_b"]),
		_softmax(h @ w["turn_W"] + w["turn_b"]),
	)


# Igual que la plantilla del curso: se MUESTREA la política (no argmax) y cada acción se
# mantiene ACTION_REPEAT frames, como en el entrenamiento.
DEPLOY_SAMPLE = True
ACTION_REPEAT = 4


# DVF (2026-10-18, sesión 26): corrección de la observación para el equipo VIOLETA.
# build_observation (game/keras_core.py, del curso) "da vuelta" la cancha para el violeta
# invirtiendo x, vx y sumando 180° al ángulo, que es una ROTACIÓN de 180°, pero NO invierte y ni
# vy. El juego es simétrico por esa rotación (los spawns violetas son los azules rotados) y la red
# entrena siempre de azul, así que de violeta veía una "y" que contradice sus sensores: en el saque
# el striker azul ve y=0,6 y el violeta 0,4 en la misma situación. Medido: de violeta recibía 3-4
# veces más goles. Con y e vy invertidas las dos observaciones del saque coinciden (dif. ≤ 0,007).
# DVF_DL_FIX_Y=0 vuelve al comportamiento original (para comparar).
FIX_Y = os.environ.get("DVF_DL_FIX_Y", "1").strip() != "0"


def _obs(player):
	obs = build_observation(player)
	if FIX_Y and player.team == "purple":
		obs[71] = 1.0 - obs[71]     # posición y
		obs[73] = -obs[73]          # velocidad y
	return obs


def _decide(weights, player):
	p_fb, p_lr, p_turn = _infer(weights, _obs(player))
	if DEPLOY_SAMPLE:
		return [int(np.random.choice(N_ACTIONS, p=p_fb)),
		        int(np.random.choice(N_ACTIONS, p=p_lr)),
		        int(np.random.choice(N_ACTIONS, p=p_turn))]
	return [int(np.argmax(p_fb)), int(np.argmax(p_lr)), int(np.argmax(p_turn))]


_APPEARANCE = {"color": (0.95, 0.45, 0.10), "label": "DVF",
               "shape": "cone", "height": 52.0, "radius": 24.0}


class Striker(Player):
	_weights = None

	def __init__(self):
		super().__init__(task="striker")
		self._hold = 0
		self._act = [0, 0, 0]
		if Striker._weights is None:
			Striker._weights = _load_weights(STRIKER_MODEL, "striker")

	@staticmethod
	def get_team_appearance() -> dict:
		return _APPEARANCE

	def default(self):
		if self._hold <= 0:                       # re-decidir cada ACTION_REPEAT frames
			self._act = _decide(Striker._weights, self)
			self._hold = ACTION_REPEAT
		self.action = list(self._act)
		self._hold -= 1


class Keeper(Player):
	_weights = None

	def __init__(self):
		super().__init__(task="keeper")
		self._hold = 0
		self._act = [0, 0, 0]
		if Keeper._weights is None:
			Keeper._weights = _load_weights(KEEPER_MODEL, "keeper")

	@staticmethod
	def get_team_appearance() -> dict:
		return _APPEARANCE

	def default(self):
		if self._hold <= 0:
			self._act = _decide(Keeper._weights, self)
			self._hold = ACTION_REPEAT
		self.action = list(self._act)
		self._hold -= 1


striker = Striker()
keeper = Keeper()
