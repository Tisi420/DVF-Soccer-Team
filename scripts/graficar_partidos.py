#!/usr/bin/env python3
"""
Gráfico de los resultados en PARTIDOS del equipo DL a lo largo del tiempo (DVF, sesión 51).

Junta las evaluaciones con benchmark registradas en CHANGELOG.md (sesiones 26–49), todas CON la
corrección del violeta (las anteriores no son comparables). Muestra el neto por par de partidos
(uno de cada lado) contra NormalTeam, v1 y v2.3, en tres paneles con la misma escala.

    python scripts/graficar_partidos.py   # -> models/runs/_analisis/partidos.png
"""
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "models" / "runs" / "_analisis"

# (fecha y hora, rama, NormalTeam, v1, v2.3). Semillas por lado: 4 hasta las 22:10 y 8 desde las
# 22:15 (las de noche1 se reevaluaron con 4).
EVAL = [
	("2026-10-18 05:59", "noche1", 4.8, -30.5, -42.5),
	("2026-10-18 09:56", "noche1", 171.8, -27.5, -57.5),
	("2026-10-18 16:45", "principal", -7.8, -5.8, -28.0),
	("2026-10-18 17:45", "principal", 1.0, -33.5, -42.8),
	("2026-10-18 18:41", "principal", 6.2, -31.8, -90.8),
	("2026-10-18 19:50", "principal", 1.0, -7.8, -18.8),
	("2026-10-18 20:55", "principal", -0.2, -9.8, -13.0),
	("2026-10-18 22:10", "clon", -4.5, -8.8, -16.8),
	("2026-10-18 23:35", "clon", -4.8, -18.1, -28.1),
	("2026-10-18 23:35", "principal", 3.9, -10.5, -13.1),
	("2026-10-19 00:20", "principal", -0.1, -15.0, -17.9),
	("2026-10-19 00:50", "principal", 3.1, -13.8, -15.0),
	("2026-10-19 01:30", "principal", -18.5, -6.5, -23.1),
	("2026-10-19 02:35", "principal", -9.6, -9.6, -23.9),
	("2026-10-19 03:38", "principal", 1.0, -20.4, -32.4),
	("2026-10-19 04:40", "principal", -6.2, -14.6, -25.0),
]
ELEGIDO = ("2026-10-18 23:36", 0.9, -9.9, -12.6)   # evaluación final, 16 semillas por lado
EVENTOS = [("2026-10-18 18:45", "rivales ponderados"), ("2026-10-18 21:11", "rama del clon")]
TRAMO_0015 = ("2026-10-19 00:57", "2026-10-19 01:33")   # striker con exploración 0,015
RIVALES = ["NormalTeam", "v1 (rule-based)", "v2.3 (rule-based)"]
YMIN, YMAX = -95, 25


def main():
	import matplotlib
	matplotlib.use("Agg")
	import matplotlib.dates as mdates
	import matplotlib.pyplot as plt
	BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#9a998f"
	INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e6e5df"
	t = lambda s: dt.datetime.strptime(s, "%Y-%m-%d %H:%M")
	fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharey=True, gridspec_kw={"wspace": 0.06})
	for i, (ax, rival) in enumerate(zip(axes, RIVALES)):
		ax.axhspan(0, YMAX, color="#f2f7ee", zorder=0)            # zona "le ganamos"
		ax.axhline(0, color=MUTED, lw=1, zorder=1)
		for (cuando, txt) in EVENTOS:
			ax.axvline(t(cuando), color="#cfcdc4", lw=1, ls="--", zorder=1)
			ax.text(t(cuando), YMIN + 3, " " + txt, rotation=90, fontsize=7, color=MUTED, ha="right", va="bottom")
		ax.axvspan(t(TRAMO_0015[0]), t(TRAMO_0015[1]), color="#f6e6dc", zorder=0)
		ax.text(t(TRAMO_0015[1]), YMIN + 3, " exploración 0,015", rotation=90, fontsize=7, color=MUTED,
		        ha="left", va="bottom")
		for rama, color, estilo in (("principal", BLUE, "-"), ("clon", ORANGE, "--"), ("noche1", GRAY, ":")):
			pts = [(t(e[0]), e[2 + i]) for e in EVAL if e[1] == rama]
			xs, ys = [p[0] for p in pts], [max(min(p[1], YMAX - 2), YMIN + 2) for p in pts]
			ax.plot(xs, ys, estilo, color=color, lw=2, marker="o", ms=6, markeredgecolor="white",
			        markeredgewidth=1, label={"principal": "rama principal (PPO)", "clon": "rama del clon",
			                                  "noche1": "noche1"}[rama], zorder=3)
			for x, y in pts:
				if y > YMAX:
					ax.annotate(f"↑ {y:+.0f}", (x, YMAX - 2), textcoords="offset points", xytext=(4, -12),
					            fontsize=8, color=MUTED)
		ax.plot(t(ELEGIDO[0]), ELEGIDO[1 + i], marker="*", ms=17, color=INK, markeredgecolor="white", zorder=4,
		        label="modelo elegido (16 semillas)")
		ax.annotate(f"{ELEGIDO[1 + i]:+.1f}", (t(ELEGIDO[0]), ELEGIDO[1 + i]), textcoords="offset points",
		            xytext=(8, 6), fontsize=9, color=INK, fontweight="bold")
		ax.set_title(f"contra {rival}", loc="left", color=INK, fontsize=11)
		ax.set_ylim(YMIN, YMAX)
		ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
		ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%H:%M"))
		ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[6, 12, 18, 0]))
		for s in ("top", "right"):
			ax.spines[s].set_visible(False)
		for s in ("left", "bottom"):
			ax.spines[s].set_color(GRID)
		ax.tick_params(colors=MUTED, labelsize=8)
	axes[0].set_ylabel("neto por par de partidos (DL − rival)", color=MUTED)
	axes[2].text(0.98, 0.97, "zona verde: le ganamos", transform=axes[2].transAxes, fontsize=8, color="#4f7a3a",
	             va="top", ha="right")
	h, l = axes[0].get_legend_handles_labels()
	fig.legend(h, l, loc="lower center", ncol=4, frameon=False, labelcolor=INK, bbox_to_anchor=(0.5, -0.04))
	fig.subplots_adjust(top=0.84)
	fig.suptitle("Equipo DL en partidos reales (benchmark con corrección del violeta)", x=0.01, y=0.99, ha="left",
	             color=INK, fontsize=13)
	fig.text(0.01, 0.925, "4 semillas por lado hasta las 22:10, 8 desde las 22:15; la estrella usa 16. "
	         "Líneas punteadas y franja: cambios de configuración.", fontsize=8.5, color=MUTED)
	OUT.mkdir(parents=True, exist_ok=True)
	fig.savefig(OUT / "partidos.png", dpi=130, bbox_inches="tight")
	print(f"gráfico en {OUT / 'partidos.png'}")


if __name__ == "__main__":
	main()
