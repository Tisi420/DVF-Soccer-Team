#!/usr/bin/env python3
"""
Entrenamiento PPO del equipo DVF (Deep Learning), sin Jupyter (equipo DVF, 2026-10-17).

Usa la infraestructura del curso (setup_dl_notebook.py, sin modificarla) con:
  * nuestra recompensa: dvf_rewards.compute_reward (ver CHANGELOG sesión 8);
  * entrenamiento ALTERNADO striker/keeper (lo pide la cátedra): en cada fase un rol aprende
    y el otro juega con sus pesos congelados;
  * rivales mezclados entre los workers (por defecto NormalTeam, DVF = v1, DVF_v2 = v2.3);
  * ruido en el saque (la pelota sale a ±JITTER px del centro) para no aprender un único
    saque determinista;
  * reinicio por pelota trabada en cualquier lugar (como la ventana), no solo en esquinas.

    python scripts/train_dl.py --run noche1 --hours 10
    python scripts/train_dl.py --run prueba --phase-steps 30000 --cycles 1        # prueba rápida
    python scripts/train_dl.py --run noche2 --init-from models/runs/noche1 --hours 8

Cada corrida vive en models/runs/<run>/: striker.npz, keeper.npz, checkpoints/, training.log
y run.json (configuración + horas, para la planilla de metadata).

IMPORTANTE para corridas largas (actualizado 2026-10-17 21:10): lanzarlas con el SUPERVISOR
(scripts/supervisar_entrenamiento.py, con --until) para que se relancen solas si el proceso
muere por un crash nativo, y con la salida redirigida a un archivo:

    Start-Process .\\env\\Scripts\\python.exe -ArgumentList 'scripts\\supervisar_entrenamiento.py','--run','noche1','--until','2026-10-18T07:15','--phase-steps','1500000' `
        -RedirectStandardOutput models\\runs\\_salidas\\noche1_stdout.txt `
        -RedirectStandardError models\\runs\\_salidas\\noche1_stderr.txt -WindowStyle Hidden

Por qué redirigir la salida: cada gol de los 14 workers imprime una línea y un proceso
oculto no tiene consola. (Corrección 2026-10-17: el primer "congelamiento" no fue la consola
bloqueada sino un crash nativo de un worker; ver CHANGELOG, sesión 16.)

Crashes nativos: en esta PC los procesos mueren cada ~20 min con 0xc0000005 en python310.dll.
Si muere un worker, el bucle lo reemplaza en caliente; si muere el proceso principal, lo
relanza el supervisor. El progreso se sigue en models/runs/<run>/training.log y
models/runs/<run>/supervisor.log.
"""
import argparse
import datetime as dt
import json
import math
import os
import queue
import random
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)                       # setup_dl_notebook usa rutas relativas a la raíz
sys.path.insert(0, str(ROOT))

# --- Parches del ENTORNO de entrenamiento -------------------------------------------------
# Van a nivel de módulo a propósito: los workers en paralelo se crean con "spawn", que vuelve a
# importar este archivo (como __mp_main__) antes de correr; así los parches también valen ahí.
JITTER = float(os.environ.get("DVF_TRAIN_JITTER", "5"))      # ±px de la pelota en cada saque
STILL_SPEED = 15.0                                          # px/s: pelota "quieta" (≈ 45 px en 3 s)

import setup_dl_notebook as S                               # noqa: E402  (importa TensorFlow)
from game.playground import Playground                      # noqa: E402

_orig_apply_reset = Playground._apply_reset


def _apply_reset_with_jitter(self):
	"""Saque con la pelota a ±JITTER px del centro (en el torneo sale del centro exacto)."""
	_orig_apply_reset(self)
	if JITTER > 0:
		cx, cy = self.screen_dimensions[0] / 2, self.screen_dimensions[1] / 2
		self.ball.set_pos((cx + random.uniform(-JITTER, JITTER), cy + random.uniform(-JITTER, JITTER)))


Playground._apply_reset = _apply_reset_with_jitter

_orig_ball_in_corner = S.ball_in_corner


