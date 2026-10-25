#!/usr/bin/env python3
"""
Curva de entrenamiento de una corrida de scripts/train_dl.py (equipo DVF, 2026-10-17).

Misma figura que la celda "Training Curves" de "Soccer DeepLearning.ipynb" (recompensa, goles,
pérdidas PPO y entropía), pero leyendo el log de una corrida. Las bandas de fondo marcan las
fases (fase-striker / fase-keeper). Es el training_curve.png que se entrega con la red.

    python scripts/plot_training.py noche1                 # -> models/runs/noche1/training_curve.png
    python scripts/plot_training.py noche1 --out training_curve.png
"""
import argparse
import re
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                     # sin ventana: solo genera el PNG
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent

# Mismas expresiones que la celda del notebook (compatibles con el log de train_dl.py).
_ROW = re.compile(
	r"\[(?:R|IT)\s*(\d+)\].*?(?:(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d).*?)?"
	r"goals\s+(\d+)/(\d+).*?rew_s=\s*([-+]?[\d.]+)\s+rew_k=\s*([-+]?[\d.]+).*?"
	r"pl=([-+]?[\d.]+)\s+vl=([\d.]+)\s+ent=([\d.]+)(?:.*?opp=(\S+))?")


def main():
	ap = argparse.ArgumentParser(description="Curva de entrenamiento de una corrida.")
	ap.add_argument("run", help="nombre de la corrida (models/runs/<run>/training.log)")
	ap.add_argument("--out", type=Path, help="PNG de salida (default: models/runs/<run>/training_curve.png)")
	args = ap.parse_args()
	log = ROOT / "models" / "runs" / args.run / "training.log"
	out = args.out or log.with_name("training_curve.png")

	rows = [m.groups() for m in map(_ROW.search, log.read_text(encoding="utf-8", errors="replace").splitlines()) if m]
	if not rows:
		raise SystemExit(f"Sin filas [IT n] en {log}")
	x = [datetime.fromisoformat(r[1]) for r in rows]
	sc = [int(r[2]) for r in rows]; cc = [int(r[3]) for r in rows]
	rs = [float(r[4]) for r in rows]; rk = [float(r[5]) for r in rows]
	pl = [float(r[6]) for r in rows]; vl = [float(r[7]) for r in rows]; ent = [float(r[8]) for r in rows]
	phase = [r[9] or "?" for r in rows]
	n = len(rows)

	palette = {"fase-striker": "#2196F3", "fase-keeper": "#FF9800", "fase-both": "#4CAF50"}

	def bands(ax):
		i = 0
		while i < n:
			j = i
			while j < n and phase[j] == phase[i]:
				j += 1
			ax.axvspan(mdates.date2num(x[i]), mdates.date2num(x[j - 1]),
			           color=palette.get(phase[i], "#9E9E9E"), alpha=0.10, zorder=0)
			i = j

	fig, ax = plt.subplots(2, 2, figsize=(14, 9))
	fig.suptitle(f"Entrenamiento PPO DVF — corrida {args.run} "
	             f"(fases alternadas striker/keeper, rivales NormalTeam/v1/v2.3)", fontsize=13)
	for a in ax.flat:
		bands(a)
	ax[0, 0].plot(x, rs, label="Striker", alpha=.8); ax[0, 0].plot(x, rk, label="Keeper", alpha=.8)
	ax[0, 0].set_title("Recompensa por actualización")
	w = max(1, n // 20)
	scs = np.convolve(sc, np.ones(w) / w, "valid"); ccs = np.convolve(cc, np.ones(w) / w, "valid")
	xs = x[w // 2: w // 2 + len(scs)]
	ax[0, 1].plot(xs, scs, label="A favor", color="green"); ax[0, 1].plot(xs, ccs, label="En contra", color="red")
	ax[0, 1].set_title("Goles por actualización (suavizado)")
	ax[1, 0].plot(x, pl, label="Policy loss", alpha=.8); ax[1, 0].plot(x, vl, label="Value loss", alpha=.8)
	ax[1, 0].set_title("Pérdidas PPO (del rol que entrena)")
	ax[1, 1].plot(x, ent, color="purple", alpha=.8); ax[1, 1].set_title("Entropía de la política (rol que entrena)")
	for a in ax.flat:
		a.set_xlabel("Hora"); a.grid(True, alpha=.3)
		if a.get_legend_handles_labels()[1]:
			a.legend()
		a.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
		plt.setp(a.xaxis.get_majorticklabels(), rotation=30, ha="right")
	order = list(dict.fromkeys(phase))
	fig.legend(handles=[mpatches.Patch(color=palette.get(p, "#9E9E9E"), alpha=.4, label=p) for p in order],
	           loc="lower center", ncol=len(order), title="Fase", bbox_to_anchor=(.5, -.02))
	plt.tight_layout(rect=[0, .05, 1, 1])
	fig.savefig(out, dpi=120, bbox_inches="tight")
	print(f"{n} actualizaciones | goles a favor {sum(sc)} / en contra {sum(cc)} | curva -> {out}")


if __name__ == "__main__":
	main()
