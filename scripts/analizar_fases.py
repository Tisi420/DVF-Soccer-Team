#!/usr/bin/env python3
"""
Análisis por fase de todo el entrenamiento DL (DVF, sesión 21).

Lee training.log de una o más corridas, arma una fila por fase (rol, hora, iteraciones, goles a
favor / en contra por actualización, % de goles a favor, entropía) y las agrupa en ETAPAS: tramos
con la misma recompensa y los mismos rivales, que son los únicos comparables entre sí (contra
NormalTeam solo se hacen muchos más goles que contra la mezcla).

Escribe models/runs/_analisis/fases.md (tabla por etapa y por fase) y fases.png (% de goles a
favor y entropía por fase, con las etapas sombreadas).

    python scripts/analizar_fases.py                   # noche1 + corrida2
    python scripts/analizar_fases.py noche1 corrida2
"""
import argparse
import datetime as dt
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "models" / "runs" / "_analisis"

HEADER = re.compile(r"=== PARALLEL run (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \| .*? \| opp (\{.*?\}) \| entrena (\w+)")
IT = re.compile(r"^\[IT\s+(\d+)\] \S+ \| steps=.*? \| goals (\d+)/(\d+) .*? ent=([\d.]+)")
FIN = re.compile(r"--- fin ciclo (\d+) (\w+):")

# Etapas: (nombre corto, descripción, corrida, desde, hasta). Mismo criterio que el CHANGELOG.
ETAPAS = [
	("A", "v1 · los dos vs mezcla · entropía 0,05", "noche1", "2026-10-17 00:00:00", "2026-10-17 23:33:50"),
	("B", "v1 · striker solo vs NormalTeam (0,01) · keeper mezcla (0,05)", "noche1",
	 "2026-10-17 23:33:50", "2026-10-18 06:00:00"),
	("C", "v2 (castigo por gol recibido) · striker solo NT (0,01) · keeper mezcla (0,02)", "noche1",
	 "2026-10-18 06:00:00", "2026-10-18 23:59:59"),
	# Sesión 51: D se partió en D (PPO) y E (rama del clon), y se agregaron corrida3 y corrida4.
	("D", "v3 · los dos vs mezcla · entropía 0,02 → 0,01 · rivales ponderados desde 18:45", "corrida2",
	 "2026-10-18 00:00:00", "2026-10-18 21:11:00"),
	("E", "rama del clon (striker imitando a v2.3) + PPO", "corrida2",
	 "2026-10-18 21:11:00", "2026-10-20 23:59:59"),
	("F", "rama PPO (desde corrida2 ciclo 23) · rivales ponderados · 0,01 (0,015 de 00:57 a 01:33)", "corrida3",
	 "2026-10-18 00:00:00", "2026-10-20 23:59:59"),
	("G", "entrenamiento suave desde el modelo elegido · 6 workers", "corrida4",
	 "2026-10-18 00:00:00", "2026-10-20 23:59:59"),
]


def _etapa(run, t):
	for e in ETAPAS:
		if e[2] == run and dt.datetime.fromisoformat(e[3]) <= t < dt.datetime.fromisoformat(e[4]):
			return e[0]
	return "?"


def leer(run):
	"""Lista de fases (dict) de models/runs/<run>/training.log, en orden."""
	fases, cur = [], None
	log = ROOT / "models" / "runs" / run / "training.log"
	for line in log.read_text(encoding="cp1252", errors="replace").splitlines():
		m = HEADER.search(line)
		if m:
			t = dt.datetime.fromisoformat(m.group(1))
			cur = {"run": run, "t": t, "role": m.group(3), "opp": "NT" if m.group(2) == "{'NormalTeam': 14}" else "mezcla",
			       "gf": 0, "gc": 0, "its": 0, "ent": [], "ciclo": None, "completa": False, "etapa": _etapa(run, t)}
			fases.append(cur)
			continue
		if cur is None:
			continue
		m = IT.match(line)
		if m:
			cur["its"] += 1
			cur["gf"] += int(m.group(2)); cur["gc"] += int(m.group(3))
			cur["ent"].append(float(m.group(4)))
			continue
		m = FIN.search(line)
		if m and m.group(2) == cur["role"]:
			cur["ciclo"], cur["completa"] = int(m.group(1)), True
	for f in fases:
		n = max(f["its"], 1)
		f["gf_u"], f["gc_u"] = f["gf"] / n, f["gc"] / n
		f["pct"] = 100 * f["gf"] / (f["gf"] + f["gc"]) if f["gf"] + f["gc"] else float("nan")
		f["ent_m"] = statistics.mean(f["ent"]) if f["ent"] else float("nan")
	return [f for f in fases if f["its"] >= 20]     # descarta arranques cortados al toque