def _ball_stuck(ball, dist=160.0):
	"""Predicado del 'stall reset' del entrenamiento (stuck_ball_step lo usa 3 s seguidos).
	Original: solo pelota en una esquina. Ahora además: pelota casi quieta en cualquier lugar,
	como el reinicio por pelota trabada del juego con ventana."""
	v = ball.body.velocity
	return _orig_ball_in_corner(ball, dist) or math.hypot(v.x, v.y) < STILL_SPEED


S.ball_in_corner = _ball_stuck

from dvf_rewards import compute_reward                      # noqa: E402

# Hiperparámetros: los del notebook del curso (celda "Tune freely between runs").
HPARAMS = dict(lr=3e-4, gamma=0.99, lam=0.95, clip_ratio=0.2, epochs=4, batch_size=64,
               action_repeat=4, entropy_coef=0.05, value_coef=0.5, max_grad_norm=0.5)


WORKER_TIMEOUT = float(os.environ.get("DVF_WORKER_TIMEOUT", "120"))  # s sin resultados = workers perdidos (vuelta normal: ~5 s)
MAX_REINTENTOS = 5         # reinicios de fase permitidos por corrida antes de rendirse


def _safe_save(model, path):
	"""Guardado ATÓMICO de un .npz (2026-10-17): se escribe a un temporal y se renombra.
	En noche1 el proceso principal murió por un crash nativo (0xc0000005) justo después de un
	guardado; si hubiera muerto en el medio, el .npz quedaba a medias y la corrida no podía
	continuar. os.replace es atómico: o queda el archivo viejo o el nuevo, nunca uno roto."""
	tmp = path[:-4] + ".tmp.npz"
	S._npz_save(model, tmp)
	os.replace(tmp, path)


class WorkersPerdidos(RuntimeError):
	"""Los workers dejaron de responder; main() reinicia la fase desde el último guardado."""


