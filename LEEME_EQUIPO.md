# DVF — Robotic Soccer: lo que tenemos hecho (para Diego y Fernando)

> **Desactualizado (19/10).** El estado actual está en **`AGENTS.md`** (raíz) y el detalle del
> Deep Learning en **`docs/CONTEXTO_DL.md`**. Si usan una IA para seguir entrenando, pásenle esos
> dos archivos primero y corran `env\Scripts\python.exe scripts\verificar_entorno.py`. Desde el
> 24/10 se entrena **corrida5**, que arranca de la imitación de la v2.3 con recompensa v4 y formato
> torneo. El modelo de `entrega/red_DL` ya no es el mejor.

Estado al lunes 19/10/2026 a la madrugada. El detalle de cada paso está en `CHANGELOG.md`
(sesiones 1–42, las más nuevas arriba) y en la guía del equipo (Claude Doc "Guía del equipo DVF").
El plan de entrega está en `PLAN_ENTREGA.md`.

## 1. Entregas

| Qué | Archivo | Estado |
|---|---|---|
| **Rule-based** (vence lun 19/10 10:00) | **`entrega/soccer_DVF.py`** | Listo: es nuestra **v2.3**. Hay que subirlo y reemplazar `imr-mrk-V.py` (es nuestra v1.0, más débil: pierde −6,5 por par de partidos contra la v2.3). |
| **Metadata ML** (lun 10:00) | `python scripts/metadata_entrega.py noche1 corrida2 corrida3` → `entrega/metadata_DVF.md` y `.csv` | El script está listo. Se corre cuando termine el entrenamiento (07:00). |
| **Red DL** (formato y fecha a confirmar) | `models/runs/<corrida>/striker.npz` + `keeper.npz` | Elegir con `models/runs/<corrida>/eval/mejor.txt`. |

**Dudas abiertas con los ayudantes**
- ¿Se puede **leer** `self.body.position/velocity/angle` en el rule-based? La v2.3 lo lee (nunca
  escribe). Si no se puede, la versión que usa solo sensores es `imr-mrk-V.py` / v1.0.
- Formato de entrega de la red. Ojo: corregimos en `soccer_team_DVF_DL.py` un bug de la
  observación del curso para el lado violeta (ver más abajo). Si la cátedra corre la red con su
  propia `build_observation`, esa corrección no se aplica.

## 2. Equipos rule-based (raíz del proyecto)

| Archivo | Qué es |
|---|---|
| `soccer_team_DVF.py` | v1.1 (versión base). Rival de referencia. |
| `soccer_team_DVF_v2.py` | **v2.3**, nuestro mejor equipo. Le gana a v1 (+5,6) y a NormalTeam (+9,1). Es el mismo código que `entrega/soccer_DVF.py`. |
| `experimentos/soccer_team_DVF_v24_banda.py` | v2.4 (jugada por la banda), probada y no adoptada. |

No renombrar los de la raíz: el entrenamiento los importa como rivales.

## 3. Deep Learning (PPO)

- Recompensa: `dvf_rewards.py`, actualmente en la **v3**. Respecto de la del curso:
  - corregimos el eje del frente;
  - la v2 agregó castigo por gol recibido y atajadas solo en nuestro tercio;
  - la v3 agregó la defensa del saque.
- Entrenamiento: `scripts/train_dl.py`, con fases alternadas de striker y keeper, bajo
  `scripts/supervisar_entrenamiento.py`, que lo relanza si Windows lo tira.
- Lanzar o cortar: `scripts/lanzar_corrida.ps1 -Run <nombre>` y `scripts/cortar_corrida.ps1 -Run <nombre>`.
- Equipo DL para jugar: `soccer_team_DVF_DL.py`. Elige qué red usar con variables de entorno:
  `DVF_DL_RUN=<corrida>` o `DVF_DL_STRIKER` + `DVF_DL_KEEPER`.

**Corridas** (`models/runs/`):

| Corrida | Qué tiene | Mejor resultado (neto por par de partidos, 8 semillas) |
|---|---|---|
| `noche1` | 12,6 h. Recompensas v1 → v2. El striker terminó sobreajustado a NormalTeam. | — |
| `corrida2` | Recompensa v3 y rivales ponderados (v2.3 ×4, v1 ×2, NT ×2). Desde las 21:11, rama del clon (imitación de v2.3), que no funcionó. | Ciclo 23: NT +5,1 · v1 −10,4 · v2.3 −18,2 |
| **`corrida3`** | Rama PPO, que sigue a corrida2 antes del clon. Corre hasta el lunes 07:00. | 23:35: **NT +3,9 (11-0-5) · v1 −10,5 · v2.3 −13,1** |

`models/candidatos/` tiene los pares striker+keeper que evaluamos: ciclos 12, 19 y 23 de corrida2
y la rama del clon. Los checkpoints intermedios no van en este zip (pesan ~1,3 GB).

**Hallazgos importantes**
1. **Bug de la observación del violeta** (en `game/keras_core.py`, del curso): no invierte ni la
   posición y ni la velocidad y. De violeta la red recibía 3–4 veces más goles. Lo corregimos en
   `soccer_team_DVF_DL.py`.
2. **Exploración (entropía)**: con 0,02 o 0,05 las redes quedaban casi al azar. Con 0,01 aprenden.
3. **Rivales ponderados**: con NT/v1/v2.3 repartidos parejo, el equipo se sobreajustaba a
   NormalTeam. Dándole más peso a v2.3 se enderezó la curva.
4. **Los números del entrenamiento no predicen los partidos**: siempre decidir con el benchmark,
   con 8 semillas por lado.

## 4. Cómo probar

```bash
python -m venv env          # Python 3.10
env\Scripts\activate
pip install -r requirements.txt
python run.py soccer_team_DVF_v2 soccer_team_NormalTeam                   # partido con ventana
python scripts/benchmark.py soccer_team_DVF_v2 --vs soccer_team_DVF --seeds 8   # banco de pruebas
python scripts/evaluar_corrida.py corrida3 --dry-run                      # qué checkpoints evaluaría
python scripts/analizar_fases.py                                          # curva por etapas
```

Guía del benchmark: `docs/BENCHMARK.md`. Sondas de diagnóstico: `scripts/sondas/`.
