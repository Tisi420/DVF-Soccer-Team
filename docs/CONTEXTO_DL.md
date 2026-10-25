# Contexto detallado del Deep Learning (DVF) — para seguir entrenando sin errores

Complemento de `AGENTS.md`. Actualizado: 2026-10-25 (sesión 61). La historia completa, con todos
los números, está en `CHANGELOG.md` (sesiones 8–61).

---

## 1. Cómo funciona el entrenamiento

**Red** (`game/keras_core.py`, del curso): observación de 78 valores → capas densas de 256 y 128
→ 3 cabezas de 3 acciones (avance/retroceso, lateral, giro) + valor. Un modelo para el striker y
otro para el keeper, guardados en `.npz` (pesos + estado de Adam `opt_*`; los paquetes de entrega
llevan solo los pesos).

- Observación (`build_observation`):
  - 10 sectores de sensor × 7 entidades (distancias);
  - posición, velocidad y orientación propias;
  - distancia y dirección de la pelota.
  Es "invariante al equipo", **salvo el bug de la y** (ver §6).
- Acción: `[avance, lateral, giro]`, cada uno con 0 = nada, 1 = adelante/derecha/giro izquierdo y
  2 = atrás/izquierda/giro derecho (`game/player.py`). Se repite 4 frames (`action_repeat`).
- Física: avanzar, retroceder y moverse de costado aceleran igual; el giro es de 3 rad/s (180° en
  ~1 s). La hitbox es un cuadrado de 70 px, la misma para todos.

**PPO** (`setup_dl_notebook.py`, del curso, sin modificar) orquestado por `scripts/train_dl.py`:

- **Fases alternadas**: durante una fase de striker solo aprende el striker (el keeper juega con su
  red congelada), y al revés. Cada fase dura `--phase-steps` (1,5 M pasos de simulación ≈ 10–15
  min con 8–10 workers).
- **Workers en paralelo** (`--workers`): cada uno juega contra un rival. La lista `--opponents` se
  reparte por turno (worker i → lista[i % largo]), así que **los repetidos pesan más**.
- **Siempre de azul**: el entorno de entrenamiento pone a nuestra red del lado izquierdo.
- Hiperparámetros (`HPARAMS` en `train_dl.py`): `--lr` (corrida5: 1e-4), gamma 0,99, lam 0,95,
  clip 0,2, 4 épocas y batch de 64. Entropía por rol: `--striker-entropy` y `--keeper-entropy`.
- Guardado: cada 20 actualizaciones se escriben `striker.npz`/`keeper.npz` de forma atómica y una
  copia en `checkpoints/`.
- Al terminar cada fase se anota en `run.json`: rol, hashes de los pesos, rivales, entropía,
  versión de recompensa y estadísticas (`gf_per_upd`, `gc_per_upd`, `ent_mean`).
- **Retoma sola**: relanzar con el mismo `--run` sigue desde el último guardado y desde la
  alternancia anotada en `run.json`. Una fase cortada a la mitad se repite.
- Regla de estancamiento: si 3 fases del mismo rol y configuración no mejoran, escribe
  `!!! ESTANCAMIENTO` en el log y lo anota en `run.json["plateaus"]`.

**Parches del entorno** (a nivel de módulo en `train_dl.py`, así también valen en los workers):

| parche | qué hace | variable |
|---|---|---|
| ruido en el saque | la pelota sale a ±5 px del centro | `DVF_TRAIN_JITTER` |
| pelota trabada | reinicio si la pelota queda 3 s en una esquina **o casi quieta** | — |
| formato torneo | saque nuevo cada **60 s** de juego sin gol (corta el episodio) | `DVF_TRAIN_PARTIDO_S` (0 = apagado) |

**Robustez**:

- `supervisar_entrenamiento.py` relanza `train_dl` si Windows lo tira y mata solo los workers de
  su corrida.
