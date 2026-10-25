#!/usr/bin/env python3
"""
Protocolo de corte de internet (DVF, sesión 58).

Si se corta internet, la sesión con Claude se cae, pero el entrenamiento y los benchmarks son
locales y siguen corriendo. Este script se ocupa de que no se pierda nada y de dejar todo listo
para retomar:

  --vigilar   (modo normal, queda corriendo) cada CADA_S segundos prueba la conexión. Al
              detectar un corte ejecuta "asegurar" y queda esperando. Al volver la conexión lo
              anota, vuelve a asegurar y sigue vigilando.
  --ahora     ejecuta "asegurar" una sola vez (para probarlo o usarlo a mano).

"asegurar" hace, sin frenar ni tocar ningún proceso:
  1. FOTO DEL ESTADO → models/runs/_estado/ESTADO.md: procesos del proyecto vivos (supervisores,
     entrenamientos, evaluadores, benchmarks, partidos en ventana), y por cada corrida: fases,
     horas, última fase, último guardado, última línea del log y hora límite.
  2. RESPALDO LIVIANO → models/runs/_estado/respaldo_<fecha>/: run.json, until.txt y
     supervisor.log de cada corrida, más CHANGELOG.md y PLAN_ENTREGA.md. Los .npz no se copian:
     ya se guardan solos cada 20 iteraciones (escritura atómica) y en checkpoints/.
  3. LIMPIEZA DE LO CORRUPTO:
     - borra los temporales de guardados a medio hacer (*.tmp de más de 5 minutos: un guardado
       atómico tarda < 1 s, así que uno viejo es un resto de un corte);
     - prueba abrir los .npz principales y los checkpoints de las últimas 48 h, cada run.json y
       cada .jsonl de resultados: lo que no abre se MUEVE a models/_cuarentena/<fecha>/ (no se
       borra, por si hace falta revisarlo) y queda anotado.
  4. Anota todo en models/runs/_estado/protocolo.log.

Para retomar con Claude: abrir models/runs/_estado/ESTADO.md (dice qué pasó y qué sigue
corriendo). Ver PROTOCOLO_CORTE.md en la raíz.

    python scripts/protocolo_corte.py --vigilar
    python scripts/protocolo_corte.py --ahora
"""
import argparse
import datetime as dt
import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "models" / "runs"
ESTADO_DIR = RUNS / "_estado"
CUARENTENA = ROOT / "models" / "_cuarentena"
CADA_S = 60
HOSTS = [("api.anthropic.com", 443), ("1.1.1.1", 443), ("8.8.8.8", 53)]


def _ahora():
	return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _log(texto):
	ESTADO_DIR.mkdir(parents=True, exist_ok=True)
	with open(ESTADO_DIR / "protocolo.log", "a", encoding="utf-8") as f:
		f.write(f"{_ahora()} {texto}\n")


def hay_internet():
	"""True si alguno de los hosts responde (conexión TCP, 3 s de espera)."""
	for host, port in HOSTS:
		try:
			with socket.create_connection((host, port), timeout=3):
				return True
		except OSError:
			continue
	return False


def _procesos():
	"""Procesos python del proyecto, clasificados por la línea de comando."""
	ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
	      "Where-Object { $_.CommandLine -like '*praktikum-soccer*' -or $_.CommandLine -like '*run.py*' } | "
	      "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }")
	out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
	filas = []
	for line in out.stdout.splitlines():
		if "\t" not in line:
			continue
		pid, cmd = line.split("\t", 1)
		if "spawn_main" in cmd:
			tipo = "worker"
		elif "supervisar_entrenamiento" in cmd:
			tipo = "supervisor"
		elif "train_dl" in cmd:
			tipo = "entrenamiento"
		elif "evaluar_al_terminar" in cmd:
			tipo = "evaluador"
		elif "benchmark.py" in cmd:
			tipo = "benchmark"
		elif "run.py" in cmd:
			tipo = "partido en ventana"
		elif "protocolo_corte" in cmd:
			tipo = "protocolo de corte"
		else:
			tipo = "otro"
		run = ""
		if "--run " in cmd:
			run = cmd.split("--run ", 1)[1].split()[0]
		filas.append((tipo, pid, run))
	return filas


