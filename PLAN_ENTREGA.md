# Plan de entrega — Equipo DVF (Diego, Valentino, Fernando)

**Fecha límite: lunes 2026-10-19, 10:00** (rule-based, según la plataforma; la metadata, según
entendemos, también) · **Plan armado:** sábado 2026-10-17, actualizado el mismo día a la noche
**PC:** 16 núcleos, sin GPU (TensorFlow 2.21 en CPU). Disponible todo el tiempo para entrenar.

## Qué hay que entregar

| # | Entregable | Formato | Vence | Estado |
|---|---|---|---|---|
| 1 | **Rule-based** | **`entrega/soccer_DVF.py`** (v2.3, apariencia "DVF" coral) | **lun 19/10 10:00** | ✅ Listo para subir (reglas chequeadas, 16/16 partidos idénticos a v2.3). Pendiente: ¿apellidos en la cabecera? |
| 2 | **Metadata ML** (planilla "Metadata Soccer") | Team · horas de entrenamiento · CPU/GPU · épocas · capas · neuronas · modelos entrenados · ideas (sin Elo) | **lun 19/10 10:00** (a confirmar) | Se completa con los datos de las corridas |
| 3 | **Red entrenada** striker + keeper | "Un solo archivo", entrenados por separado/alternadamente | A confirmar | `noche1` entrenando |

> **Cambio 2026-10-17 (noche): la fecha pasa del martes al lunes 10:00.** El entrenamiento
> tiene que cerrarse el lunes temprano para tener las horas y los modelos de la metadata.
> El archivo a subir se arma en `entrega/`. Los nombres actuales no se tocan mientras se
> entrena, porque `scripts/train_dl.py` importa `soccer_team_DVF` y `soccer_team_DVF_v2` como
> rivales.

Regla de trabajo: cada cambio se comenta en el código y se registra en `CHANGELOG.md`. Toda
decisión de "mejor o peor" se toma con `scripts/benchmark.py` (ver `docs/BENCHMARK.md`).

---

> **Actualización 2026-10-17 (noche):** prioridad = llegar a completar la metadata. Formato de
> la red y fechas se ven después. **Elo: no se completa** (ningún equipo lo hace en la planilla
> actual, `../Soccer Metadata.pdf`). Lectura de `body.*` en el rule-based: sin respuesta todavía.

## Paso 0 — Dudas para los asistentes (pendiente, no bloquea)

1. **Formato de la red:** "un solo archivo" ¿es **un `.npz` con los dos modelos** o el `.py`
   del equipo DL más dos `.npz`, como dice `HowTo_DL_Train_Run_And_Submit.MD`? ¿Va con
   `training_curve.png`?
2. **Fechas:** ¿el martes se entregan las tres cosas, o solo el rule-based?
3. **Elo:** ¿lo calculan ustedes (torneo) o lo calculamos nosotros? ¿Contra qué referencia?
4. **Lectura de `self.body.position/velocity` en el rule-based:** el HowTo dice "solo
   sensores", pero v2 la usa (solo lectura, el anti-exploit no la revierte) y el propio
   `game/keras_core.py` del curso también la usa. ¿Está permitido?

Mientras no respondan, seguimos con los supuestos del caso más exigente: las tres cosas el
martes, sin depender de la respuesta 4 para el núcleo del comportamiento.

Borrador listo para pegar en Teams:

> Hallo, wir (Team DVF: Diego, Valentino, Fernando) haben ein paar kurze Fragen zur Abgabe:
> 1. Deep Learning: Soll das trainierte Netzwerk (Striker + Keeper) als **eine einzige Datei**
>    abgegeben werden (z. B. ein `.npz` mit beiden Modellen) oder wie im HowTo als `.py` +
>    `<team>_striker.npz` + `<team>_keeper.npz` + `training_curve.png`?
> 2. Ist am Dienstag alles fällig (Rule-Based, Metadaten, Netzwerk) oder nur Rule-Based?
> 3. Elo-Wert in der Metadaten-Tabelle: Berechnen Sie ihn (Turnier) oder sollen wir ihn selbst
>    berechnen? Falls ja, gegen welche Referenz?
> 4. Rule-Based: Dürfen wir `self.body.position` / `self.body.velocity` **lesen** (nicht
>    schreiben)? `game/keras_core.py` nutzt diese Werte ebenfalls für die Beobachtung.
>
> Vielen Dank!

---

## Bloque A — Rule-based (prioridad 1, congelar el lunes a la noche)