def _run_parallel_dvf(striker, keeper, tr_s, tr_k, compute_reward_fn, cfg, role, extra=None):
	"""Copia de setup_dl_notebook._run_parallel (curso) con dos cambios DVF:
	  1) solo se actualiza el rol que entrena (role = 'striker' | 'keeper' | 'both'); el otro
	     juega con sus pesos congelados (entrenamiento alternado, pedido de la cátedra);
	  2) el log registra pl/vl/ent DEL ROL QUE ENTRENA (el original siempre mostraba los del
	     striker: en una fase de keeper quedaba ent=0.000 y la curva engañaba) y pone la fase
	     en 'opp=' para que la celda de curvas del notebook pinte una banda por fase.
	El formato de la línea [IT n] es compatible con esa celda.

	extra (2026-10-17, opcional): {"ent": {"striker": c, "keeper": c}} fija el coeficiente de
	entropía de cada rol para esta fase (los entrenadores del curso lo capturan al primer paso
	de entrenamiento, y train() crea entrenadores nuevos en cada fase); a la salida deja en
	extra["stats"] el resumen de la fase (entropía media, goles por actualización)."""
	import cloudpickle
	extra = extra if extra is not None else {}
	for rname, tr in (("striker", tr_s), ("keeper", tr_k)):
		c = extra.get("ent", {}).get(rname)
		if c is not None:
			tr.entropy_coef = float(c)
	hist = {"ent": [], "gf": [], "gc": []}
	from collections import Counter
	np, tf = S.np, S.tf
	md = cfg["model_dir"]; LOG = cfg["log_file"]; W = cfg["workers"]; R = cfg["worker_rollout"]; AR = cfg["action_repeat"]
	os.environ["OMP_NUM_THREADS"] = "1"; os.environ["TF_NUM_INTRAOP_THREADS"] = "1"; os.environ["TF_NUM_INTEROP_THREADS"] = "1"
	reward_bytes = cloudpickle.dumps(compute_reward_fn)
	opps = list(cfg["opponent"]) if isinstance(cfg["opponent"], (list, tuple)) else [cfg["opponent"]]
	worker_opps = [opps[i % len(opps)] for i in range(W)]
	ctx = S._mp.get_context("spawn")
	result_q = ctx.Queue(); weight_qs = []; procs = []

	def _spawn(wid):
		"""Crea (o re-crea) el worker 'wid' con su propia cola de pesos."""
		wq = ctx.Queue()
		pr = ctx.Process(target=S._parallel_worker, args=(wid, worker_opps[wid], reward_bytes,
		                 dict(worker_rollout=R, action_repeat=AR), wq, result_q), daemon=True)
		pr.start()
		return wq, pr

	for wid in range(W):
		wq, pr = _spawn(wid); weight_qs.append(wq); procs.append(pr)
	run_tag = dt.datetime.now().strftime("%Y%m%d_%H%M%S"); ckpt = S._ckpt_dir(md)
	with open(LOG, "a") as f:
		f.write(f"\n=== PARALLEL run {dt.datetime.now():%Y-%m-%d %H:%M:%S} | {W} workers x {R} | "
		        f"opp {dict(Counter(worker_opps))} | entrena {role} | "
		        f"entropía s={tr_s.entropy_coef} k={tr_k.entropy_coef} ===\n")

	def _upd(tr, pays, key):          # igual que en el curso
		O = []; FB = []; LRa = []; TRa = []; OLP = []; ADV = []; RET = []
		for p in pays:
			o, fb, lr_, tra, lp, vs, rs, dn, lv = p[key]
			a, r = S._gae_np(vs, rs, dn, lv, cfg["gamma"], cfg["lam"])
			O.append(o); FB.append(fb); LRa.append(lr_); TRa.append(tra); OLP.append(lp); ADV.append(a); RET.append(r)
		O = np.concatenate(O); FB = np.concatenate(FB); LRa = np.concatenate(LRa); TRa = np.concatenate(TRa)
		OLP = np.concatenate(OLP); ADV = np.concatenate(ADV); RET = np.concatenate(RET)
		ADV = (ADV - ADV.mean()) / (ADV.std() + 1e-8)
		Ot = tf.constant(O); FBt = tf.constant(FB); LRt = tf.constant(LRa); TRt = tf.constant(TRa)
		OLPt = tf.constant(OLP); ADVt = tf.constant(ADV, tf.float32); RETt = tf.constant(RET, tf.float32)
		n = len(O); sp = sv = se = 0.0; nb = 0
		for _ in range(cfg["epochs"]):
			perm = np.random.permutation(n)
			for s in range(0, n, cfg["batch_size"]):
				idx = perm[s:s + cfg["batch_size"]]
				pl, vl, ent = tr._train_step(tf.gather(Ot, idx), tf.gather(FBt, idx), tf.gather(LRt, idx),
				                             tf.gather(TRt, idx), tf.gather(OLPt, idx), tf.gather(ADVt, idx), tf.gather(RETt, idx))
				sp += pl.numpy(); sv += vl.numpy(); se += ent.numpy(); nb += 1
		return sp / max(nb, 1), sv / max(nb, 1), se / max(nb, 1)

	ts = it = alls = allc = 0; t0 = time.time()
	try:
		while ts < cfg["total_steps"]:
			sw = striker.get_weights(); kw = keeper.get_weights()
			for wq in weight_qs:
				wq.put((sw, kw))
			# DVF (2026-10-17): watchdog + REEMPLAZO de workers. En noche1 los workers mueren de golpe
			# cada ~20 min por un crash nativo (0xc0000005 en python310.dll, visor de eventos) y el
			# bucle original esperaba para siempre. Primera versión: tras 120 s se reiniciaba la
			# fase entera. Ahora: cada 5 s sin resultados se revisa si murió algún worker; si murió,
			# se lo reemplaza por uno nuevo (mismo rival) con los pesos de esta iteración y se sigue
			# (~15 s de arranque). Solo si nadie murió y no llega nada en WORKER_TIMEOUT s, se corta
			# la fase con WorkersPerdidos y main() la reinicia desde el último guardado.
			pays = []
			limite_iter = time.time() + WORKER_TIMEOUT
			while len(pays) < W:
				try:
					pays.append(result_q.get(timeout=5))
				except queue.Empty:
					muertos = [i for i, p in enumerate(procs) if not p.is_alive()]
					for i in muertos:
						code = procs[i].exitcode
						weight_qs[i], procs[i] = _spawn(i)
						weight_qs[i].put((sw, kw))
						with open(LOG, "a") as f:
							f.write(f"{dt.datetime.now():%Y-%m-%dT%H:%M:%S} !!! worker {i} ({worker_opps[i]}) murió "
							        f"(código 0x{(code or 0) & 0xFFFFFFFF:08X}); reemplazado, la iteración sigue\n")
					if muertos:
						limite_iter = time.time() + WORKER_TIMEOUT
					elif time.time() > limite_iter:
						vivos = sum(p.is_alive() for p in procs)
						raise WorkersPerdidos(f"sin respuesta en {WORKER_TIMEOUT} s ({vivos}/{W} workers vivos)")
			ts += W * R * AR
			stats = {}
			if role in ("striker", "both"):
				stats["s"] = _upd(tr_s, pays, "s")
			if role in ("keeper", "both"):
				stats["k"] = _upd(tr_k, pays, "k")
			pl_, vl_, ent_ = stats["s"] if role in ("striker", "both") else stats["k"]
			it += 1; sc = sum(p["scored"] for p in pays); cc = sum(p["conceded"] for p in pays); alls += sc; allc += cc
			rs_ = sum(p["rew_s"] for p in pays) / W; rk_ = sum(p["rew_k"] for p in pays) / W
			sps = ts / max(time.time() - t0, 1); tstr = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
			hist["ent"].append(ent_); hist["gf"].append(sc); hist["gc"].append(cc)
			extra_txt = f" ent_k={stats['k'][2]:.3f}" if role == "both" else ""
			line = (f"[IT{it:4d}] {tstr} | steps={ts:>10,} | goals {sc}/{cc} (tot {alls}/{allc}) | "
			        f"rew_s={rs_:+6.1f} rew_k={rk_:+6.1f} | pl={pl_:.4f} vl={vl_:.4f} ent={ent_:.3f}{extra_txt} | "
			        f"{sps:,.0f} stp/s | workers={W} | opp=fase-{role}")
			print(line, flush=True)
			with open(LOG, "a") as f:
				f.write(line + "\n")
			if it % cfg["save_every"] == 0:
				_safe_save(striker, os.path.join(md, "striker.npz")); _safe_save(keeper, os.path.join(md, "keeper.npz"))
				ck = f"{run_tag}_IT{it:04d}_s{ts}_{role}"
				_safe_save(striker, os.path.join(ckpt, f"striker_{ck}.npz")); _safe_save(keeper, os.path.join(ckpt, f"keeper_{ck}.npz"))
	except KeyboardInterrupt:
		print("\nInterrumpido — guardando.")
		raise
	finally:
		for wq in weight_qs:
			try:
				wq.put("STOP")
			except Exception:
				pass
		for pr in procs:              # por si alguno quedó colgado
			if pr.is_alive():
				pr.terminate()
		_safe_save(striker, os.path.join(md, "striker.npz")); _safe_save(keeper, os.path.join(md, "keeper.npz"))
		n = len(hist["ent"])          # resumen de la fase para la regla de estancamiento
		if n:
			extra["stats"] = {"its": n, "ent_mean": round(float(sum(hist["ent"])) / n, 4),   # float: numpy
			                  "gf_per_upd": round(float(sum(hist["gf"])) / n, 3),            # float32 no va a JSON
			                  "gc_per_upd": round(float(sum(hist["gc"])) / n, 3)}


