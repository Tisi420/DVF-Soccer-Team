#!/usr/bin/env python3
"""
Verifica que una PC esté lista para entrenar y evaluar el DL de DVF (sesión 61).

Pensado para Diego y Fernando (y para la IA que los ayude): correrlo ANTES de entrenar. Revisa:

  1. Python 3.10 y que se esté usando el venv del proyecto (env\\).
  2. Paquetes y versiones (requirements.txt): numpy < 2.3, tensorflow, pymunk, pygame, ...
  3. Archivos del proyecto: motor del curso, equipos rivales, recompensa, punto de partida de la
     imitación y corrida5.
  4. Imports: motor, entorno de entrenamiento (TensorFlow), recompensa (versión) y equipo DL.
  5. Un partido corto sin ventana del equipo DL contra la v2.3 (benchmark, 20 s).
  6. Un entrenamiento mínimo (2 workers, 2 iteraciones por fase) en una corrida temporal que
     después se borra. Prueba spawn, workers, guardado y run.json.

Al final: tabla OK / AVISO / FALLA, con qué hacer en cada caso. Código de salida 1 si algo falló.

    env\\Scripts\\python.exe scripts\\verificar_entorno.py            # todo (~1-2 min)
    env\\Scripts\\python.exe scripts\\verificar_entorno.py --rapido   # sin partido ni entrenamiento
"""
import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
resultados = []          # (estado, chequeo, detalle)


def anotar(estado, chequeo, detalle=""):
	resultados.append((estado, chequeo, detalle))
	print(f"[{estado:5}] {chequeo}{' — ' + detalle if detalle else ''}", flush=True)


def version_tuple(v):
	out = []
	for p in str(v).split("."):
		num = "".join(ch for ch in p if ch.isdigit())
		out.append(int(num) if num else 0)
	return tuple(out)


def chequear_python():
	v = sys.version_info
	if (v.major, v.minor) == (3, 10):
		anotar("OK", "Python", sys.version.split()[0])
	else:
		anotar("AVISO", "Python", f"{sys.version.split()[0]}: el proyecto se probó con 3.10 (TensorFlow y pymunk pueden fallar con otras)")
	en_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
	if en_venv and Path(sys.prefix).resolve() == (ROOT / "env").resolve():
		anotar("OK", "venv del proyecto", sys.prefix)
	elif en_venv:
		anotar("AVISO", "venv", f"se usa {sys.prefix}, no {ROOT / 'env'}")
	else:
		anotar("AVISO", "venv", "no estás en un venv: crealo con 'python -m venv env' y "
		                        "'env\\Scripts\\pip install -r requirements.txt'")


def chequear_paquetes():
	reglas = [  # (módulo, nombre pip, mínimo, máximo excluido)
		("numpy", "numpy", (1, 21), (2, 3)),
		("tensorflow", "tensorflow", (2, 13), None),
		("pymunk", "pymunk", (6, 11), (7, 0)),
		("pygame", "pygame", (2, 6), None),
		("moderngl", "moderngl", (5, 0), None),
		("pyrr", "pyrr", (0, 10), None),
		("cloudpickle", "cloudpickle", (0, 0), None),
		("matplotlib", "matplotlib", (3, 5), None),
	]
	for mod, pip, vmin, vmax in reglas:
		try:
			m = importlib.import_module(mod)
			v = getattr(m, "__version__", None) or getattr(getattr(m, "version", None), "ver", None) or getattr(m, "version", "?")
			vt = version_tuple(v)
			if vt[:2] < vmin or (vmax and vt[:2] >= vmax):
				anotar("FALLA", f"paquete {pip}", f"versión {v}; hace falta >= {'.'.join(map(str, vmin))}"
				       + (f" y < {'.'.join(map(str, vmax))}" if vmax else "") + " (ver requirements.txt)")
			else:
				anotar("OK", f"paquete {pip}", str(v))
		except Exception as e:
			anotar("FALLA", f"paquete {pip}", f"no se puede importar ({e.__class__.__name__}): "
			                                    f"env\\Scripts\\pip install -r requirements.txt")


def chequear_archivos():
	necesarios = ["game/engine.py", "game/keras_core.py", "setup_dl_notebook.py", "dvf_rewards.py",
	              "soccer_team_DVF.py", "soccer_team_DVF_v2.py", "soccer_team_NormalTeam.py", "soccer_team_DVF_DL.py",
	              "scripts/train_dl.py", "scripts/benchmark.py", "scripts/supervisar_entrenamiento.py"]
	faltan = [f for f in necesarios if not (ROOT / f).exists()]
	if faltan:
		anotar("FALLA", "archivos del proyecto", "faltan: " + ", ".join(faltan))
	else:
		anotar("OK", "archivos del proyecto", f"{len(necesarios)} archivos clave presentes")
	imit = ROOT / "models/imitacion/equipo_v23"
	if (imit / "striker.npz").exists() and (imit / "keeper.npz").exists():
		anotar("OK", "punto de partida (imitación v2.3)", str(imit.relative_to(ROOT)))
	else:
		anotar("AVISO", "punto de partida (imitación v2.3)", "falta models/imitacion/equipo_v23: "
		                "copiarlo o regenerarlo con scripts/imitar_equipo.py")
	c5 = ROOT / "models/runs/corrida5"
	if (c5 / "striker.npz").exists():
		meta = json.loads((c5 / "run.json").read_text(encoding="utf-8"))
		anotar("OK", "corrida5", f"{len(meta.get('phases', []))} fases, {meta.get('total_hours', 0)} h")
	else:
		anotar("AVISO", "corrida5", "no está en esta PC (solo hace falta para seguirla desde acá)")
	if " " in str(ROOT):
		anotar("AVISO", "ruta con espacios", f"'{ROOT}': poné las rutas siempre entre comillas")