| Paso | Qué | Criterio de "listo" |
|---|---|---|
| A1 ✅ | v2.1 (arquero violeta) + v2.2 (delantero colgado) | Hecho. Con ruido + reinicio por pelota trabada: +2.1 vs v1, +12.2 vs NormalTeam, +2.4 vs v2.1 |
| A2 ✅ | **Jugada de saque** (v2.3) | Hecho. Goles de saque en contra 2.4 → 0.2 por partido. Con ruido: +5.6 vs v1, +3.4 vs v2.2. Sin ruido: 32-0-0 vs v2.1 y NormalTeam. Pendiente: de izquierda vs v1 sin ruido todavía 1–3 (juego abierto) |
| A3 | Robustez contra estilos distintos: v1, NormalTeam, Passive, v2.1 y más adelante el equipo DL | Neto ≥ 0 contra todos, con ruido y sin ruido |
| A4 ✅ | **Chequeo de reglas** → `entrega/soccer_DVF.py` | Hecho (CHANGELOG sesión 13). Única duda: lectura de `body.*` |
| A5 | Partido en ventana de cada lado con el archivo de entrega y **subirlo** | Domingo. Si el entrenamiento está corriendo, ver los partidos con `soccer_team_DVF_v2` (misma lógica) |

---

## Bloque B — Deep Learning (arrancar YA en paralelo; la PC entrena mientras pulimos A)

| Paso | Qué | Detalle |
|---|---|---|
| B1 ✅ | **Prueba rápida** | `scripts/train_dl.py` (sesión 10): ~2 900 pasos/s con 14 workers ≈ 10M pasos/hora |
| B2 ✅ | **Entrenamiento alternado por rol** | Fases striker/keeper, el otro rol congelado (verificado con huellas de pesos en el log) |
| B3 ✅ | **Rivales** | NormalTeam + v1 + v2.3 mezclados entre los workers; ruido en el saque ±5 px |
| B4 ✅ | **Recompensa revisada** (`dvf_rewards.py`) | Hecho antes de entrenar: 3 bugs de la base corregidos (orientación al revés, premio por quedarse quieto, arquero dentro del arco) + refine 2, 6 y 8. Ver CHANGELOG sesión (8). Ajustes futuros: de a uno y con su curva |
| A3+ ✗ | **Esquinas en el rule-based** | Medido (~33 % del tiempo) y diagnosticado: la mayoría son pelotas encajadas que destraba el reinicio del motor. La jugada de banda (v2.4) no lo baja y empata con v2.3 → no adoptada; guardada en `experimentos/`. Se ataca desde la recompensa del DL (refine 6) |
| B5 ⏳ | **Corridas nocturnas** | `noche1` lanzada sáb 2026-10-17 20:21, 11 h (hasta ~07:30). Domingo: evaluarla (B6) y decidir la segunda noche (seguir desde `noche1` con `--init-from`, o ajustar la recompensa) |
| B6 | **Evaluar checkpoints** con `scripts/benchmark.py` | Herramientas listas (sesión 11): `soccer_team_DVF_DL.py` + `DVF_DL_RUN` / `DVF_DL_STRIKER`+`DVF_DL_KEEPER`, y `scripts/plot_training.py`. Elegir el mejor por neto, no por la recompensa del log. Pasos y criterios: abajo |
| B7 | **Empaquetar** según la respuesta del paso 0 | Renombrar `<teamname>_striker/keeper.npz` (o fusionarlos en un archivo) + `.py` DL + `training_curve.png` |

### Domingo a la mañana: evaluar `noche1` y decidir la segunda noche

1. Ver que terminó: última línea de `models/runs/noche1/training.log` y `run.json`
   (fases, horas totales).
2. Curva: `python scripts/plot_training.py noche1`. Mirar si la entropía baja, si los goles a
   favor suben y si bajan los en contra.
3. Evaluar el modelo final (con ruido y sin ruido, ambos lados, 8 semillas) contra
   **NormalTeam, v1 y v2.3**: `DVF_DL_RUN=noche1` + `scripts/benchmark.py soccer_team_DVF_DL --vs ...`.
4. Evaluar 4–5 checkpoints repartidos en la noche (`DVF_DL_STRIKER`/`DVF_DL_KEEPER`) contra
   NormalTeam, para ver si mejora con el tiempo o si se estancó o empeoró.
   > **Atajo (sesión 18):** los pasos 3 y 4 juntos en un comando:
   > `python scripts/evaluar_corrida.py noche1` (5 fines de fase + el final, vs NormalTeam, v1
   > y v2.3, ambos lados, ruido 3 y 0) → tabla en `models/runs/noche1/eval/resumen.md`.
   > Con `--dry-run` muestra qué puntos elegiría. Para mezclar ciclos (sesión 19):
   > `--strikers 26 27 final --keepers 10 11 final` → `eval/resumen_combos.md`.
   > **Ojo (sesión 19):** desde las 06:01 `noche1` entrena con la **recompensa v2** (castigo por
   > gol recibido, keeper atado al arco). Los checkpoints anteriores son v1 y todos perdían
   > contra NormalTeam (−3 a −9). Evaluar primero el `final` y los ciclos posteriores a las 06:01,
   > y compararlos con los v1. Con `python scripts/sondas/sonda_keeper.py <striker.npz>
   > <keeper.npz>` se ve si el keeper vuelve al arco (mediana x, % lejos, x a 2 s del saque).
   > **Corrida 2 (sesión 20, lista sin lanzar):**
   > `powershell -ExecutionPolicy Bypass -File scripts\lanzar_corrida2.ps1` → recompensa v3
   > (defensa del saque), striker y keeper contra los tres rivales, desde el final de noche1,
   > hasta el lunes 07:00. Evaluar con `evaluar_corrida.py corrida2` y
   > `scripts/sondas/sonda_saque.py` (quién toca primero, dónde está el keeper en el saque).
   > Metadata con las dos corridas: `python scripts/metadata_entrega.py noche1 corrida2`. Metadata: `python scripts/metadata_entrega.py
   > noche1 [noche2]` → `entrega/metadata_DVF.md` y `.csv`.

