#!/usr/bin/env python3
"""
Genera la planilla de metadata de la entrega ML a partir de las corridas (DVF, 2026-10-17).

Lee models/runs/<run>/run.json (horas, CPU, épocas) y models/runs/<run>/striker.npz (capas y
neuronas) y escribe entrega/metadata_DVF.md y entrega/metadata_DVF.csv con las columnas de la
planilla del curso: Team, horas de entrenamiento, CPU/GPU, épocas, capas, neuronas, modelos
entrenados, ideas creativas. Elo NO se llena (decisión del equipo, ninguna planilla lo tiene).

Uso:
    python scripts/metadata_entrega.py noche1            # una corrida
    python scripts/metadata_entrega.py noche1 noche2     # suma las horas de varias corridas
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

# Ideas creativas (texto para la planilla; editar acá si se agrega algo nuevo).
IDEAS = ("Recompensa propia (dvf_rewards.py): eje de orientación corregido, recompensas de "
         "orientación escaladas por velocidad (sin premio por quedarse quieto), arquero parado "
         "en la trayectoria del tiro, malus por pelota trabada en esquinas; entrenamiento "
         "alternado striker/keeper contra NormalTeam y nuestros equipos rule-based v1/v2.3, con "
         "ruido en el saque, exploración por rol y detección automática de estancamiento.")


def _red(npz_path):
	"""(capas, neuronas) contando las capas densas del modelo: ocultas + capa de salida.

	Las cabezas fb/lr/turn/val salen todas de la última oculta, así que cuentan como UNA capa
	de salida; las neuronas son la suma de todos los sesgos (256 + 128 + 3 + 3 + 3 + 1 = 394).
	"""
	z = np.load(npz_path)
	biases = {k[:-2]: z[k].shape[0] for k in z.files if k.endswith("_b")}
	hidden = [k for k in biases if k.startswith("h")]
	return len(hidden) + 1, sum(biases.values())


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("runs", nargs="+", help="corridas en models/runs/ (se suman las horas)")
	ap.add_argument("--team", default="DVF")
	ap.add_argument("--out-dir", type=Path, default=ROOT / "entrega")
	args = ap.parse_args()

	hours, cpus, epochs, n_phases = 0.0, set(), set(), 0
	for run in args.runs:
		meta = json.loads((ROOT / "models" / "runs" / run / "run.json").read_text(encoding="utf-8"))
		hours += float(meta.get("total_hours", 0))
		cpus.add(meta["config"].get("cpu_count"))
		epochs.add(meta["config"]["hparams"]["epochs"])
		n_phases += len(meta.get("phases", []))
	layers, neurons = _red(ROOT / "models" / "runs" / args.runs[-1] / "striker.npz")

	row = {
		"Team": args.team,
		"horas de entrenamiento": f"{hours:.1f}",
		"CPU/GPU": f"CPU ({', '.join(str(c) for c in sorted(c for c in cpus if c))} núcleos), sin GPU",
		"épocas": "/".join(str(e) for e in sorted(epochs)),
		"capas": layers,
		"neuronas": neurons,
		# Dos redes (striker + keeper) que se entregan juntas; las fases son sesiones de
		# entrenamiento alternadas, no modelos distintos.
		"modelos entrenados": f"2 (striker + keeper), {n_phases} fases alternadas",
		"ideas creativas": IDEAS,
	}

	args.out_dir.mkdir(parents=True, exist_ok=True)
	with open(args.out_dir / f"metadata_{args.team}.csv", "w", encoding="utf-8-sig", newline="") as f:
		w = csv.DictWriter(f, fieldnames=list(row))
		w.writeheader()
		w.writerow(row)
	md = ["| campo | valor |", "|---|---|"] + [f"| {k} | {v} |" for k, v in row.items()]
	(args.out_dir / f"metadata_{args.team}.md").write_text(
		f"# Metadata ML — {args.team}\n\nCorridas: {', '.join(args.runs)}\n\n" + "\n".join(md) + "\n",
		encoding="utf-8")
	for k, v in row.items():
		print(f"{k:24} {v}")
	print(f"\nEscrito en {args.out_dir / f'metadata_{args.team}.md'} y .csv")


if __name__ == "__main__":
	main()