- Si un worker muere, `train_dl` lo reemplaza en caliente (`WORKER_TIMEOUT` 120 s).
- `lanzar_corrida.ps1 -Desacoplado` crea el supervisor por WMI, fuera del árbol de procesos de la
  app, en prioridad baja. No lanza si el reloj de Windows está desfasado.

## 2. Recompensa (`dvf_rewards.py`, versión actual v4)

| versión | qué agregó | por qué |
|---|---|---|
| v1 | copia del notebook + corrección del eje del frente (`(sin a, −cos a)`) + términos de orientación escalados por la velocidad + punto ideal del keeper fuera del arco + castigo por esquinas | la del curso premiaba ponerse de costado y quedarse quieto |
| v2 | castigo por gol recibido (keeper −5, striker −1); atajadas solo en nuestro tercio; el keeper vuelve al arco | el keeper aprendió a jugar de mediocampista |
| v3 | carrera al saque del striker; el keeper vuelve al arco en el saque (castigo ×3) | perdíamos casi todos los saques |
| **v4** | **`W_FRENTE`**: premio por moverse de frente y castigo por moverse de espaldas; castigo por tiempo del striker ×2; `W_ADV_DELTA` 0,5 → 0,8 | el modelo de corrida3 corría de espaldas el 92 % del tiempo; formato torneo de 1 min |

- Cada vez que se cambia algo, **subir `REWARD_VERSION`**: queda anotada en cada fase y la regla de
  estancamiento solo compara fases de la misma versión.
- Escala de referencia: un gol a favor vale +20 para el striker; los términos densos valen milésimas
  por paso. Antes de entrenar, probar los cambios con casos sintéticos (ver el CHANGELOG, sesiones
  19–20 y 59).

## 3. Imitación (punto de partida de corrida5)

`scripts/imitar_equipo.py`:

1. Graba al equipo v2.3 completo jugando de azul en el entorno de entrenamiento: 43.200 decisiones
   por rol en ~1 min.
2. Entrena una red nueva por rol: entropía cruzada en las acciones + valor con el retorno de la
   recompensa v4.
3. Precisión de validación: striker 94 / 89 / 99,8 %, keeper 84 / 99 / 100 %.
4. Salida en `models/imitacion/equipo_v23/` (solo pesos; `train_dl` arranca un Adam nuevo).

Hay que rehacerla si cambia el maestro (una v2.x mejor) o la recompensa (para la cabeza de valor).

## 4. Evaluación (la única vara que vale)

```powershell
# Formato torneo: 1 min con gol de oro, ambos lados, 16 semillas → 32 partidos por rival
$env:DVF_DL_STRIKER="...\striker.npz"; $env:DVF_DL_KEEPER="...\keeper.npz"
env\Scripts\python.exe scripts\benchmark.py soccer_team_DVF_DL --vs soccer_team_NormalTeam soccer_team_DVF soccer_team_DVF_v2 --seeds 16 --duration 60 --gol-de-oro --workers 10
```

- Métrica principal: **G-E-P** (ganados-empatados-perdidos). La secundaria es el neto por par de
  partidos (la columna "neto/2 part.").
- Criterio para elegir modelo: rendir bien contra **v1 y v2.3**. NormalTeam es fácil y premia
  trucos que solo sirven contra él.
- `scripts/chequeo_completo.py --run <corrida>` hace todo junto y deja un informe en
  `models/runs/<run>/chequeos/<fecha>.md`: 1 min, 3 min, % de espaldas y saques.
- **En cada chequeo, ver también partidos en ventana**: `run.py ... --duracion 60 --gol-de-oro`,
  uno de cada lado. El equipo quiere juzgar la calidad del juego, no solo los números.

**Referencias** (1 min + gol de oro, G-E-P en 32 partidos por rival):

