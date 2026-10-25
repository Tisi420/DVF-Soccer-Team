#!/usr/bin/env python3
"""
Imitación del EQUIPO rule-based v2.3 completo — striker y keeper (DVF, sesión 59).

Punto de partida de la corrida5. En vez de seguir el modelo de corrida3, que corre de espaldas el
92 % del tiempo, se empieza de cero copiando a la v2.3 (nuestro mejor equipo) y después se afina
con PPO.

  1. GRABAR: el equipo v2.3 juega de azul en el entorno del entrenamiento (setup_dl_notebook)
     contra NormalTeam, v1 y v2.3, con ruido en el saque y un saque nuevo cada 60 s sin gol
     (formato torneo). Cada 4 frames, que es cuando decide la red, se guardan para cada rol la
     observación (build_observation), la acción del experto y la recompensa de dvf_rewards (v4)
     de esos 4 frames.
  2. VALOR: con esas recompensas se calcula el retorno descontado (gamma 0,99, cortado en cada gol
     o saque). Así la cabeza de valor no arranca de cero, y las primeras actualizaciones de PPO no
     destruyen lo imitado por ventajas mal estimadas.
  3. ENTRENAR: una red nueva por rol (78 -> 256 -> 128 -> 3 cabezas + valor), con entropía
     cruzada en los 3 controles + 0,5 × error cuadrático del valor.
  4. GUARDAR: models/imitacion/equipo_v23/striker.npz y keeper.npz (solo pesos: train_dl arranca
     un Adam nuevo) + resumen.json.

    python scripts/imitar_equipo.py --segundos 240 --semillas 4 --epocas 40
"""
import argparse
import importlib.util
import json
import math
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
import numpy as np
import setup_dl_notebook as S
import dvf_rewards as R
from game.keras_core import build_observation, build_model, OBS_DIM

AR = 4
GAMMA = 0.99
JITTER = 5.0
PARTIDO_S = 60.0
RIVALES = ["soccer_team_NormalTeam", "soccer_team_DVF", "soccer_team_DVF_v2"]


def _mod(path, alias):
	spec = importlib.util.spec_from_file_location(alias, ROOT / path)
	m = importlib.util.module_from_spec(spec); sys.modules[alias] = m; spec.loader.exec_module(m)
	return m


def _saque(pg):
	"""Saque como en el entrenamiento: todos a su spawn y la pelota al centro ±JITTER px."""
	pg._apply_reset()
	cx, cy = pg.screen_dimensions[0] / 2, pg.screen_dimensions[1] / 2
	pg.ball.set_pos((cx + random.uniform(-JITTER, JITTER), cy + random.uniform(-JITTER, JITTER)))


def grabar(rival, seed, segundos):
	random.seed(seed); np.random.seed(seed)
	gt = S.GoalTracker()
	opp = _mod(f"{rival}.py", f"opp_{rival}_{seed}")
	pg, space, _, _, os_, ok = S.create_simulation(opp, gt)
	v2 = _mod("soccer_team_DVF_v2.py", f"exp_{rival}_{seed}")
	es, ek = v2.Striker(), v2.Keeper()
	es.set_team("blue"); ek.set_team("blue")
	pg.init_players(os_, ok, es, ek)
	_saque(pg)
	datos = {rol: {"X": [], "Y": [], "r": [], "fin": []} for rol in ("striker", "keeper")}
	decisiones = int(segundos * S.FPS / AR)
	desde_saque = 0
	for _ in range(decisiones):
		pg.update_view_fields()
		obs = {"striker": build_observation(es), "keeper": build_observation(ek)}
		pbp = (pg.ball.body.position.x, pg.ball.body.position.y)
		pbv = (pg.ball.body.velocity.x, pg.ball.body.velocity.y)
		prev = {}
		for rol, p in (("striker", es), ("keeper", ek)):
			pp = (p.body.position.x, p.body.position.y)
			prev[rol] = (pp, math.hypot(pbp[0] - pp[0], pbp[1] - pp[1]))
		acciones = None
		sc = cc = False
		for f in range(AR):
			if f:
				pg.update_view_fields()
			es.default(); ek.default()          # los expertos deciden cada frame, como en un partido
			if f == 0:
				acciones = {"striker": list(es.action), "keeper": list(ek.action)}
			S.sim_step(pg, space, es, ek, os_, ok, call_opponent_ai=True)
			ev = gt.pop()
			sc |= ev == "blue"; cc |= ev == "purple"
		desde_saque += 1
		fin = sc or cc
		for rol, p in (("striker", es), ("keeper", ek)):
			r = R.compute_reward(sc, cc, rol, player=p, ball=pg.ball, prev_ball_pos=pbp, prev_ball_vel=pbv,
			                     prev_dist=prev[rol][1], prev_player_pos=prev[rol][0])
			d = datos[rol]
			d["X"].append(obs[rol]); d["Y"].append(acciones[rol]); d["r"].append(r)
		if not fin and desde_saque >= PARTIDO_S * S.FPS / AR:
			_saque(pg); fin = True              # fin de "partido" sin gol: saque nuevo
		if fin:
			desde_saque = 0
		for rol in datos:
			datos[rol]["fin"].append(fin)
	return datos, (pg.goal_counter_blue, pg.goal_counter_purple)


