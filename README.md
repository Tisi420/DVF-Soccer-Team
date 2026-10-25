# DVF — Robotic Soccer (2 contra 2) · rule-based + Deep Learning (PPO)

Proyecto del equipo **DVF** (Diego, Valentino y Fernando) para el Praktikum *Robotic Motions*
(Reutlingen University, 2026): fútbol 2 contra 2 simulado con pymunk. Cada equipo tiene un
striker y un keeper.

- **Rule-based**: `soccer_team_DVF_v2.py` (v2.3, el que entregamos como `entrega/soccer_DVF.py`).
  Llegó a la semifinal del torneo de la cátedra.
- **Deep Learning (PPO)**: una red por jugador (78 → 256 → 128 → acciones + valor), entrenada con
  fases alternadas striker/keeper, una recompensa propia (`dvf_rewards.py`, v4) y arrancando desde
  la **imitación** del equipo rule-based.

> ⚠️ **Este repositorio no incluye el simulador de la cátedra** (`game/`, `setup_dl_notebook.py`,
> `setup_game_notebook.py`, los equipos de ejemplo `soccer_team_NormalTeam.py`, `Passive`,
> `ManualControl` y `DeepLearning`, los notebooks y sus guías). Es material del curso. Para correr
> el proyecto, copiá esos archivos del material del Praktikum en la raíz.

## Resultados (partidos de 1 minuto con gol de oro, ganados-empatados-perdidos sobre 32)

| equipo | contra NormalTeam (curso) | contra nuestra v1 | contra nuestra v2.3 |
|---|---|---|---|
| rule-based v2.3 | 30-0-2 | 27-0-5 | 13-6-13 |
| DL, primer intento (PPO desde cero) | 15-0-17 | 5-0-27 | 1-0-31 |
| DL, imitación de la v2.3 (sin PPO) | 23-0-9 | 9-0-23 | 4-3-25 |
| **DL, imitación + 1,4 h de PPO** | **30-0-2** | **27-0-5** | 7-3-22 |

## Lo más interesante que aprendimos

- **Bug en la observación del curso**: para el equipo violeta no se invertía la posición y ni la
  velocidad y, así que de ese lado la red recibía 3–4 veces más goles. Lo corregimos en
  `soccer_team_DVF_DL.py`.
- **La red corría de espaldas** el 92 % del tiempo. La física es simétrica (hitbox cuadrada,
  misma aceleración hacia adelante y hacia atrás) y así se ahorraba girar. Lo resolvimos con un
  término de recompensa (`W_FRENTE`) y empezando desde la imitación.
- **Los números del entrenamiento engañan**: los modelos se eligen con partidos
  (`scripts/benchmark.py`), en los dos lados, con ruido en el saque y muchas semillas.
- **La exploración (entropía) define todo**: muy alta y la red queda al azar, muy baja y colapsa.

Todo el proceso está, con números, en [`CHANGELOG.md`](CHANGELOG.md) (más de 60 sesiones).

## Estructura

| ruta | qué es |
|---|---|
| `soccer_team_DVF.py`, `soccer_team_DVF_v2.py` | equipos rule-based v1 y v2.3 |
| `soccer_team_DVF_DL.py` | equipo Deep Learning (carga los `.npz`) |
| `dvf_rewards.py` | recompensa (v1 → v4) |
| `scripts/train_dl.py` (+ `supervisar_entrenamiento.py`, `lanzar_corrida.ps1`) | entrenamiento PPO en paralelo |
| `scripts/benchmark.py`, `scripts/chequeo_completo.py` | evaluación (formato torneo con gol de oro) |
| `scripts/imitar_equipo.py` | imitación del equipo rule-based |
| `scripts/sondas/` | diagnósticos (carrera de espaldas, saques, recompensa) |
| `models/` | redes entrenadas (`runs/<corrida>/`, `imitacion/`, `candidatos/`) |
| `experimentos/` | variantes rule-based probadas y no adoptadas |
| `AGENTS.md`, `docs/CONTEXTO_DL.md` | contexto completo para seguir trabajando (también para asistentes de IA) |

## Cómo correrlo

Requiere Windows y Python 3.10, más los archivos del simulador del curso (ver arriba).

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1     # venv + paquetes + verificación
env\Scripts\python.exe run.py soccer_team_DVF_DL soccer_team_DVF_v2 --duracion 60 --gol-de-oro
env\Scripts\python.exe scripts\benchmark.py soccer_team_DVF_v2 --vs soccer_team_DVF --seeds 8 --duration 60 --gol-de-oro
```

Para entrenar, ver [`EMPEZAR_ACA.md`](EMPEZAR_ACA.md) y [`AGENTS.md`](AGENTS.md).