| equipo | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| rule-based v2.3 | 30-0-2 | 27-0-5 | 13-6-13 |
| DL viejo (`entrega/red_DL`, corrida3) | 15-0-17 | 5-0-27 | 1-0-31 |
| equipo clonado (inicio de corrida5) | 23-0-9 | 9-0-23 | 4-3-25 |
| **corrida5, 24/10 14:01 (mejor hasta ahora)** | **30-0-2** | **27-0-5** | **7-3-22** |

## 5. Cómo es una sesión de entrenamiento (paso a paso)

1. `env\Scripts\python.exe scripts\verificar_entorno.py`: tiene que dar todo OK.
2. Sincronizar el reloj de Windows si hubo un apagón.
3. Lanzar con `lanzar_corrida.ps1 -Desacoplado` (comando en `AGENTS.md` §7). 6 workers si se usa
   la PC (16 núcleos), hasta 8 si nadie la usa.
4. Opcional: monitor horario desacoplado (`scripts/monitorear.py --run X --esperar-pid
   <supervisor> --cada-min 60 --seeds 16 --workers 2 --duracion 60 --gol-de-oro`) y el vigilante de
   cortes (`scripts/protocolo_corte.py --vigilar`).
5. Cada hora: `chequeo_completo.py`, partidos en ventana y anotar en el CHANGELOG.
6. Al terminar: `cortar_corrida.ps1 -Run X`, que corta justo después de un guardado.
7. Elegir el mejor par por benchmark (16 semillas o más, formato torneo) y guardarlo como candidato.

## 6. Problemas conocidos y cómo se resolvieron

| síntoma | causa | solución |
|---|---|---|
| de violeta recibe 3–4 veces más goles | `build_observation` no invierte y ni vy para el violeta | `_obs()` en `soccer_team_DVF_DL.py` (activo por defecto) |
| el striker corre de espaldas | física simétrica + nada lo castigaba | recompensa v4 `W_FRENTE`; medir con `sonda_espaldas.py` |
| la red queda al azar | entropía alta (0,02–0,05) | 0,01–0,015; vigilar `ent_mean` |
| la red colapsa y empeora | entropía 0,01 + lr 3e-4 desde imitación | lr 1e-4 y 0,015 |
| sobreajuste a NormalTeam | rivales parejos o solo NT | más peso a v2.3 en `--opponents` |
| `train_dl` muere sin traza | crash nativo de Windows (0xc0000005) | el supervisor lo relanza |
| mueren todos los procesos juntos | se cerró la app que los lanzó | `-Desacoplado` |
| horas raras en `run.json` | reloj desfasado después de un apagón | sincronizar el reloj; el lanzador lo chequea |
| PC que se apaga | temperatura con 14+ procesos | ≤10 workers y prioridad baja |
| corte de internet | — | `protocolo_corte.py` (ver `PROTOCOLO_CORTE.md`) |
| el lanzador `.ps1` "no termina" | el supervisor hereda la salida | lanzarlo en segundo plano o con `-Desacoplado` |
| grep no encuentra texto en `training.log` | el log está en cp1252 | `grep -a` |

## 7. Entrenar en otra PC

1. Copiar el proyecto (el zip de `scripts/empaquetar.py` no incluye `env/` ni los checkpoints).
2. Crear el venv: `python -m venv env` y `env\Scripts\pip install -r requirements.txt`, con Python
   3.10.
3. `env\Scripts\python.exe scripts\verificar_entorno.py`.
4. Usar una corrida con nombre propio. Para seguir desde corrida5, armar una carpeta con su
   `striker.npz` y `keeper.npz` y pasarla en `-InitFrom` (con `--init-from`, si los `.npz` traen
   estado de Adam, se retoma con optimizador).
5. Ajustar `-Workers` a los núcleos de esa PC: la mitad menos 2 si la estás usando (lo sugiere
   `verificar_entorno.py`), en prioridad baja.
6. Devolver los resultados: `models/runs/<corrida>/` sin `checkpoints/` + los `chequeos/`, y la
   sesión anotada en `CHANGELOG.md`.
