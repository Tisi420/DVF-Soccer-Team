#!/usr/bin/env python3
"""
Pre-entrenamiento por IMITACIÓN del striker (DVF, sesión 33).

El striker DL aprendió a defender pero casi no ataca contra los rule-based. Nuestro striker
rule-based v2.3 sí ataca (v2.3 le gana a v1 +5,6 y a NormalTeam +9,1). Este script:
  1. graba (observación, acción) del striker v2.3 jugando DE AZUL en el entorno del entrenamiento
     (setup_dl_notebook), con nuestro keeper = la red de una corrida y rivales NormalTeam/v1/v2.3;
     la observación es la misma build_observation que ve la red y la acción se toma cada
     ACTION_REPEAT frames (cuando decide la red);
  2. entrena la red del striker para copiarlo (entropía cruzada en sus 3 controles), partiendo de
     los pesos actuales de la corrida (así la cabeza de valor no arranca de cero);
  3. guarda el clon SOLO con pesos (sin estado del optimizador): si después se usa para seguir con
     PPO, train_dl arranca un Adam nuevo ("Resumed striker (weights only)").

No toca la corrida en curso: escribe en models/imitacion/.

    python scripts/imitar_striker.py --run corrida2 --segundos 240 --semillas 2 --epocas 15
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
from game.keras_core import build_observation, build_model, OBS_DIM

AR = 4
RIVALES = ["soccer_team_NormalTeam", "soccer_team_DVF", "soccer_team_DVF_v2"]


def _mod(path, alias):
	spec = importlib.util.spec_from_file_location(alias, ROOT / path)
	m = importlib.util.module_from_spec(spec); sys.modules[alias] = m; spec.loader.exec_module(m)
	return m


def _infer(w, obs):
	h = np.maximum(0.0, obs @ w["h1_W"] + w["h1_b"])
	h = np.maximum(0.0, h @ w["h2_W"] + w["h2_b"])
	out = []
	for k in ("fb", "lr", "turn"):
		z = h @ w[f"{k}_W"] + w[f"{k}_b"]; e = np.exp(z - z.max()); out.append(e / e.sum())
	return out


def grabar(rival, seed, segundos, keeper_w):
	"""Un partido del striker v2.3 (azul) + nuestro keeper DL contra `rival`: lista de (obs, acción)."""
	random.seed(seed); np.random.seed(seed)
	gt = S.GoalTracker()
	opp = _mod(f"{rival}.py", f"opp_{rival}_{seed}")
	pg, space, ks, kk, os_, ok = S.create_simulation(opp, gt)
	v2 = _mod("soccer_team_DVF_v2.py", f"exp_{rival}_{seed}")
	exp = v2.Striker(); exp.set_team("blue")
	pg.init_players(os_, ok, exp, kk)
	X, Y = [], []
	ka = [0, 0, 0]
	frames = int(segundos * S.FPS)
	for f in range(frames):
		pg.update_view_fields()
		decide = f % AR == 0
		if decide:
			obs = build_observation(exp)
			ka = [int(np.random.choice(3, p=q)) for q in _infer(keeper_w, build_observation(kk))]
		exp.default()                         # el experto decide cada frame (como en el partido)
		if decide:
			X.append(obs); Y.append(list(exp.action))
		kk.action = list(ka)
		S.sim_step(pg, space, exp, kk, os_, ok, call_opponent_ai=True)
		gt.pop()
	return X, Y, (pg.goal_counter_blue, pg.goal_counter_purple)


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--run", default="corrida2")
	ap.add_argument("--segundos", type=float, default=240)
	ap.add_argument("--semillas", type=int, default=2)
	ap.add_argument("--epocas", type=int, default=15)
	ap.add_argument("--out", type=Path, default=ROOT / "models" / "imitacion")
	args = ap.parse_args()
	args.out.mkdir(parents=True, exist_ok=True)
	run_dir = ROOT / "models" / "runs" / args.run
	kw = np.load(run_dir / "keeper.npz"); kw = {k: kw[k] for k in kw.files}

	t0 = time.time()
	X, Y, marcadores = [], [], {}
	for rival in RIVALES:
		for s in range(args.semillas):
			x, y, m = grabar(rival, 100 + s, args.segundos, kw)
			X += x; Y += y; marcadores[f"{rival}#{s}"] = m
			print(f"  grabado {rival} semilla {s}: {len(x)} decisiones, marcador v2.3+keeperDL {m[0]}-{m[1]}", flush=True)
	X = np.asarray(X, np.float32); Y = np.asarray(Y, np.int64)
	np.savez_compressed(args.out / "datos_striker_v23.npz", X=X, Y=Y)
	dist = {k: np.bincount(Y[:, i], minlength=3).tolist() for i, k in enumerate(("fb", "lr", "turn"))}
	print(f"{len(X)} muestras en {time.time() - t0:.0f} s · distribución de acciones {dist}", flush=True)

	import tensorflow as tf
	tf.random.set_seed(0)
	model = build_model(); model(tf.zeros((1, OBS_DIM)))
	S._npz_load(model, run_dir / "striker.npz")          # parte de la red actual de la corrida
	actor = tf.keras.Model(model.input, model.outputs[:3])
	actor.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
	              loss=["sparse_categorical_crossentropy"] * 3, metrics=[["accuracy"]] * 3)
	idx = np.random.permutation(len(X)); X, Y = X[idx], Y[idx]
	hist = actor.fit(X, [Y[:, 0], Y[:, 1], Y[:, 2]], epochs=args.epocas, batch_size=256,
	                 validation_split=0.15, verbose=2)
	h = {k: [round(float(v), 4) for v in vals] for k, vals in hist.history.items()}
	acc = {k: h[k][-1] for k in h if k.startswith("val_") and "accuracy" in k}
	print(f"precisión de validación al final: {acc}", flush=True)

	S._npz_save(model, str(args.out / "striker_clon.npz"))  # sin opt_* (no está registrado)
	(args.out / "imitacion.json").write_text(json.dumps({
		"fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "run_base": args.run, "muestras": int(len(X)),
		"segundos_por_partido": args.segundos, "semillas": args.semillas, "epocas": args.epocas,
		"marcadores_grabacion": marcadores, "distribucion_acciones": dist, "val_accuracy_final": acc,
		"historia": h}, indent=1), encoding="utf-8")
	print(f"clon guardado en {args.out / 'striker_clon.npz'}")


if __name__ == "__main__":
	main()