**Criterios para la segunda noche**

| Lo que muestra noche1 | Segunda noche |
|---|---|
| Mejora y ya le gana a NormalTeam | Seguir desde el mejor checkpoint (`--init-from`), mismos rivales; sumar el propio modelo como rival si se puede |
| Mejora pero todavía pierde con NormalTeam | Seguir desde el mejor checkpoint, mismos ajustes, otra noche completa |
| Plana: entropía casi no baja, goles iguales | Ajustar antes de seguir: `ENTROPY_COEF` 0.05 → 0.01 y/o arrancar solo contra NormalTeam (currículum) |
| Empeora en la segunda mitad | Seguir desde el mejor checkpoint y bajar el learning rate (3e-4 → 1e-4) |

**Regla de corte:** si el lunes a la noche la red no le gana a NormalTeam, se entrega igual el
mejor checkpoint. Lo pedido es entregar la red entrenada; la pieza competitiva es el rule-based.

---

## Bloque C — Metadata (ir anotando desde ya, completar el lunes)

Referencia: `../Soccer Metadata.pdf` (planilla de los otros equipos al 2026-10-17).

| Columna | De dónde sale | Lo que pusieron los demás |
|---|---|---|
| Team | Fach / Gruppe / "DVF" | p. ej. "KiB / kib-D / JJN" |
| Elo | **No se completa** | Nadie lo completa |
| Horas de entrenamiento | Sumar las corridas de `training.log` (anotar inicio y fin de cada una) | 10–40 h (máx. 72 h) |
| CPU/GPU | CPU de 16 núcleos (modelo exacto: `wmic cpu get name`), sin GPU, N workers | Formato: "AMD Ryzen 7 …, 16 Kerne, 14 Worker" |
| Épocas | `EPOCHS = 4` | Casi todos ponen **4** |
| Capas | **3** (convención de la planilla: 256 → 128 → salidas) | Casi todos ponen **3** |
| Neuronas totales | **394** = 256 + 128 + 10 | Casi todos ponen **394** |
| Modelos entrenados | Contar corridas y checkpoints evaluados | 1 a 50+ |
| Ideas creativas | Ver abajo | Recompensas *refine* del notebook, rivales mezclados, self-play, liga de snapshots |

**Ideas propias para la columna "kreative Ideen"** (lo que nos diferencia):
- Banco de pruebas propio: ambos lados, semillas fijas, ruido en el saque y emulación del
  reinicio por pelota trabada. Descubrimos que el saque es caótico y que sin ruido las
  comparaciones engañan.
- Rivales: nuestros rule-based v1, v2.1, v2.2 y v2.3 + NormalTeam (lo recomienda el enunciado).
- Entrenamiento alternado striker/keeper (lo pide la cátedra).
- Recompensas inspiradas en bugs reales del rule-based (delantero colgado → anti-freeze/chase;
  saque determinista → recompensa de saque).

---

## Calendario

Actualizado 2026-10-17 (noche) por la fecha del **lunes 10:00**. Lo hecho el sábado está en el
CHANGELOG (sesiones 1–11).

| Cuándo | Qué | La PC entrena |
|---|---|---|
| **Sáb 17 noche** | — | `noche1` (20:24 → **10:30 del domingo**, extendida; supervisor + encadenador) |
| **Dom 18 mañana** | Partido en ventana de cada lado con el rule-based · subirlo (ya está en `entrega/`) | `noche1` sigue hasta las 10:30 |
| **Dom 18 ~10:30** | Evaluar `noche1` y decidir la corrida 2 (criterios arriba) | Corrida 2 desde el mejor checkpoint |
| **Dom 18 tarde** | Evaluar checkpoints de la corrida 2 · borrador de la metadata con las horas hasta el momento · **subir el rule-based** (no hace falta esperar al lunes) | Corrida 2 sigue toda la noche, hasta ~07:00 del lunes |
| **Lun 19 07:00–09:30** | Cortar el entrenamiento · evaluar y elegir el modelo final · curva · completar la metadata con las horas y los modelos finales | — |
| **Lun 19 10:00** | **Vencen el rule-based y la metadata** | — |
| Después | Red entrenada: formato y fecha a confirmar con los asistentes | — |