def retornos(r, fin):
	g, out = 0.0, np.zeros(len(r), np.float32)
	for t in reversed(range(len(r))):
		if fin[t]:
			g = 0.0
		g = r[t] + GAMMA * g
		out[t] = g
	return out


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--segundos", type=float, default=240)
	ap.add_argument("--semillas", type=int, default=4)
	ap.add_argument("--epocas", type=int, default=40)
	ap.add_argument("--out", type=Path, default=ROOT / "models" / "imitacion" / "equipo_v23")
	args = ap.parse_args()
	args.out.mkdir(parents=True, exist_ok=True)

	t0 = time.time()
	junto = {rol: {"X": [], "Y": [], "G": []} for rol in ("striker", "keeper")}
	marcadores = {}
	for rival in RIVALES:
		for s in range(args.semillas):
			datos, m = grabar(rival, 200 + s, args.segundos)
			marcadores[f"{rival}#{s}"] = m
			for rol, d in datos.items():
				junto[rol]["X"] += d["X"]; junto[rol]["Y"] += d["Y"]
				junto[rol]["G"].append(retornos(d["r"], d["fin"]))
			print(f"  grabado {rival} semilla {s}: {len(datos['striker']['X'])} decisiones, v2.3 {m[0]}-{m[1]}", flush=True)
	print(f"grabación: {time.time() - t0:.0f} s", flush=True)

	import tensorflow as tf
	tf.random.set_seed(0)
	resumen = {"fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "recompensa": R.REWARD_VERSION,
	           "segundos_por_partido": args.segundos, "semillas": args.semillas, "epocas": args.epocas,
	           "marcadores_grabacion": marcadores, "roles": {}}
	for rol in ("striker", "keeper"):
		X = np.asarray(junto[rol]["X"], np.float32); Y = np.asarray(junto[rol]["Y"], np.int64)
		G = np.concatenate(junto[rol]["G"]).astype(np.float32)
		idx = np.random.permutation(len(X)); X, Y, G = X[idx], Y[idx], G[idx]
		model = build_model(); model(tf.zeros((1, OBS_DIM)))
		model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
		              loss=["sparse_categorical_crossentropy"] * 3 + ["mse"], loss_weights=[1, 1, 1, 0.5],
		              metrics=[["accuracy"], ["accuracy"], ["accuracy"], []])
		h = model.fit(X, [Y[:, 0], Y[:, 1], Y[:, 2], G], epochs=args.epocas, batch_size=256,
		              validation_split=0.15, verbose=0)
		acc = {k: round(float(v[-1]), 4) for k, v in h.history.items() if k.startswith("val_") and "accuracy" in k}
		vloss = round(float(h.history["val_value_loss"][-1]), 4) if "val_value_loss" in h.history else None
		dist = {k: np.bincount(Y[:, i], minlength=3).tolist() for i, k in enumerate(("fb", "lr", "turn"))}
		print(f"{rol}: {len(X)} muestras · precisión de validación {acc} · error del valor {vloss} · "
		      f"retorno medio {float(G.mean()):+.3f} ± {float(G.std()):.3f}", flush=True)
		S._npz_save(model, str(args.out / f"{rol}.npz"))   # sin opt_* (optimizador no registrado)
		resumen["roles"][rol] = {"muestras": int(len(X)), "val_accuracy": acc, "val_value_loss": vloss,
		                         "retorno_medio": float(G.mean()), "distribucion_acciones": dist}
	(args.out / "resumen.json").write_text(json.dumps(resumen, indent=1), encoding="utf-8")
	print(f"listo en {time.time() - t0:.0f} s → {args.out}")


if __name__ == "__main__":
	main()