def _ultima_linea(path):
	try:
		lines = path.read_text(encoding="cp1252", errors="replace").splitlines()
		return lines[-1][:160] if lines else ""
	except OSError:
		return ""


def _npz_ok(path):
	try:
		import numpy as np
		with np.load(path) as z:
			for k in z.files:
				z[k]
		return True
	except Exception:
		return False


def _cuarentena(path, carpeta, motivo, informe):
	dest = carpeta / path.relative_to(ROOT)
	dest.parent.mkdir(parents=True, exist_ok=True)
	shutil.move(str(path), str(dest))
	informe.append(f"- cuarentena: `{path.relative_to(ROOT)}` ({motivo})")


def asegurar(motivo):
	t0 = time.time()
	sello = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
	informe = []
	corridas = sorted(p for p in RUNS.iterdir() if p.is_dir() and not p.name.startswith("_")) if RUNS.exists() else []

	# 2) respaldo liviano
	resp = ESTADO_DIR / f"respaldo_{sello}"
	for run in corridas:
		for nombre in ("run.json", "until.txt", "supervisor.log"):
			src = run / nombre
			if src.exists():
				(resp / run.name).mkdir(parents=True, exist_ok=True)
				shutil.copy2(src, resp / run.name / nombre)
	for nombre in ("CHANGELOG.md", "PLAN_ENTREGA.md"):
		if (ROOT / nombre).exists():
			resp.mkdir(parents=True, exist_ok=True)
			shutil.copy2(ROOT / nombre, resp / nombre)

	# 3) limpieza
	carpeta_q = CUARENTENA / sello
	limite_tmp = time.time() - 300
	for tmp in list((ROOT / "models").rglob("*.tmp")):
		if tmp.stat().st_mtime < limite_tmp:
			tmp.unlink()
			informe.append(f"- borrado temporal viejo: `{tmp.relative_to(ROOT)}`")
	hace_48h = time.time() - 48 * 3600
	for run in corridas:
		candidatos = [run / "striker.npz", run / "keeper.npz"]
		ck = run / "checkpoints"
		if ck.exists():
			candidatos += [p for p in ck.glob("*.npz") if p.stat().st_mtime > hace_48h]
		for p in candidatos:
			# un archivo que se está escribiendo justo ahora no se toca
			if p.exists() and time.time() - p.stat().st_mtime > 10 and not _npz_ok(p):
				_cuarentena(p, carpeta_q, "no abre como .npz", informe)
		rj = run / "run.json"
		if rj.exists():
			try:
				json.loads(rj.read_text(encoding="utf-8"))
			except Exception:
				informe.append(f"- ⚠ `{rj.relative_to(ROOT)}` no es JSON válido: NO se movió (la corrida lo "
				               f"necesita); hay copias en models/runs/_estado/respaldo_*/")
	for jl in list(RUNS.rglob("*.jsonl")):
		if time.time() - jl.stat().st_mtime < 10:
			continue
		try:
			for line in jl.read_text(encoding="utf-8").splitlines():
				if line.strip():
					json.loads(line)
		except Exception:
			_cuarentena(jl, carpeta_q, "resultado cortado a la mitad", informe)

	# 1) foto del estado
	procs = _procesos()
	md = [f"# Estado del proyecto — {_ahora()}", "", f"Motivo: **{motivo}**.", "",
	      "Leer esto al retomar con Claude. El entrenamiento y los benchmarks son locales: un corte "
	      "de internet no los frena. Si la PC no se apagó, lo que figura como vivo sigue corriendo.", "",
	      "## Procesos del proyecto vivos", ""]
	if procs:
		cuenta = {}
		for tipo, pid, run in procs:
			if tipo == "worker":
				cuenta[run or "?"] = cuenta.get(run or "?", 0) + 1
				continue
			md.append(f"- {tipo}{' de ' + run if run else ''}: PID {pid}")
		n_workers = sum(1 for t, _, _ in procs if t == "worker")
		if n_workers:
			md.append(f"- workers de entrenamiento: {n_workers}")
	else:
		md.append("- ninguno")
	md += ["", "## Corridas", "", "| corrida | fases | horas | última fase | último guardado | hora límite |",
	       "|---|---|---|---|---|---|"]
	for run in corridas:
		try:
			meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
			fases = meta.get("phases", [])
			ult = f"ciclo {fases[-1]['cycle']} {fases[-1]['role']}" if fases else "—"
			horas = meta.get("total_hours", 0)
		except Exception:
			fases, ult, horas = [], "run.json ilegible", 0
		npz = run / "striker.npz"
		guard = dt.datetime.fromtimestamp(npz.stat().st_mtime).strftime("%d/%m %H:%M:%S") if npz.exists() else "—"
		until = (run / "until.txt").read_text(encoding="utf-8").strip() if (run / "until.txt").exists() else "—"
		md.append(f"| {run.name} | {len(fases)} | {horas} | {ult} | {guard} | {until} |")
	vivas = sorted({run for t, _, run in procs if t in ("supervisor", "entrenamiento") and run})
	for run in vivas:
		md += ["", f"Última línea del log de **{run}**:", "",
		       "```", _ultima_linea(RUNS / run / "training.log"), "```"]
	md += ["", "## Limpieza", ""] + (informe or ["- nada corrupto"])
	md += ["", f"Respaldo liviano: `models/runs/_estado/respaldo_{sello}/` · cuarentena (si hubo): "
	       f"`models/_cuarentena/{sello}/` · historial: `models/runs/_estado/protocolo.log`.", "",
	       "## Para retomar", "",
	       "1. Abrir esta sesión de Claude (o una nueva) y pedirle que lea `models/runs/_estado/ESTADO.md`.",
	       "2. Si un entrenamiento murió, relanzarlo: retoma desde su último guardado "
	       "(`scripts/lanzar_corrida.ps1 -Run <corrida> -Desacoplado`).",
	       "3. Lo que haya ido a cuarentena se revisa y se borra a mano."]
	ESTADO_DIR.mkdir(parents=True, exist_ok=True)
	(ESTADO_DIR / "ESTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
	_log(f"asegurado ({motivo}) en {time.time() - t0:.1f} s; procesos vivos: {len(procs)}; "
	     f"limpieza: {len(informe)} item(s)")
	return informe


def vigilar():
	_log("vigilante iniciado")
	en_linea = hay_internet()
	corte = None
	_log(f"estado inicial: {'con' if en_linea else 'SIN'} internet")
	if not en_linea:
		corte = time.time()
		asegurar("arranqué sin internet")
	while True:
		time.sleep(CADA_S)
		ahora = hay_internet()
		if en_linea and not ahora:
			# doble chequeo para no disparar por un parpadeo
			time.sleep(15)
			if hay_internet():
				continue
			corte = time.time()
			_log("!!! CORTE DE INTERNET detectado")
			asegurar("corte de internet")
			en_linea = False
		elif not en_linea and ahora:
			dur = (time.time() - corte) / 60 if corte else 0
			_log(f"conexión recuperada tras {dur:.0f} min")
			asegurar(f"conexión recuperada (estuvo cortada {dur:.0f} min)")
			en_linea = True


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	g = ap.add_mutually_exclusive_group(required=True)
	g.add_argument("--vigilar", action="store_true")
	g.add_argument("--ahora", action="store_true")
	args = ap.parse_args()
	if args.ahora:
		informe = asegurar("ejecución manual")
		print((ESTADO_DIR / "ESTADO.md").read_text(encoding="utf-8"))
		return
	vigilar()


if __name__ == "__main__":
	main()