def chequear_imports():
	try:
		from game.engine import GameEngine  # noqa: F401
		anotar("OK", "motor del juego (game.engine)")
	except Exception as e:
		anotar("FALLA", "motor del juego", repr(e))
	try:
		import dvf_rewards as R
		anotar("OK", "recompensa", f"REWARD_VERSION = {getattr(R, 'REWARD_VERSION', '?')}")
	except Exception as e:
		anotar("FALLA", "recompensa (dvf_rewards.py)", repr(e))
	t0 = time.time()
	try:
		import setup_dl_notebook  # noqa: F401  (importa TensorFlow)
		anotar("OK", "entorno de entrenamiento (setup_dl_notebook + TensorFlow)", f"{time.time() - t0:.0f} s")
	except Exception as e:
		anotar("FALLA", "entorno de entrenamiento", repr(e))
	imit = ROOT / "models/imitacion/equipo_v23"
	if (imit / "striker.npz").exists():
		try:
			os.environ["DVF_DL_STRIKER"] = str(imit / "striker.npz"); os.environ["DVF_DL_KEEPER"] = str(imit / "keeper.npz")
			spec = importlib.util.spec_from_file_location("dl_verif", ROOT / "soccer_team_DVF_DL.py")
			m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
			anotar("OK", "equipo DL carga los .npz", f"corrección violeta {'activa' if m.FIX_Y else 'APAGADA'}")
		except Exception as e:
			anotar("FALLA", "equipo DL (soccer_team_DVF_DL.py)", repr(e))
		finally:
			os.environ.pop("DVF_DL_STRIKER", None); os.environ.pop("DVF_DL_KEEPER", None)


def chequear_partido():
	imit = ROOT / "models/imitacion/equipo_v23"
	if not (imit / "striker.npz").exists():
		anotar("AVISO", "partido sin ventana", "sin modelo para probar")
		return
	env = dict(os.environ, DVF_DL_STRIKER=str(imit / "striker.npz"), DVF_DL_KEEPER=str(imit / "keeper.npz"),
	           PYTHONIOENCODING="utf-8")
	t0 = time.time()
	r = subprocess.run([sys.executable, "scripts/benchmark.py", "soccer_team_DVF_DL", "--vs", "soccer_team_DVF_v2",
	                    "--seeds", "1", "--duration", "20", "--workers", "2"], cwd=ROOT, env=env,
	                   capture_output=True, text=True, encoding="utf-8", errors="replace")
	if r.returncode == 0 and "soccer_team_DVF_v2" in r.stdout and "fallaron" not in r.stdout:
		anotar("OK", "partido sin ventana (benchmark 20 s)", f"{time.time() - t0:.0f} s")
	else:
		anotar("FALLA", "partido sin ventana", (r.stdout + r.stderr)[-400:].replace("\n", " "))


def chequear_entrenamiento():
	imit = ROOT / "models/imitacion/equipo_v23"
	run = f"_verificacion_{os.environ.get('COMPUTERNAME', 'pc')}"
	run_dir = ROOT / "models/runs" / run
	if run_dir.exists():
		shutil.rmtree(run_dir)
	cmd = [sys.executable, "scripts/train_dl.py", "--run", run, "--workers", "2", "--phase-steps", "1024",
	       "--cycles", "1", "--lr", "1e-4", "--opponents", "DVF_v2", "NormalTeam"]
	if (imit / "striker.npz").exists():
		cmd += ["--init-from", str(imit)]
	t0 = time.time()
	r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
	try:
		meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
		fases = meta.get("phases", [])
		if r.returncode == 0 and len(fases) == 2:
			anotar("OK", "entrenamiento mínimo (2 workers, 2 fases)",
			       f"{time.time() - t0:.0f} s, recompensa {fases[-1].get('reward')}, lr {meta['config']['hparams']['lr']}")
		else:
			anotar("FALLA", "entrenamiento mínimo", f"código {r.returncode}, {len(fases)} fases; " + r.stderr[-300:].replace("\n", " "))
	except Exception as e:
		anotar("FALLA", "entrenamiento mínimo", f"{e!r}; " + (r.stdout + r.stderr)[-300:].replace("\n", " "))
	finally:
		shutil.rmtree(run_dir, ignore_errors=True)


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--rapido", action="store_true", help="sin partido ni entrenamiento de prueba")
	args = ap.parse_args()
	print(f"Verificación del entorno DVF en {os.environ.get('COMPUTERNAME', '?')} — {ROOT}\n", flush=True)
	chequear_python()
	chequear_paquetes()
	chequear_archivos()
	chequear_imports()
	if not args.rapido:
		chequear_partido()
		chequear_entrenamiento()
	n = os.cpu_count() or 4
	# Sesión 61: con 10 workers en una PC de 16 núcleos que se está usando, la máquina iba "al palo";
	# 6 (n/2 - 2) dejó la CPU en ~40 %. Hasta 8 si nadie usa la PC.
	anotar("OK", "núcleos", f"{n}: usar --workers {max(1, n // 2 - 2)} si estás usando la PC "
	      f"(hasta {max(1, n // 2)} si nadie la usa), siempre en prioridad baja")
	fallas = [r for r in resultados if r[0] == "FALLA"]
	avisos = [r for r in resultados if r[0] == "AVISO"]
	print(f"\nResumen: {len(resultados) - len(fallas) - len(avisos)} OK, {len(avisos)} avisos, {len(fallas)} fallas.")
	if fallas:
		print("NO entrenar hasta resolver las fallas (ver el detalle arriba y AGENTS.md / docs/CONTEXTO_DL.md).")
		sys.exit(1)
	print("Listo para entrenar. Comandos en AGENTS.md §7.")


if __name__ == "__main__":
	main()