def _tendencia(vals):
	"""Primer tercio vs último tercio de una etapa (cambio en unidades de la métrica)."""
	if len(vals) < 3:
		return None
	k = max(1, len(vals) // 3)
	return statistics.mean(vals[-k:]) - statistics.mean(vals[:k])


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("runs", nargs="*", default=["noche1", "corrida2", "corrida3", "corrida4"])
	args = ap.parse_args()
	fases = [f for r in args.runs if (ROOT / "models" / "runs" / r / "training.log").exists() for f in leer(r)]
	OUT.mkdir(parents=True, exist_ok=True)

	md = ["# Análisis por fase del entrenamiento DL", "",
	      f"Generado {dt.datetime.now():%Y-%m-%d %H:%M} por scripts/analizar_fases.py · corridas: {', '.join(args.runs)}.",
	      "Por actualización = por iteración de PPO (14 workers × 256 pasos). Solo son comparables las fases",
	      "de la misma etapa (misma recompensa y mismos rivales).", "",
	      "## Por etapa", "",
	      "| etapa | descripción | rol | fases | goles a favor / act. | en contra / act. | % a favor | Δ % (1er → último tercio) | entropía (1ª → última fase) |",
	      "|---|---|---|---|---|---|---|---|---|"]
	for e in ETAPAS:
		for role in ("striker", "keeper"):
			fs = [f for f in fases if f["etapa"] == e[0] and f["role"] == role]
			if not fs:
				continue
			gf = sum(f["gf"] for f in fs); gc = sum(f["gc"] for f in fs); its = sum(f["its"] for f in fs)
			d = _tendencia([f["pct"] for f in fs])
			md.append(f"| {e[0]} | {e[1]} | {role} | {len(fs)} | {gf / its:.2f} | {gc / its:.2f} | "
			          f"{100 * gf / max(gf + gc, 1):.0f} % | {'—' if d is None else f'{d:+.0f} pts'} | "
			          f"{fs[0]['ent_m']:.2f} → {fs[-1]['ent_m']:.2f} |")
	md += ["", "## Por fase", "", "| corrida | etapa | inicio | rol | ciclo | its | a favor / act. | en contra / act. | % a favor | entropía |",
	       "|---|---|---|---|---|---|---|---|---|---|"]
	for f in fases:
		md.append(f"| {f['run']} | {f['etapa']} | {f['t']:%d/%m %H:%M} | {f['role']} | "
		          f"{f['ciclo'] if f['completa'] else '(cortada)'} | {f['its']} | {f['gf_u']:.2f} | {f['gc_u']:.2f} | "
		          f"{f['pct']:.0f} % | {f['ent_m']:.2f} |")
	(OUT / "fases.md").write_text("\n".join(md) + "\n", encoding="utf-8")

	_grafico(fases)
	# Sesión 51: por un pipe en Windows la consola es cp1252 y el "Δ" de la tabla cortaba el script.
	sys.stdout.reconfigure(encoding="utf-8", errors="replace")
	print("\n".join(md[:9 + 2 * len(ETAPAS)]))
	print(f"\nTabla completa en {OUT / 'fases.md'} · gráfico en {OUT / 'fases.png'}")


def _grafico(fases):
	import matplotlib
	matplotlib.use("Agg")
	import matplotlib.pyplot as plt
	# Paleta de referencia (dataviz): categórica slot 1 azul / slot 2 naranja; texto en tinta neutra.
	COL = {"striker": "#2a78d6", "keeper": "#eb6834"}
	INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e6e5df"
	BAND = ["#f4f3ee", "#ffffff"]
	x = list(range(len(fases)))
	fig, axes = plt.subplots(2, 1, figsize=(14, 7.5), sharex=True, gridspec_kw={"hspace": 0.12})
	for ax, key, titulo, ylab in ((axes[0], "pct", "Goles a favor sobre el total de goles, por fase", "% a favor"),
	                              (axes[1], "ent_m", "Entropía media de la política, por fase (más baja = más decidida)", "entropía")):
		# Etapas sombreadas alternadas, con su letra arriba
		for i, e in enumerate(ETAPAS):
			idx = [j for j, f in enumerate(fases) if f["etapa"] == e[0]]
			if not idx:
				continue
			ax.axvspan(idx[0] - 0.5, idx[-1] + 0.5, color=BAND[i % 2], zorder=0)
			if ax is axes[0]:
				nombre = e[0]   # sesión 51: con 7 etapas, solo la letra (la leyenda de abajo las explica)
				ax.text((idx[0] + idx[-1]) / 2, 0.97, nombre, transform=ax.get_xaxis_transform(),
				        ha="center", va="top", color=INK, fontsize=10, fontweight="bold")
		for role in ("striker", "keeper"):
			xs = [j for j, f in enumerate(fases) if f["role"] == role]
			ys = [fases[j][key] for j in xs]
			ax.plot(xs, ys, color=COL[role], lw=2, marker="o", ms=4.5, label=role,
			        markeredgecolor="white", markeredgewidth=1, zorder=3)
		ax.set_title(titulo, loc="left", color=INK, fontsize=11)
		ax.set_ylabel(ylab, color=MUTED)
		ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
		for s in ("top", "right"):
			ax.spines[s].set_visible(False)
		for s in ("left", "bottom"):
			ax.spines[s].set_color(GRID)
		ax.tick_params(colors=MUTED)
	axes[0].set_ylim(0, 100)
	axes[0].legend(loc="center left", frameon=False, labelcolor=INK)
	# Eje x: hora de la primera fase de cada etapa
	ticks = []
	for e in ETAPAS:
		idx = [j for j, f in enumerate(fases) if f["etapa"] == e[0]]
		if idx and (not ticks or idx[0] - ticks[-1][0] >= 10):   # sesión 51: no pisar fechas vecinas
			ticks.append((idx[0], f"{fases[idx[0]]['t']:%d/%m %H:%M}"))
	axes[1].set_xticks([t[0] for t in ticks], [t[1] for t in ticks])
	axes[1].set_xlabel("fases en orden (marca = inicio de cada etapa)", color=MUTED)
	leyenda = "\n".join(f"{e[0]}: {e[1]}" for e in ETAPAS)   # una línea por etapa (no se corta)
	fig.text(0.01, -0.06, leyenda, fontsize=8, color=MUTED, va="top")
	fig.suptitle("Entrenamiento DL de DVF por etapas", x=0.01, ha="left", color=INK, fontsize=13)
	fig.savefig(OUT / "fases.png", dpi=130, bbox_inches="tight")


if __name__ == "__main__":
	main()
