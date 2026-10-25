#!/usr/bin/env python3
"""
Arma un .zip del proyecto para pasárselo al equipo (DVF, sesión 43).

Incluye código, documentación, entregas, logs, evaluaciones y los modelos finales de cada corrida,
más los pares candidatos en models/candidatos/. Deja afuera lo que se regenera o pesa demasiado:
env/ (se reinstala con requirements.txt), __pycache__/, los checkpoints intermedios
(models/runs/*/checkpoints, ~1,3 GB) y la propia carpeta compartir/.

    python scripts/empaquetar.py              # -> compartir/DVF_robotic_soccer_<fecha>.zip (~25 MB)
    python scripts/empaquetar.py --completo   # + checkpoints intermedios (~1,3 GB)
"""
import datetime as dt
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Sesión 63: también .git (si se sube a GitHub) y _cuarentena (archivos dañados del protocolo de corte)
FUERA_DIRS = {"env", "__pycache__", "checkpoints", "compartir", ".ipynb_checkpoints", ".git", "_cuarentena"}
# Pares striker+keeper evaluados en las sesiones 36–38 (etiqueta -> corrida, tag del checkpoint)
CANDIDATOS = {
	"corrida2_c12_1645": ("corrida2", "20261018_163446"),
	"corrida2_c19_1950": ("corrida2", "20261018_191858"),
	"corrida2_c23_2058_ppo": ("corrida2", "20261018_204924"),
	"corrida2_c26_2210_clon": ("corrida2", "20261018_220044"),
}
# Sesión 63: pares guardados fuera de checkpoints/ (etiqueta -> ruta del striker; el keeper es igual
# con _keeper). El mejor medido de corrida5 (1 min + gol de oro: NT 30-0-2, v1 27-0-5, v2.3 7-3-22).
CANDIDATOS_DIRECTOS = {
	"corrida5_20261024_1401_MEJOR": "models/runs/corrida5/chequeos/20261024_1401_striker.npz",
	"corrida5_20261025_1302": "models/runs/corrida5/monitoreo/1302_striker.npz",
}


def main():
	import argparse
	ap = argparse.ArgumentParser()
	# --completo: incluye también los checkpoints intermedios (todo menos env/ y cachés).
	# env/ nunca va: tiene rutas absolutas de esta PC y se rearma con pip install -r requirements.txt.
	ap.add_argument("--completo", action="store_true")
	args = ap.parse_args()
	fuera = FUERA_DIRS - {"checkpoints"} if args.completo else FUERA_DIRS
	out_dir = ROOT / "compartir"
	out_dir.mkdir(exist_ok=True)
	sufijo = "_completo" if args.completo else ""
	zpath = out_dir / f"DVF_robotic_soccer_{dt.datetime.now():%Y-%m-%d_%H%M}{sufijo}.zip"
	n = 0
	with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
		for p in sorted(ROOT.rglob("*")):
			rel = p.relative_to(ROOT)
			if not p.is_file() or any(part in fuera for part in rel.parts) or p.suffix == ".pyc":
				continue
			z.write(p, Path("praktikum-soccer") / rel); n += 1
		for etiqueta, (run, tag) in CANDIDATOS.items():
			for rol in ("striker", "keeper"):
				src = ROOT / "models" / "runs" / run / "checkpoints" / f"{rol}_{tag}_IT0180_s1474560_keeper.npz"
				if src.exists():
					z.write(src, Path("praktikum-soccer") / "models" / "candidatos" / f"{etiqueta}_{rol}.npz"); n += 1
		for etiqueta, rel_s in CANDIDATOS_DIRECTOS.items():
			for rol in ("striker", "keeper"):
				src = ROOT / rel_s.replace("_striker.npz", f"_{rol}.npz")
				if src.exists():
					z.write(src, Path("praktikum-soccer") / "models" / "candidatos" / f"{etiqueta}_{rol}.npz"); n += 1
	print(f"{n} archivos -> {zpath} ({zpath.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
	main()