def _weights_hash(npz_path):
	"""Huella corta de los pesos de un .npz (sin el estado del optimizador 'opt_*').
	Sirve para verificar en el log que el rol congelado no cambió durante una fase."""
	import hashlib
	import numpy as np
	if not npz_path.exists():
		return "-"
	h = hashlib.sha1()
	with np.load(npz_path) as w:
		for k in sorted(k for k in w.files if not k.startswith("opt_")):
			h.update(k.encode()); h.update(w[k].tobytes())
	return h.hexdigest()[:10]


PLATEAU_WINDOW = 3        # fases del mismo rol (y misma configuración) que se comparan
PLATEAU_MIN_ENT_DROP = 0.01
PLATEAU_MIN_GAIN = {"striker": 0.10, "keeper": 0.30}   # goles/actualización a favor / en contra


def _check_plateau(meta, role, log_file):
	"""Regla automática de estancamiento (2026-10-17). Compara las últimas PLATEAU_WINDOW fases
	del rol con la MISMA configuración (rivales + entropía): si de la primera a la última la
	entropía bajó menos de PLATEAU_MIN_ENT_DROP y la métrica del rol no mejoró al menos
	PLATEAU_MIN_GAIN (striker: más goles a favor; keeper: menos goles en contra), lo marca en el
	log ("!!! ESTANCAMIENTO") y en run.json ("plateaus"). Solo avisa; no cambia el entrenamiento."""
	if role not in PLATEAU_MIN_GAIN:
		return
	last = meta["phases"][-1]
	same = [p for p in meta["phases"] if p["role"] == role and p.get("stats")
	        and p.get("opponents") == last.get("opponents") and p.get("entropy_coef") == last.get("entropy_coef")]
	if len(same) < PLATEAU_WINDOW:
		return
	a, b = same[-PLATEAU_WINDOW]["stats"], same[-1]["stats"]
	ent_drop = a["ent_mean"] - b["ent_mean"]
	gain = (b["gf_per_upd"] - a["gf_per_upd"]) if role == "striker" else (a["gc_per_upd"] - b["gc_per_upd"])
	if ent_drop < PLATEAU_MIN_ENT_DROP and gain < PLATEAU_MIN_GAIN[role]:
		msg = (f"{role}: en {PLATEAU_WINDOW} fases la entropía bajó {ent_drop:+.3f} y la métrica mejoró "
		       f"{gain:+.2f} goles/actualización (umbral {PLATEAU_MIN_GAIN[role]})")
		meta.setdefault("plateaus", []).append({"time": dt.datetime.now().isoformat(timespec="seconds"),
		                                        "role": role, "cycle": last["cycle"], "detail": msg})
		_log(log_file, f"!!! ESTANCAMIENTO {msg}")


def _log(log_file, text):
	line = f"{dt.datetime.now():%Y-%m-%dT%H:%M:%S} {text}"
	print(line, flush=True)
	with open(log_file, "a", encoding="utf-8") as f:
		f.write(line + "\n")


def main():
	ap = argparse.ArgumentParser(description="Entrenamiento PPO del equipo DVF (alternado striker/keeper).")
	ap.add_argument("--run", default=dt.datetime.now().strftime("run_%Y%m%d_%H%M"),
	                help="nombre de la corrida -> models/runs/<run>/")
	ap.add_argument("--opponents", nargs="+", default=["NormalTeam", "DVF", "DVF_v2"],
	                help="rivales (soccer_team_<nombre>), repartidos entre los workers")
	ap.add_argument("--workers", type=int, default=14, help="simulaciones en paralelo (default 14)")
	ap.add_argument("--worker-rollout", type=int, default=256, help="decisiones por worker y actualización")
	ap.add_argument("--mode", choices=["alternate", "both"], default="alternate",
	                help="alternate = un rol por fase (pedido de la cátedra); both = los dos a la vez")
	ap.add_argument("--phase-steps", type=int, default=1_000_000, help="pasos de simulación por fase")
	ap.add_argument("--first", choices=["striker", "keeper"], default="striker", help="rol de la primera fase")
	ap.add_argument("--cycles", type=int, default=0, help="ciclos striker+keeper (0 = hasta --hours)")
	ap.add_argument("--hours", type=float, default=0.0, help="no arrancar fases nuevas después de este tiempo")
	ap.add_argument("--until", help="hora límite absoluta (ISO, p. ej. 2026-10-18T07:00): no arrancar "
	                                "fases nuevas después; sobrevive a reinicios del supervisor")
	ap.add_argument("--init-from", type=Path, help="carpeta con striker.npz/keeper.npz para arrancar")
	ap.add_argument("--save-every", type=int, default=20, help="checkpoint cada N actualizaciones")
	# 2026-10-17: configuración por rol (el striker se estancó contra los tres rivales con 0.05)
	ap.add_argument("--striker-opponents", nargs="+", help="rivales en las fases del striker (default: --opponents)")
	ap.add_argument("--keeper-opponents", nargs="+", help="rivales en las fases del keeper (default: --opponents)")
	ap.add_argument("--striker-entropy", type=float, help="coef. de entropía del striker (default: el general)")
	ap.add_argument("--keeper-entropy", type=float, help="coef. de entropía del keeper (default: el general)")
	args = ap.parse_args()
	if args.cycles <= 0 and args.hours <= 0 and not args.until:
		ap.error("indicá --cycles, --hours o --until")

	run_dir = ROOT / "models" / "runs" / args.run
	run_dir.mkdir(parents=True, exist_ok=True)
	log_file = run_dir / "training.log"
	meta_file = run_dir / "run.json"
	if args.init_from:
		for role in ("striker", "keeper"):
			src, dst = args.init_from / f"{role}.npz", run_dir / f"{role}.npz"
			if src.exists() and not dst.exists():
				shutil.copy2(src, dst)

	meta = json.loads(meta_file.read_text()) if meta_file.exists() else {"phases": []}
	meta["config"] = {**vars(args), "init_from": str(args.init_from) if args.init_from else None,
	                  "jitter_px": JITTER, "still_speed": STILL_SPEED, "hparams": HPARAMS,
	                  "reward": "dvf_rewards.compute_reward", "cpu_count": os.cpu_count()}

	# train() del curso arma modelos, optimizadores y el resume; el bucle lo pone _run_parallel_dvf.
	orig_run_parallel = S._run_parallel
	state = {"role": None, "extra": {}}
	S._run_parallel = lambda st, kp, tr_s, tr_k, fn, cfg: _run_parallel_dvf(st, kp, tr_s, tr_k, fn, cfg,
	                                                                        state["role"], state["extra"])
	ent_default = HPARAMS["entropy_coef"]
	role_cfg = {   # rivales y entropía de cada fase según el rol que entrena
		"striker": (args.striker_opponents or args.opponents,
		            args.striker_entropy if args.striker_entropy is not None else ent_default),
		"keeper": (args.keeper_opponents or args.opponents,
		           args.keeper_entropy if args.keeper_entropy is not None else ent_default),
		"both": (args.opponents, ent_default),
	}
	ent_by_role = {"striker": role_cfg["striker"][1], "keeper": role_cfg["keeper"][1]}

	order = ["striker", "keeper"] if args.first == "striker" else ["keeper", "striker"]
	roles = order if args.mode == "alternate" else ["both"]
	t_start = time.time()
	until_file = run_dir / "until.txt"

	def _deadline():
		"""Hora límite vigente (timestamp o None), releída antes de cada fase.
		2026-10-17: si existe models/runs/<run>/until.txt (una fecha ISO), MANDA sobre --until y
		--hours: así la hora de fin se puede mover sin cortar el entrenamiento."""
		txt = until_file.read_text(encoding="utf-8").strip() if until_file.exists() else ""
		if txt:
			return dt.datetime.fromisoformat(txt).timestamp()
		d = t_start + args.hours * 3600 if args.hours > 0 else None
		if args.until:                # límite absoluto (gana el más temprano)
			u = dt.datetime.fromisoformat(args.until).timestamp()
			d = min(d, u) if d else u
		return d

	if _deadline() and time.time() >= _deadline():
		_log(log_file, "=== hora límite ya pasada: no se arranca ninguna fase ===")
		return
	# 2026-10-17: al relanzar una corrida, la alternancia SIGUE desde la última fase completa de
	# run.json (antes arrancaba siempre por --first: tras una fase de striker venía otra de
	# striker). Una fase cortada a la mitad no figura en run.json, así que se repite.
	last = meta["phases"][-1] if meta["phases"] else None
	if last and last["role"] in roles:
		idx = (roles.index(last["role"]) + 1) % len(roles)
		cycle = last["cycle"] + (1 if idx == 0 else 0)
	else:
		idx, cycle = 0, (last["cycle"] + 1 if last else 1)
	cycles_limit = (cycle + args.cycles - (1 if idx == 0 else 0)) if args.cycles else 0
	fallas_esta_vez = 0
	_log(log_file, f"=== DVF run '{args.run}' | modo {args.mode} | rivales {args.opponents} | "
	               f"{args.workers} workers | {args.phase_steps:,} pasos/fase | ruido saque ±{JITTER} px | "
	               f"sigue en ciclo {cycle} {roles[idx]} ===")
	try:
		while True:
			if cycles_limit and cycle > cycles_limit:
				break
			dl = _deadline()
			if dl and time.time() >= dl:
				break
			role = roles[idx]
			state["role"] = role
			t0 = time.time()
			_log(log_file, f"--- ciclo {cycle} | entrena: {role} ---")
			while True:
				try:
					state["extra"] = {"ent": ent_by_role}
					S.train(compute_reward, total_steps=args.phase_steps, opponent=list(role_cfg[role][0]),
					        resume=True, parallel=True, workers=args.workers,
					        worker_rollout=args.worker_rollout, save_every=args.save_every,
					        model_dir=str(run_dir), log_file=str(log_file), **HPARAMS)
					break
				except WorkersPerdidos as e:
					# La fase se repite desde el último guardado (resume=True lee los .npz)
					meta.setdefault("interruptions", []).append(
						{"time": dt.datetime.now().isoformat(timespec="seconds"), "cycle": cycle,
						 "role": role, "reason": str(e)})
					meta_file.write_text(json.dumps(meta, indent=2))
					# 2026-10-17: el tope cuenta solo los reintentos de ESTE lanzamiento (antes contaba
					# toda la historia de run.json y, tras 5 en la noche, cualquier falla cortaba todo)
					fallas_esta_vez += 1
					if fallas_esta_vez > MAX_REINTENTOS:
						_log(log_file, f"!!! workers perdidos otra vez ({e}); demasiados reintentos, se corta")
						raise
					_log(log_file, f"!!! workers perdidos ({e}); se reinicia la fase {role} desde el último guardado")
			hs, hk = _weights_hash(run_dir / "striker.npz"), _weights_hash(run_dir / "keeper.npz")
			_log(log_file, f"--- fin ciclo {cycle} {role}: {(time.time() - t0) / 60:.1f} min | "
			               f"pesos striker={hs} keeper={hk} ---")
			meta["phases"].append({"cycle": cycle, "role": role, "steps": args.phase_steps,
			                       "start": dt.datetime.fromtimestamp(t0).isoformat(timespec="seconds"),
			                       "hours": round((time.time() - t0) / 3600, 3),
			                       "hash_striker": hs, "hash_keeper": hk,
			                       "opponents": list(role_cfg[role][0]), "entropy_coef": role_cfg[role][1],
			                       "stats": state["extra"].get("stats", {})})
			_check_plateau(meta, role, log_file)
			meta["total_hours"] = round(sum(p["hours"] for p in meta["phases"]), 3)
			meta_file.write_text(json.dumps(meta, indent=2))
			idx = (idx + 1) % len(roles)
			if idx == 0:
				cycle += 1
	except KeyboardInterrupt:
		pass
	finally:
		S._run_parallel = orig_run_parallel
		meta["total_hours"] = round(sum(p["hours"] for p in meta["phases"]), 3)
		meta_file.write_text(json.dumps(meta, indent=2))
		_log(log_file, f"=== fin: {len(meta['phases'])} fases, {meta['total_hours']} h acumuladas en esta corrida ===")


if __name__ == "__main__":
	main()
