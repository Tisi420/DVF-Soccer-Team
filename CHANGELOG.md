# Changelog — Equipo DVF (Diego, Valentino, Fernando)

Registro de cambios por sesión de trabajo. Cada entrada indica fecha, archivos tocados,
qué se cambió y por qué. Lo más reciente va arriba.

---

## Sesión 2026-10-25 (63) — corrida5 detenida y paquete para que Diego y Fernando sigan entrenando

- **corrida5 detenida** 2 s después del guardado de las 13:15:56: **2,46 h, 14 fases**. Llegó a
  correr ~1 min con el keeper en 0,01. Antes del corte se frenaron el monitor, el chequeo
  programado y el vigilante de corte. Foto final en `models/runs/_estado/ESTADO.md`.
- `AGENTS.md` §5 actualizado: estado al 25/10 13:16, tabla de pares y pendientes.
- **`EMPEZAR_ACA.md`** (nuevo, para personas): instalar, usar una IA, entrenar con nombre propio
  desde corrida5, medir cada hora y devolver resultados.
- **`scripts/instalar.ps1`** (nuevo): busca Python 3.10, crea `env\`, instala `requirements.txt` y
  corre `verificar_entorno.py`.
- `scripts/empaquetar.py`:
  - excluye `.git` y `_cuarentena`;
  - agrega a `models/candidatos/` el mejor par de corrida5 (`corrida5_20261024_1401_MEJOR_*`) y
    el de las 13:02 del 25/10.
- **Zip para el equipo**: `compartir/DVF_robotic_soccer_2026-10-25_1317.zip` (467 archivos,
  40 MB; sin `env\` ni checkpoints). Probado descomprimiéndolo en otra carpeta:
  `verificar_entorno.py` sobre esa copia dio 19 OK, 0 fallas (incluye partido y entrenamiento
  mínimo). El único aviso es esperable: la prueba usó el venv de esta PC.
- **Preparación para GitHub** (todavía sin subir: falta la URL del repo vacío):
  - repositorio **público** por decisión del equipo, **sin el material de la cátedra**: `game/`,
    `setup_*_notebook.py`, equipos de ejemplo, notebooks, `HowTo_*.MD` y documentos del curso en
    `docs/`. Todo eso queda en `.gitignore`;
  - el README del curso pasó a `README_curso.md` (no se sube) y hay un `README.md` propio (qué
    es, resultados, aprendizajes, estructura, cómo correrlo con el simulador del curso);
  - también se excluyen el venv, los checkpoints, los zips, las salidas y estados locales y
    `.vscode/`;
  - `git init -b main` local, autor de commits `Tisi420`. Lo que se subiría: 170 archivos, ~31 MB,
    ninguno de más de 5 MB. Sin emails ni rutas personales (verificado con grep).

## Sesión 2026-10-25 (62) — Chequeo de corrida5 a las 13:10 (2,46 h, 14 fases)

- Todo vivo (supervisor, monitor, vigilante). CPU ~49 % con 6 workers + la evaluación del monitor.
- Curva (ciclos 5–7): 62–67 % de goles a favor por fase (con 8 workers rondaba 63–76 %). Entropía
  del striker estable (~1,3). **La del keeper sube: 1,89 → 2,08 → 2,28**. Puede que 0,015 le dé
  demasiada exploración; a vigilar.
- Monitor 13:02 (par `monitoreo/1302_*`, 1 min + gol de oro, 32 partidos por rival):
  **NormalTeam 29-0-3 (+3,9) · v1 21-2-9 (+1,1) · v2.3 6-0-26 (−2,4)**. Contra v1 y v2.3 algo peor
  que el mejor par de ayer (14:01: 27-0-5 y 7-3-22), pero todavía por encima del clon de partida.
- De espaldas: **8 %** del tiempo en movimiento (ayer 15–16 %).
- **Saques: mejoró la carrera del striker.** Contra v2.3 toca primero en 6 de 10 saques (ayer 0 de
  5; a 146 px de la pelota al segundo). Contra v1, 2 de 12, con 2 goles de saque a favor y 2 en
  contra en 300 s. El keeper vuelve algo menos (x≈338 a los 2 s; ayer 281).
- Partidos en ventana (1 min + gol de oro) del par de las 13:02 contra v2.3, uno de cada lado.
- **Keeper con exploración 0,01**: el equipo vio en la ventana lo mismo que la sonda (el keeper
  vuelve peor al arco en el saque) y la entropía del keeper venía subiendo. Corte 1 s después del
  guardado de las 13:14:39 (2,46 h, 14 fases) y **relanzada a las 13:14:52** con keeper 0,01,
  striker 0,015 y 6 workers (supervisor 19728). Monitor rearmado (PID 20796; próximo chequeo
  ~14:15).

## Sesión 2026-10-25 (61) — corrida5 sigue; partidos en ventana de 1 y 3 min; contexto para la IA del equipo

### corrida5 retomada
- 11:54 con 10 workers (pedido: 10 núcleos, prioridad baja). El equipo avisó que la PC iba "al
  palo": a esa carga se le sumó un rato la verificación del entorno (abajo).
- Corte 1 s después del guardado de las 12:01:26 y **relanzada a las 12:01:37 con 6 workers**
  (supervisor 18136; v2.3 ×3, v1 ×2, NT ×1). CPU ~40 %. Retoma pesos y optimizador.
- Hasta 2026-10-26T08:00. Monitor horario desacoplado (PID 13096, 16 semillas en formato torneo,
  2 procesos). Vigilante de corte relanzado (PID 19204).
- Límite nuevo con la PC en uso: 6 workers (antes 10). Actualizado en `AGENTS.md`,
  `docs/CONTEXTO_DL.md`, `verificar_entorno.py` (sugiere núcleos/2 − 2) y la memoria.

### `run.py`: formato torneo en ventana
- Los partidos en ventana duraban 5 min (`MATCH_DURATION_S = 300` fijo). Ahora
  `python run.py <izq> <der> --duracion 60 --gol-de-oro [--oro-max 120]`; para la final,
  `--duracion 180`.
- Gol de oro: con empate y el tiempo cumplido, se corre el final un segundo por frame hasta el
  primer gol, y en ese frame termina. En la ventana el reloj solo corre con el juego activo.
- Error de un frame corregido: el motor suma el frame antes de mirar el reloj.
- Probado sin ventana, con una copia temporal:
  - 0-0 → termina en el tope (7 s);
  - v2.3 contra v1, 0-0 a los 10 s → termina con el gol, 1-0 a los 44 s;
  - sin `--gol-de-oro` → termina a tiempo.

### Contexto para la IA de Diego y Fernando
- **`AGENTS.md`** (raíz, lo leen Codex, Cursor, Copilot y otros): proyecto, reglas de trabajo,
  entorno de Windows, mapa de archivos, estado del DL, lecciones aprendidas, comandos y cómo
  entrenar en otra PC.
- **`CLAUDE.md`**: importa `AGENTS.md` (`@AGENTS.md`) más notas para Claude Code.
- **`docs/CONTEXTO_DL.md`**: cómo funciona el entrenamiento, historia de la recompensa (v1–v4),
  imitación, evaluación con referencias, paso a paso de una sesión, tabla de problemas conocidos y
  sus soluciones, y cómo entrenar en otra PC.
- **`scripts/verificar_entorno.py`**: Python/venv, paquetes y versiones, archivos, imports, un
  partido de 20 s y un entrenamiento mínimo que después se borra. Sale con código 1 si algo falla.
  En esta PC: 20 OK, 1 aviso (ruta con espacios), 0 fallas, ~1 min.
- `LEEME_EQUIPO.md`: aviso de que está desactualizado, con la referencia a los archivos nuevos.

## Sesión 2026-10-24 (60) — Chequeo exhaustivo de corrida5 (14:00) y cierre para apagar la PC

- Durante la corrida hubo un **corte de internet de 9 min** (13:08–13:17). El protocolo lo
  detectó, aseguró todo (nada corrupto) y el entrenamiento siguió sin interrupciones.
- **`scripts/chequeo_completo.py`** (nuevo): un comando, un informe en
  `models/runs/<run>/chequeos/<fecha>.md`. Hace:
  - copia fija del par;
  - curva de todas las fases;
  - formato torneo de 1 min y de 3 min (final), los dos con gol de oro;
  - % de carrera de espaldas;
  - sonda de saques;
  - referencias del punto de partida.
  Probado en chico. El chequeo real tardó 1,5 min con 12 procesos.
- **corrida5 cortada** 2 s después del guardado de las 14:00:53 (1,43 h, 9 fases; la fase del
  keeper del ciclo 5 quedó a 3 iteraciones de terminar). El monitor (13:25) y el vigilante de
  corte se frenaron a mano. Foto final en `models/runs/_estado/ESTADO.md`.

### Resultado (par `models/runs/corrida5/chequeos/20261024_1401_*.npz`)

Curva: % de goles a favor por fase 51 → 65 → 65 → 64 → 73 → 76 → 71 → 69 %. La entropía subió de
~0,7 a ~1,3–1,6 sin colapsar.

| 1 min + gol de oro (32 partidos) | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| **corrida5 14:01** | **30-0-2 (+4,2)** | **27-0-5 (+2,2)** | 7-3-22 (−1,6) |
| corrida5 13:25 (monitor) | 31-0-1 (+5,3) | 30-1-1 (+2,5) | 10-2-20 (−0,8) |
| equipo clonado (inicio) | 23-0-9 (+2,1) | 9-0-23 (−1,1) | 4-3-25 (−2,4) |
| DL elegido (`entrega/red_DL`) | 15-0-17 (−0,1) | 5-0-27 (−2,1) | 1-0-31 (−2,5) |
| rule-based v2.3 | 30-0-2 (+2,3) | 27-0-5 (+1,6) | 13-6-13 (0,0) |

| 3 min + gol de oro (16 partidos) | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| corrida5 14:01 | 16-0-0 (+12,1) | 13-0-3 (+4,0) | 2-1-13 (−3,9) |

- **En 1,4 h de PPO el DL alcanzó al rule-based v2.3 contra NormalTeam y v1**: mismo G-E-P y
  mejor diferencia de gol. Contra el DL anterior la mejora es enorme (v1: 5-0-27 → 27-0-5).
  Contra v2.3 todavía pierde la mayoría (7-3-22).
- **De espaldas: 16 %** del tiempo en movimiento, pero solo **2 % yendo hacia la pelota**: el hábito
  viejo, acercarse de espaldas, no volvió. La v2.3 retrocede un 28 % para destrabarse. El clon
  arrancaba en 5 %, así que hay que vigilarlo en las próximas sesiones.
- **Saques**: el keeper vuelve mejor al arco (x≈281 a los 2 s; el clon, ~310). El striker perdió la
  carrera del saque: el clon ganaba 7 de 7 primeros toques contra v2.3 y ahora 0 de 5, a 153 px de
  la pelota al segundo (el clon, a 102). Contra v1 recibe 3 goles de saque en 300 s.
- Para seguir: relanzar con
  `scripts\lanzar_corrida.ps1 -Run corrida5 -InitFrom models\imitacion\equipo_v23 -Workers 8
  -StrikerEntropy 0.015 -KeeperEntropy 0.015 -Lr 1e-4 -Hasta <fecha> -Desacoplado`, que continúa
  desde el último guardado. También relanzar el monitor y el vigilante de corte. Prestar
  atención a la carrera del saque del striker y al % de espaldas.

## Sesión 2026-10-24 (59) — corrida5: desde imitación del equipo v2.3, formato torneo, recompensa v4

Pedidos del equipo:
- empezar de nuevo desde imitación, porque el clon jugó mucho mejor en ventana;
- adaptar todo al formato del torneo: partidos de 1 min con **gol de oro** si hay empate, y final
  de 3 min;
- recompensas para que hagan todo más rápido.

La v2.5 no se usa: ninguna de sus ideas le ganó a la v2.3 fuera del ruido, así que la v2.3 sigue
siendo el maestro.

### Herramientas
- **`benchmark.py --gol-de-oro [--oro-max 120]`**: si al cumplirse `--duration` el marcador está
  empatado, se sigue hasta el próximo gol (tope 120 s). Usa el reloj del motor sin ventana, que
  cuenta también las pausas de celebración. Nuevo campo `gol_de_oro` en el JSONL y una línea de
  resumen. Probado: 60 s, sin empates.
- **`train_dl.py`**:
  - `--lr` (tasa de aprendizaje de PPO; queda en `config.hparams`);
  - **saque forzado cada 60 s de juego sin gol** (`DVF_TRAIN_PARTIDO_S`, default 60, 0 = apagado).
    Parchea `S.stuck_ball_step` a nivel de módulo, así vale en los workers, y corta el episodio.
    Probado: dispara en los pasos 900 y 1800.
- **`lanzar_corrida.ps1 -Lr`**.
- **`monitorear.py`**:
  - evalúa el **par fijo copiado** en cada chequeo, con `DVF_DL_STRIKER`/`KEEPER` (antes, con
    `DVF_DL_RUN`, cada partido cargaba los `.npz` de ese momento y mezclaba guardados);
  - `--duracion` y `--gol-de-oro`;
  - anota el **% del tiempo que el striker corre de espaldas**.
- `sonda_espaldas.medir(..., seg=)` se puede importar.

### Recompensa v4 (`dvf_rewards.py`)
- `W_FRENTE = 0,003` × (velocidad · frente)/400 para el striker: + de frente, − de espaldas.
- Presión de tiempo: castigo por paso del striker ×2 (`W_TIEMPO_STRIKER`) y `W_ADV_DELTA`
  0,5 → 0,8.
- Casos sintéticos (yendo a la pelota a 400 px/s): de frente +2,5 por minuto, de espaldas −3,8,
  de costado −1,1, quieto −1,5.

### Imitación del equipo (`scripts/imitar_equipo.py`, nuevo)
- Graba la v2.3 completa (striker + keeper) de azul contra NormalTeam, v1 y v2.3 (4 semillas × 240
  s, ruido en el saque, saque cada 60 s): 43.200 decisiones por rol en 46 s.
- Entrena una red nueva por rol: imitación de las acciones + **cabeza de valor** con el retorno
  descontado de la recompensa v4.
- Precisión de validación (avance / lateral / giro): striker 94 / 89 / 99,8 %, keeper 84 / 99 /
  100 %.
- Guardado en `models/imitacion/equipo_v23/`, solo pesos.

### Punto de partida en formato torneo (1 min + gol de oro, 16 semillas por lado; G-E-P en 32)

| equipo | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| **equipo clonado (inicio de corrida5)** | **23-0-9** | 9-0-23 | 4-3-25 |
| DL elegido (`entrega/red_DL`) | 15-0-17 | 5-0-27 | 1-0-31 |
| rule-based v2.3 | 30-0-2 | 27-0-5 | 13-6-13 |

El clon corre de espaldas el 5 % del tiempo (de frente, 87 %).

### Lanzamiento
- Prueba chica OK: retoma el clon con Adam nuevo, v4 y lr 1e-4. La entropía arranca baja
  (~0,35–0,41) porque el experto es casi determinista.
- **corrida5 lanzada a las 12:24:57, desacoplada** (supervisor 6480): 8 workers (v2.3 ×4, v1 ×2,
  NT ×2), lr 1e-4, entropía 0,015 / 0,015, fases de 1,5 M pasos, hasta el 25/10 09:00.
- **Monitor desacoplado** (PID 17588): cada 60 min, 16 semillas en formato torneo, 3 procesos, %
  de espaldas → `models/runs/corrida5/monitoreo.md`.
- El vigilante de corte de internet (PID 12112) sigue activo.

## Sesión 2026-10-24 (58) — Protocolo de corte de internet

Pedido del equipo: si se corta internet, que quede todo guardado, se limpie lo corrupto y el
proyecto quede esperando la reconexión.

- **`scripts/protocolo_corte.py`** (nuevo):
  - `--vigilar` prueba la conexión cada 60 s (TCP a api.anthropic.com, 1.1.1.1 y 8.8.8.8) y
    confirma el corte con una segunda prueba a los 15 s. Al cortarse y al volver ejecuta
    "asegurar".
  - `--ahora` ejecuta "asegurar" una vez.
  - "asegurar": foto del estado (`models/runs/_estado/ESTADO.md`), respaldo liviano de `run.json`,
    `until.txt`, `supervisor.log`, CHANGELOG y PLAN, y limpieza: borra `*.tmp` de más de 5 min y
    **mueve a cuarentena** (`models/_cuarentena/<fecha>/`) los `.npz` y `.jsonl` que no abren, sin
    borrarlos. No frena ni toca ningún proceso. El entrenamiento es local: un corte no lo para.
- Probado:
  - manual sobre el proyecto real: 1,5 s, nada corrupto, nada movido;
  - con una corrida falsa (`.npz` roto, temporal viejo, `.jsonl` cortado): borró el temporal, movió
    los otros dos a cuarentena y dejó el `.npz` y el `run.json` válidos. La prueba se borró después.
- **Vigilante corriendo** (PID 12112, desacoplado por WMI, BelowNormal): sobrevive al cierre de la
  app, pero no a un reinicio de la PC.
- **`PROTOCOLO_CORTE.md`** (raíz): qué hace y cómo retomar. Para retomar, leer
  `models/runs/_estado/ESTADO.md`.

## Sesión 2026-10-24 (57) — ¿El DL actual es viable? El striker que corre de espaldas

Contexto: la entrega de la red es opcional y vence a fin de semestre, así que hay meses para
entrenar. El equipo ve que el striker DL avanza de espaldas demasiado.

- **`scripts/sondas/sonda_espaldas.py`** (nuevo): juega como azul contra NormalTeam y v2.3 (2
  semillas × 120 s) y clasifica cada frame en movimiento (> 60 px/s) según el ángulo entre la
  velocidad y el frente: adelante (cos > 0,5), de costado o de espaldas (cos < −0,5). Separa
  también los frames "yendo hacia la pelota".

| striker | adelante | de costado | **de espaldas** | de espaldas yendo a la pelota |
|---|---|---|---|---|
| **DL elegido (corrida3 23:36, `entrega/red_DL`)** | 0 % | 8 % | **92 %** | **88 %** |
| DL noche1 05:59 (recompensa v1) | 10 % | 64 % | 26 % | 20 % |
| DL clon de v2.3 (imitación) | **86 %** | 12 % | 2 % | 0 % |
| rule-based v2.3 | 61 % | 11 % | 28 % | 0 % (retrocede solo para destrabarse) |

  (Esta sonda no emula el reinicio por pelota trabada, así que el % "quieto" sale inflado. No
  afecta la clasificación de los frames en movimiento.)
- **No es una etapa del aprendizaje, es un hábito que creció**: 26 % en noche1 y 92 % en el modelo
  elegido. Las causas:
  - **Física**: adelante, atrás y de costado aceleran igual (`PLAYER_ACCELERATION`), y la hitbox
    es un cuadrado simétrico que empuja la pelota igual con la espalda. Girar 180° tarda ~1 s
    (3 rad/s), así que retroceder hacia la pelota le ahorra el giro.
  - **Recompensa**: ningún término cobra moverse de espaldas. Los de orientación (`W_FACE_BALL`
    0,001, `W_SHOOT_ALIGN` 0,002) son diminutos, y la carrera al saque y el acercamiento no miran
    hacia dónde está el frente.
  - Lo único que pierde es percepción: los sectores de atrás miden 60° y los de adelante 20–30°.
- **Viabilidad del modelo elegido para seguir entrenando: baja.**
  - Toda su forma de jugar está armada de espaldas: corregirlo obliga a desaprender casi todo.
  - Con este método (PPO alternado) más horas lo empeoraron (corrida4: −11,3 → −18,4).
  - Juega bien solo sorteando acciones: determinista, contra v2.3 da −115.
- **El clon de la v2.3 ya juega de frente (86 %)** y con 1 h de PPO alcanzó el nivel de 10 h de PPO
  desde cero. Después se degradó porque colapsó su entropía, algo que se puede ajustar.
- Partidos en ventana abiertos para el equipo: modelo elegido contra v2.3, y striker clon con el
  keeper elegido contra v2.3.
- **Propuesta: empezar de nuevo desde imitación (corrida5)**, sin seguir el modelo elegido, que
  queda como entrega de respaldo:
  1. imitación de la v2.3 para los **dos** roles (hoy solo existe la del striker);
  2. recompensa v4 = v3 + un término del striker que premie moverse hacia el frente y castigue
     moverse de espaldas, proporcional a (velocidad · frente) / 400;
  3. PPO más suave para no destruir lo imitado: tasa de aprendizaje más baja, fases más largas y
     la entropía vigilada;
  4. en cada chequeo: benchmark de 8 semillas, `sonda_espaldas.py` y partidos en ventana.

## Sesión 2026-10-24 (56) — Experimento v2.5: las ideas de los rivales del torneo, una por una

**`experimentos/soccer_team_DVF_v25.py`** (base v2.3). Interruptores por variable de entorno
`DVF25` (lista separada por comas); sin ella juega igual que la v2.3. Verificado: 6 de 6
marcadores idénticos con las mismas semillas.

- `linea`: keeper sobre la línea de gol. Con la pelota a menos de 420 px (en X) de su línea entra
  al arco (centro a 20 px de la línea), sigue la Y de la pelota de poste a poste (255–625), la
  mira siempre de frente y la despeja si la tiene a menos de 85 px justo adelante. Sale del modo
  con la pelota a más de 500 px.
- `directo`: el striker le pega sin rodearla si el empuje sale a menos de 55° del eje del arco
  rival.
- `cara`: a menos de 110 px solo empuja con la pelota en el sector 3 (±20°). Si está en el 2 o el
  4, se corre de costado para centrarla.
- `box`: apariencia 'box'.
- Helpers nuevos: `ball_world()` (posición estimada de la pelota con los sensores + la pose
  propia) y `_move_toward()` (de la v2.4).
- Sonda de la estimación: el error es chico con la pelota cerca (sectores laterales, 9–25 px) y
  grande con la pelota lejos en el sector 3, porque ±20° a 500 px son más de 100 px de costado.
  El sensor de distancia es exacto (error 0).

**Benchmark** (8 semillas por lado, ruido 3, 10–14 procesos; neto por par de partidos, G-E-P en
16 partidos):

| variante | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| base (= v2.3) | +10,5 (15-1-0) | +6,2 (14-2-0) | +0,0 (5-6-5) |
| linea | +9,4 (15-0-1) | +3,8 (10-1-5) | −1,1 (3-5-8) |
| directo | +6,4 (16-0-0) | +5,2 (13-0-3) | −0,6 (6-2-8) |
| **cara** | **+11,9 (16-0-0)** | +6,1 (11-4-1) | **+0,6 (8-2-6)** |
| box | +10,5 (15-1-0) | +6,2 (14-2-0) | +0,0 (5-6-5) |
| las cuatro | +10,6 (16-0-0) | +3,1 (10-2-4) | −1,8 (3-2-11) |

- **box da exactamente los mismos números que la base**, partido por partido: confirma que la
  forma es solo visual y que la hitbox es la misma.
- **linea empeora** contra v1 (−2,4) y v2.3 (−1,1): sobre la línea cubre menos ángulo y la Y
  estimada llega tarde. Así como está, no sirve.
- **directo empeora contra NormalTeam** (−4,1; hace menos goles) y queda neutro contra v1 y v2.3.
- **cara mejora un poco en todo** (+1,4 contra NT, +0,6 contra v2.3, que gana 8 de 16), pero
  dentro del ruido. Hay que confirmarlo con 16 semillas.
- Las cuatro juntas empeoran: pesa más lo de `linea`.
- Límite: solo medimos contra nuestros equipos y NormalTeam, no contra los rivales del torneo que
  usaban esas ideas. Puede que el keeper en la línea funcione mejor contra delanteros que patean
  de lejos.

## Sesión 2026-10-24 (55) — Torneo rule-based: semifinal. Observaciones de los mejores equipos

- Resultado: el torneo de esta etapa fue solo de rule-based y **DVF perdió en la semifinal**.
- Observaciones del equipo sobre los rivales que jugaron mejor, revisadas contra el motor:
  1. **"Los cubos tienen ventaja de hitbox"**: en el motor no es así. Todos los jugadores tienen
     la misma hitbox física, un cuadrado de 70×70 px (`game/player.py`: `pymunk.Poly` de
     `PLAYER_SIZE = 70`) que gira con el jugador. El `shape` de `get_team_appearance()`
     ('cylinder' | 'cone' | 'box') solo cambia el dibujo 3D (`renderer/scene_3d.py`). Lo que sí
     pasa: el cubo muestra la hitbox real, y nuestro cono la hace parecer más chica. Y la
     orientación importa: pegarle a la pelota con una cara plana la manda derecho, y con una
     esquina la desvía.
  2. **Keeper sobre la línea de gol**: cuando la pelota se acerca, el arquero se mete al arco,
     sigue la línea de gol de poste a poste y mira siempre a la pelota. Nuestra v2.3 hace otra
     cosa: se para a 120–220 px del arco mirando al campo (arco propio a la espalda), sigue la
     pelota de costado y sale a despejar si la pelota está adelante a menos de 300 px.
  3. **Striker que pega directo**: cuando el ángulo alcanza para mandar la pelota al campo rival,
     le pega sin rodearla. La v2.3 la rodea (órbita) siempre que el arco rival no esté en los
     sectores de adelante (2, 3 y 4).
- Propuesta (sin implementar): un experimento v2.5 en `experimentos/` con cada idea por separado
  (keeper en la línea, golpe directo, cara plana hacia la pelota y apariencia 'box'), medido con
  el benchmark contra v2.3, v1 y NormalTeam (8 semillas por lado).

## Sesión 2026-10-19 (54) — ¿Por qué el striker DL se mueve tan al azar?

- Partidos en ventana del modelo elegido contra v2.3: DL a la izquierda 0–3, DL a la derecha 0–1.
- Pregunta del equipo: el striker DL parece errático comparado con la v2.3.
- `soccer_team_DVF_DL.py`: variable `DVF_DL_ARGMAX=1` para jugar determinista (la acción más
  probable de cada control) en vez de sortear. Por defecto sigue sorteando; el paquete
  `entrega/red_DL` no cambió.
- Medido con 16 semillas por lado (neto por par de partidos):

| modo | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| sorteo (por defecto) | +0,9 | −9,9 | −12,6 |
| determinista | −8,1 (2-2-28) | −21,8 | **−115,0** (52,7 goles de saque en contra) |

- Conclusión: el azar es parte de cómo aprendió a jugar la política de PPO. Sin azar se traba
  en las mismas situaciones; por ejemplo, el keeper no sale de su spawn en el saque. Las otras
  causas del juego errático:
  - la red ve menos: 10 sectores de sensor de ~36° más su posición y velocidad, contra las
    posiciones exactas que lee la v2.3;
  - aprendió poco a atacar: el gol es una señal rara y la entropía del striker sigue en ~2,1 de
    3,3.

## Sesión 2026-10-19 (53) — Resumen para el equipo y partidos en ventana

- Nuevo documento compartido **"DVF — Resumen para el equipo"** (Claude Doc,
  https://claude.ai/code/artifact/b8ca6c19-e7c6-4be0-9855-6ebfe47a11ea). Contiene: estado de las
  entregas; dos gráficas dibujadas desde sus datos; qué aprendió la red y qué aprendimos; cómo
  funciona todo (tabla de piezas y archivos); pendientes con los tutores.
  - "Contra v2.3 pasamos de −91 a −12,6 por par de partidos": neto en partidos de la rama
    principal, contra NormalTeam, v1 y v2.3, con el modelo elegido marcado.
  - "El entrenamiento engaña": % de goles a favor por etapa, con el resultado real contra v2.3
    debajo.
- Partidos en ventana con el modelo elegido (`models/DVF_*.npz` = `entrega/red_DL`) contra el
  rule-based v2.3, uno de cada lado: `run.py soccer_team_DVF_DL soccer_team_DVF_v2` y al revés.

## Sesión 2026-10-19 (52) — Resultado de corrida4 (1 h suave desde el modelo elegido)

- corrida4 terminó sola a las 11:29 ("train_dl.py terminó bien (código 0)"): 1,03 h y 5 fases.
  El lanzamiento desacoplado funcionó. El monitor hizo un chequeo a las 10:57 (criterio −13,8) y
  se cerró al terminar el supervisor (el de las 11:27 no alcanzó a correr).
- Evaluación final del modelo de corrida4 (16 semillas por lado, neto por par de partidos):

| modelo | NormalTeam | v1 | v2.3 | criterio |
|---|---|---|---|---|
| **elegido (corrida3 23:36)** | **+0,9** | **−9,9** | **−12,6** | **−11,3** |
| corrida4 10:57 (8 semillas) | −0,4 | −8,6 | −18,9 | −13,8 |
| corrida4 final 11:29 | −2,8 | −13,1 | −23,6 | −18,4 |

- **La hora extra empeoró el modelo.** Pasó lo mismo que en la noche: con el entrenamiento
  alternado, PPO lo desestabiliza en vez de afinarlo. **Se mantiene el modelo elegido** en
  `entrega/red_DL/`, que no se tocó.
- Si se quiere seguir mejorando, no alcanza con más horas: hace falta cambiar el método (tasa de
  aprendizaje más baja para afinar, fases más largas o entrenar un solo rol a la vez).

## Sesión 2026-10-19 (51) — Gráficos de todo el aprendizaje

- **`scripts/graficar_partidos.py`** (nuevo) → `models/runs/_analisis/partidos.png`: neto por par
  de partidos contra NormalTeam, v1 y v2.3 a lo largo del tiempo. Usa solo las evaluaciones con
  la corrección del violeta (sesiones 26–49, datos copiados en el script), separa rama principal,
  rama del clon y noche1, y marca el modelo elegido y los cambios de configuración.
- **`analizar_fases.py`**:
  - Etapas actualizadas: D (corrida2 PPO), E (rama del clon), F (corrida3) y G (corrida4).
  - Corridas por defecto: noche1, corrida2, corrida3 y corrida4.
  - Ya no pisa fechas vecinas en el eje.
  - El `print` no se corta por la consola cp1252.

## Sesión 2026-10-19 (50) — corrida4: 1 h de entrenamiento suave desde el modelo elegido

- La entrega de la red todavía no abrió (figura para el 13/01/2027 y está bloqueada hasta que la
  actividad Metadata quede marcada como completa). Se mandó la consulta a los tutores. Mientras
  tanto, entrenamiento suave.
- `models/runs/_init_corrida4/`: el par elegido (corrida3 `*_232821_IT0140`) **con** su estado de
  optimizador, para seguir sin saltos. La copia de entrega (`entrega/red_DL/`) no se toca.
- **`lanzar_corrida.ps1 -Desacoplado`** (nuevo): crea el supervisor por WMI (`Win32_Process.Create`)
  con `cmd /c` para redirigir la salida, en prioridad BelowNormal y oculto. Así queda fuera del
  árbol de procesos de la app y no muere si se cierra (lo que probablemente pasó a las 05:12).
  Verificado: el padre del supervisor es ese `cmd`, no la app, y los 9 procesos van en
  BelowNormal.
- **corrida4 lanzada a las 10:27** (supervisor 26172): 6 workers (v2.3 ×3, v1 ×2, NT ×1),
  entropía 0,01 / 0,01, hasta las 11:27. Retomó pesos y optimizador.
- Monitor desacoplado (PID 468) cada 30 min, que escribe en `models/runs/corrida4/monitoreo.md`.
  Referencia para comparar (16 semillas por lado): NT +0,9 · v1 −9,9 · v2.3 −12,6 (criterio
  −11,3).

## Sesión 2026-10-19 (49) — Elección del modelo DL (evaluación final, 16 semillas por lado)

- El rule-based (`entrega/soccer_DVF.py`) y la metadata ya fueron subidos por el equipo.
- Ojo con las evaluaciones del "modelo actual" hechas durante el entrenamiento: cada partido del
  benchmark carga los `.npz` al arrancar, así que mezclaban guardados de varios minutos. Por eso
  esta evaluación final usa checkpoints fijos. El "modelo de las 23:35" corresponde a corrida3
  `*_20261018_232821_IT0140` (23:36): el striker del fin del ciclo 2 y el keeper a mitad de su fase.
- Evaluación con 96 partidos por candidato (16 por lado y rival), 14 procesos, corrección
  violeta. Neto por par de partidos:

| candidato | NormalTeam | v1 | v2.3 | criterio (v1+v2.3)/2 |
|---|---|---|---|---|
| **corrida3 23:36** | +0,9 ± 1,7 (16-7-9) | −9,9 ± 1,9 (0-2-30) | **−12,6 ± 1,8** | **−11,3** |
| corrida3 23:45 | +2,8 ± 1,9 (17-6-9) | −11,1 ± 1,9 | −17,0 ± 1,9 | −14,1 |
| corrida2 ciclo 23 (PPO) | **+4,5 ± 2,2 (23-2-7)** | −9,7 ± 1,7 | −18,5 ± 2,0 | −14,1 |
| corrida2 ciclo 26 (clon) | +0,9 ± 2,6 | −9,2 ± 1,7 | −17,5 ± 2,6 | −13,4 |

- **Elegido: corrida3 23:36.** Contra v1 empatan todos (~−9/−11). La diferencia está contra v2.3,
  donde es claramente mejor (−12,6 contra −17/−18,5, fuera del ruido). Si importara más ganarle a
  rivales tipo NormalTeam, la alternativa es corrida2 ciclo 23 (+4,5, gana 23 de 32).
- **Paquete listo en `entrega/red_DL/`**: `soccer_team_DVF_DL.py` + `models/DVF_striker.npz` y
  `DVF_keeper.npz`, solo pesos (sin `opt_*`, 220 KB cada uno). El equipo DL los carga solo, sin
  variables de entorno, desde su carpeta `models/`. Trae la corrección del violeta. La misma copia
  quedó en `models/DVF_*.npz` (la ruta por defecto del proyecto).
- Verificado jugando el paquete (8 semillas por lado): NormalTeam +0,6, v1 −8,8, v2.3 −12,0. Da lo
  mismo que la evaluación del candidato, dentro del ruido.
- Pendiente con los ayudantes: el formato de entrega de la red. Si corren la red con su propia
  `build_observation`, no se aplica la corrección del violeta.

## Sesión 2026-10-19 (48) — Resultado de la noche (09:45, 15 min antes de la entrega)

- **Metadata generada**: `python scripts/metadata_entrega.py noche1 corrida2 corrida3` →
  `entrega/metadata_DVF.md` y `.csv`. 29,0 h, CPU de 16 núcleos sin GPU, 4 épocas, 3 capas, 394
  neuronas, 2 modelos (170 fases alternadas). Ojo: corrida2 y corrida3 corrieron en paralelo
  ~1,25 h (22:30–23:45), así que en la suma ese tramo cuenta doble (son horas-proceso).
- **El entrenamiento se cortó a las 05:12:23**: el último IT está en el log y los `.npz` son de
  las 05:12:12. Murieron a la vez train_dl, el supervisor, el monitor y los dos evaluadores, sin
  registro en `supervisor.log`. No hubo reinicio ni eventos de energía (Kernel-Power 41/42/107,
  6008). Lo más probable es que se haya cerrado la app que los lanzó y se llevara a sus procesos
  hijos; no está confirmado. Por eso los rankings automáticos no corrieron. corrida3 quedó en 6,0 h
  y 34 fases.
- **Monitor horario** (`models/runs/corrida3/monitoreo.md`, criterio = promedio contra v1 y
  v2.3): 02:35 −16,8 · 03:38 −26,4 · 04:40 −19,8. La noche no mejoró sobre el modelo de las 23:35
  (−11,8).
- **Mejores candidatos DL**: corrida3 de las 23:35 (−11,8), clon ciclo 26 (−13,5) y corrida2
  ciclo 23 (−14,3). Falta una evaluación final para elegir. Lección: lanzar los procesos largos
  de forma que no dependan de la app (por ejemplo, con el Programador de tareas de Windows).

## Sesión 2026-10-19 (47) — Configuración final de la noche (el equipo se va a dormir)

- corrida3 cortada 1 s después del guardado de las 01:33:19 (2,39 h, 11 fases). **Relanzada a las
  01:33:36** con striker 0,01 / keeper 0,01 y **10 workers** (v2.3 ×5, v1 ×3, NT ×2), parte 5,
  supervisor 25248.
- **Hasta las 08:00**: `models/runs/corrida3/until.txt` = 2026-10-19T08:00 (lo releen el
  supervisor y train_dl).
- Evaluadores automáticos esperando al supervisor 25248: corrida2 (PID 18888, combos
  12/19/23/final) y corrida3 (PID 22352). A las ~08:00 escriben `eval/mejor.txt` en cada corrida.
- **`scripts/monitorear.py`** (nuevo, lanzado: PID 1140): cada 60 min agrega a
  `models/runs/corrida3/monitoreo.md`:
  - las fases nuevas, con entropía y % de goles a favor;
  - una evaluación en partidos de 8 semillas por lado (3 procesos), con neto, G-E-P y criterio;
  - una copia del par evaluado en `models/runs/corrida3/monitoreo/<hora>_*.npz`.
  Termina solo cuando muere el supervisor. Problema encontrado al probarlo: por un pipe en Windows
  el "±" llegaba roto y no se leían las filas. Se corrigió con `PYTHONIOENCODING=utf-8`.
- Energía (solo lectura, ya estaba bien): enchufada, sin suspensión ni hibernación. Solo se apaga
  la pantalla a los 10 min, y eso no afecta al entrenamiento. La tapa tiene que quedar abierta.
  Los apagados de golpe por temperatura no se pueden evitar desde la configuración.

## Sesión 2026-10-19 (46) — Chequeo de las 01:28: el striker con 0,015

- Entropía del striker por fase: 0,32 (0,01) → **1,85 → 2,48** (0,015). Volvió a explorar, pero
  sigue subiendo y ya está en el borde alto de lo sano.
- Partidos (8 semillas por lado, corrección violeta, neto por par de partidos):

| corrida3 | NormalTeam | v1 | v2.3 | suma de los tres |
|---|---|---|---|---|
| 23:35 (0,01) | +3,9 | −10,5 | −13,1 | −19,7 |
| 00:50 (0,01) | +3,1 | −13,8 | −15,0 | −25,7 |
| **01:30 (0,015)** | **−18,5 (0-0-16)** | −6,5 | −23,1 | **−48,1** |

- Lectura: con más exploración el striker juega más al azar en los partidos (el equipo DL sortea
  sus acciones). Casi no hace goles (0,2–1,2 por partido) y contra NormalTeam recibe 8,4 goles de
  saque por par de partidos. El −6,5 contra v1 es un partido trabado (3–4 goles en contra, casi
  ninguno a favor), no una mejora real.
- El costo de corto plazo es mayor que lo esperado y la entropía va hacia el azar. Recomendación:
  volver a 0,01. El ranking de la mañana conserva los checkpoints buenos de antes del cambio.

## Sesión 2026-10-19 (45) — Chequeo de las 00:48 (corrida3, 1,87 h, 8 fases)

- Entrenamiento: % de goles a favor estable en 21–31 %. **La entropía del striker colapsa**:
  2,37 → 1,40 → **0,32** (ciclos 2–4). Es el mismo patrón que tuvo la rama del clon antes de
  empeorar. La del keeper sigue sana (~2,2).
- Partidos (8 semillas por lado, corrección violeta, neto por par de partidos):

| corrida3 | NormalTeam | v1 | v2.3 | criterio (v1+v2.3)/2 |
|---|---|---|---|---|
| 23:35 | +3,9 (11-0-5) | −10,5 | −13,1 | **−11,8** |
| 00:20 | −0,1 (6-4-6) | −15,0 | −17,9 | −16,5 |
| 00:50 | +3,1 (11-1-4) | −13,8 | −15,0 | −14,4 |

  Oscila sin mejorar desde las 23:35. El riesgo está acotado: el ranking de las 07:00 evalúa los
  fines de fase de toda corrida3 y elige el mejor checkpoint aunque el modelo empeore.
- Opción planteada al equipo: subir la exploración del striker a 0,015 para frenar el colapso.
- **Aplicado (decisión del equipo)**:
  - Frené los dos evaluadores y corté corrida3 2 s tras el guardado de las 00:57:02 (1,87 h, 8
    fases).
  - **Relanzada a las 00:57:17** con striker 0,015 / keeper 0,01, 8 workers (parte 4, supervisor
    26844). Arrancó por una fase del striker con entropía 0,50.
  - Evaluadores rearmados sobre el supervisor 26844: corrida2 (PID 9328) y corrida3 (PID 24124).
  - Qué mirar en el chequeo de las ~01:28: si la entropía del striker se estabiliza en ~1,5–2,5
    (sano) o se dispara hacia ~3 (azar, volver a 0,01).

## Sesión 2026-10-19 (43) — Paquete para el equipo

- **`LEEME_EQUIPO.md`** (nuevo): resumen para Diego y Fernando. Cubre el estado de las entregas,
  los equipos rule-based, las corridas DL con sus mejores resultados, los hallazgos importantes,
  cómo probar y las dudas abiertas con los ayudantes.
- **`scripts/empaquetar.py`** (nuevo): arma `compartir/DVF_robotic_soccer_<fecha>.zip`.
  - **Liviano** (23 MB, 256 archivos): código, documentación, entregas, logs, evaluaciones, los
    modelos finales de cada corrida y los pares candidatos en `models/candidatos/` (ciclos 12, 19 y
    23 de corrida2 y la rama del clon).
  - **`--completo`** (1,1 GB, 2389 archivos): lo mismo más todos los checkpoints intermedios.
  - En ninguno de los dos va `env/`: tiene rutas absolutas de esta PC y se rearma con
    `pip install -r requirements.txt`. Tampoco van las cachés.
- Se armó con corrida3 entrenando. Sus `.npz` se guardan de forma atómica, así que entraron
  enteros: son los del momento del zip, no los finales de las 07:00.
- El equipo no necesita los checkpoints intermedios, así que **se borró el zip completo** y queda
  solo el liviano (`compartir/DVF_robotic_soccer_2026-10-19_0015.zip`, 23 MB). La opción
  `--completo` sigue en el script por si alguna vez hace falta.

## Sesión 2026-10-19 (44) — Chequeo de las 00:15 (corrida3, 1,33 h, 5 fases)

- Entrenamiento: % de goles a favor por fase 20 → 22 → 23 → 31 → 25 %. La entropía del striker
  bajó de 2,37 a 1,40 sin colapsar (la rama del clon había quedado en 0,2). CPU ~66 % durante la
  evaluación.
- Partidos (8 semillas por lado, 2 procesos; neto por par de partidos):

| corrida3 | NormalTeam | v1 | v2.3 | criterio |
|---|---|---|---|---|
| 23:35 | +3,9 (11-0-5) | −10,5 ± 2,6 | −13,1 ± 2,6 | −11,8 |
| 00:20 | −0,1 (6-4-6) | **−15,0 ± 1,1** | −17,9 ± 3,3 | −16,5 |

- Empeoró respecto de las 23:35, y contra v1 la diferencia está fuera del ruido. Con el
  entrenamiento alternado la política oscila entre fases: el % del entrenamiento sube, pero eso no
  siempre se ve en los partidos. **Por eso el modelo final se elige con el ranking de la mañana y
  no se usa el último checkpoint a ciegas.** El de las 23:35 (fin de la fase del striker del
  ciclo 2) está entre los fines de fase que evalúa el evaluador de corrida3.
- No se cambia nada. Próximo chequeo en 30 min.

## Sesión 2026-10-19 (42) — Archivo de entrega renombrado a `soccer_DVF.py`

- Decisión del equipo: entregar el rule-based como **`entrega/soccer_DVF.py`** (antes
  `entrega/soccer_team_DVF.py`). El contenido no cambió: es la v2.3. El archivo no se nombra a sí
  mismo en ningún lado, así que alcanza con renombrarlo.
- Verificado: carga y juega con el benchmark. Contra la v2.3 de la raíz da +0,0, como debe ser
  entre dos copias del mismo equipo.
- `PLAN_ENTREGA.md` actualizado con la ruta nueva. Las sesiones anteriores del CHANGELOG quedan
  con el nombre viejo como registro.
- Los archivos de la raíz (`soccer_team_DVF.py` = v1, `soccer_team_DVF_v2.py` = v2.3) no se
  tocan: el entrenamiento los importa como rivales.

## Sesión 2026-10-19 (41) — Análisis de `imr-mrk-V.py` (subido a la entrega rule-based)

Archivo `C:\BECA\varios\imr-mrk-V.py`, subido a la entrega por alguien del equipo.

- **Qué es**: es nuestra **v1.0**. Tiene el mismo código y la misma apariencia ("DFC", turquesa)
  que `soccer_team_DVF.py`, pero sin el módulo `_TeamTactics` de la v1.1 (defensa del saque) y sin
  `move_upfield/downfield`. Cabecera mínima ("# name: imr-mrk-V", autores Diego, Valentino y
  Fernando).
- **Usa solo sensores**: 0 lecturas de `body.*`. Nuestra v2.3 (`entrega/soccer_team_DVF.py`) lee
  `body.position/velocity/angle` en 13 lugares. Si la cátedra no permite leer el body, este
  archivo cumple y la v2.3 no (pregunta todavía abierta con los ayudantes).
- **Nombre**: no sigue la convención `soccer_team_<equipo>.py` de la Anleitung.
- **Benchmark** (8 semillas por lado, ruido 3, neto por par de partidos):

| rival | neto | G-E-P (16) |
|---|---|---|
| NormalTeam | +11,0 ± 3,8 | 15-0-1 |
| v1.1 | −1,8 ± 2,0 (empate dentro del ruido) | 5-4-7 |
| **v2.3 (nuestra entrega)** | **−6,5 ± 2,8** | 3-0-13 |

  Pelota trabada en esquinas el 31,4 % del tiempo y 14,5 reinicios por pelota trabada por partido:
  es el problema de esquinas que la v2.x mejoró.
- **Conclusión**: la v2.3 le gana claro (13 de 16 partidos). Conviene que la entrega sea
  `entrega/soccer_team_DVF.py`, salvo que la cátedra prohíba leer el body; en ese caso esta versión
  es la alternativa que cumple.

## Sesión 2026-10-19 (40) — corrida3 baja a 8 workers

- Con 12 workers la PC iba muy cargada mientras se usaba.
- Primero frené los dos evaluadores, porque esperaban al supervisor de corrida3 y habrían
  arrancado al cortarlo. Después corté corrida3 2 s tras el guardado de las 00:01:53 (1,14 h, 4
  fases).
- **Relanzada a las 00:02:06 con 8 workers** (parte 3, supervisor 19908): v2.3 ×4, v1 ×2, NT ×2.
  CPU total ~52 %.
- Evaluadores rearmados sobre el supervisor 19908: corrida2 (PID 30544) y corrida3 (PID 29952).

## Sesión 2026-10-18 (39) — Solo la rama PPO (corrida3) con 12 workers

- Decisión del equipo: seguir con la rama PPO. Son 12 workers y no 14 porque la PC se sigue
  usando. Habrá chequeos cada 30 min hasta que el equipo se vaya a dormir.
- corrida2 (clon) cortada 2 s después del guardado de las 23:44:49 (10,40 h, 56 fases). corrida3
  siguió con sus 4 workers durante ese corte: el corte por corrida funciona.
- corrida3 cortada 1 s después del guardado de las 23:45:00 (0,97 h, 3 fases) y **relanzada a
  las 23:45:12 con 12 workers** (parte 2, supervisor 28224): v2.3 ×6, v1 ×3, NormalTeam ×3.
  Retomó sus propios pesos y optimizador ("Resumed … (+optimizer)").
- Evaluadores automáticos rearmados, **los dos esperando al supervisor de corrida3** (que es el
  que termina a las 07:00): corrida2 (PID 21288, combos 12/19/23/final) y corrida3 (PID 20820).
- Sobre el objetivo: buscar 0 goles en contra no es realista. El criterio para elegir modelo ya es
  la **diferencia de gol neta**, y la recompensa equilibra +20 por gol a favor contra −5 (keeper)
  / −1 (striker) por gol en contra. Para seguir el progreso conviene mirar también el G-E-P
  (ganados-empatados-perdidos) contra cada rival.

## Sesión 2026-10-18 (38) — Comparación de las dos ramas (23:32, 8 semillas por lado)

- Entrenamiento (con 4 workers cada fase tarda ~20 min): corrida2 (clon) 30–33 % de goles a
  favor, pero la entropía del striker sigue colapsando (0,20). corrida3 (PPO) 20–23 %.
- **Partidos** (corrección violeta, neto por par de partidos; criterio = promedio contra v1 y v2.3):

| rama | NormalTeam | v1 | v2.3 | criterio |
|---|---|---|---|---|
| punto de partida de las dos (22:15) | — | ~−9 / −10 | ~−18 | ~−13,5 / −14,3 |
| corrida2, clon (23:35) | −4,8 (1-1-14) | −18,1 | −28,1 | **−23,1** (empeoró) |
| **corrida3, PPO (23:35)** | **+3,9 (11-0-5)** | −10,5 | **−13,1** | **−11,8** (el mejor hasta ahora) |

- La rama del clon **se degradó** con PPO: entropía casi nula y recibe el doble de goles. La rama
  PPO mejoró sobre su punto de partida (c23: −14,3) y es la mejor contra v2.3 en partidos.
- **Recomendación: seguir solo con corrida3 (PPO)** y darle toda la CPU. Los checkpoints del clon
  quedan y su evaluador automático sigue armado para el ranking de la mañana.

## Sesión 2026-10-18 (37) — Las dos ramas en paralelo (clon en corrida2, PPO en corrida3)

Decisión del equipo: correr las dos ramas a la vez, con la mitad de los workers cada una (la PC
se sigue usando), y antes de dormir elegir una para darle toda la CPU.

- **Riesgo encontrado antes de lanzar**: si una corrida se caía, su supervisor mataba todos los
  workers del proyecto creados desde su arranque, **incluidos los de la otra corrida**.
  - `train_dl.py` ahora escribe su PID en `models/runs/<run>/train_pid.txt`.
  - `supervisar_entrenamiento.py` mata solo los workers con `spawn_main(parent_pid=<ese PID>,`
    en la línea de comando, que es como multiprocessing marca a los hijos de cada proceso.
- **`scripts/lanzar_corrida.ps1`** (nuevo, genérico): `-Run`, `-InitFrom`, `-Workers` (4),
  entropías, `-Opponents` con pesos, `-Hasta`. No lanza si esa corrida ya corre. Con 4 workers,
  la lista por defecto da v2.3 ×2, v1 ×1 y NormalTeam ×1.
- **`scripts/cortar_corrida.ps1`** (nuevo): corta una sola corrida después de un guardado. Primero
  frena su evaluador, después mata su supervisor, su `train_dl` y sus workers (por `parent_pid`).
- corrida2 cortada 1 s después del guardado de las 22:29:49 (9,43 h, 53 fases).
- **corrida2 (rama del clon)**: relanzada a las 22:30:02 con 4 workers (parte 7, supervisor 23580).
- **corrida3 (rama PPO)**: nueva, lanzada a las 22:30:08 desde `corrida2/respaldo_antes_clon`
  (striker de PPO + keeper, con su optimizador; parte 1, supervisor 20616). Cuenta sus ciclos y
  horas aparte.
- Evaluadores automáticos, uno por corrida, con 7 workers cada uno para no saturar la PC a las
  07:00: corrida2 (PID 28552, combos 12/19/23/final) y corrida3 (PID 25304). Los PID están en
  `_salidas/<run>_evaluador_pid.txt` y los rankings en `models/runs/<run>/eval/mejor.txt`.
- Metadata: las horas de corrida2 y corrida3 corren en paralelo. Al sumarlas son horas-proceso,
  no horas de reloj (aclararlo en la planilla).

## Sesión 2026-10-18 (36) — Análisis antes de decidir la noche (8 semillas por lado)

Reevaluación de 4 candidatos de corrida2 con el doble de partidos (16 por rival; corrección
violeta; neto por par de partidos; criterio = promedio contra v1 y v2.3):

| candidato | NormalTeam | v1 | v2.3 | criterio |
|---|---|---|---|---|
| c12 (16:45, PPO) | −4,0 ± 1,8 (0-3-13) | −9,2 ± 2,5 | −34,9 ± 4,0 | −22,1 |
| c19 (19:50, PPO, rivales ponderados) | **+7,2 ± 3,5 (13-0-3)** | −9,4 ± 4,2 (2-1-13) | −22,8 ± 2,9 | −16,1 |
| c23 (20:58, PPO antes del clon) | +5,1 ± 2,7 (12-1-3) | −10,4 ± 1,8 | −18,2 ± 2,5 | −14,3 |
| **c26 (22:10, rama del clon)** | +1,2 ± 3,3 (9-2-5) | **−9,1 ± 2,1** | **−17,8 ± 3,7** | **−13,5** |

- Con 4 semillas, c12 parecía el mejor contra v1 (−5,8). Con 8 da −9,2. **Las decisiones van con
  8 semillas.**
- c23 (rama PPO) y c26 (rama del clon) **empatan** dentro del ruido. La rama del clon alcanzó en
  1 hora lo que la de PPO logró en ~10. Contra v1, todos los candidatos están clavados en ~−9/−10.
- Referencia rule-based: v2.3 le gana a v1 por +5,6 y a NormalTeam por +9,1. El DL todavía está
  claramente por debajo contra v1 y v2.3, y ya le gana a NormalTeam (12–13 de 16 partidos).
- Diferencia entre ramas para la noche: el striker del clon casi no explora (entropía 0,28) y el
  de PPO sí (~2,4), con mejora sostenida. Opción nueva: correr **las dos ramas en paralelo** con
  4 workers cada una (la misma carga de hoy) y que el ranking de la mañana decida.

## Sesión 2026-10-18 (35) — Chequeo de la rama del clon (22:11, 1 h de PPO desde el clon)

- **Entrenamiento** (ciclos 24–26): el % de goles a favor cayó de 27–38 % (rama PPO) a 17–19 % y
  se recupera de a poco (26 % en el ciclo 26). **La entropía del striker colapsa**: 0,68 → 0,56 →
  **0,28**. Casi no explora, así que PPO tiene poco margen para mejorarlo.
- **Saque**: el clon va 100 % adelante, pero igual pierde el primer toque (0 de 10 contra v2.3; a
  ~204 px al segundo). Goles de saque en contra en 300 s: 1 contra v2.3 y 2 contra v1. El keeper
  vuelve algo menos (x≈377–381 a los 2 s, antes 364).
- **Partidos** (corrección violeta, neto por par de partidos; criterio = promedio contra v1 y v2.3):

| modelo | NormalTeam | v1 | v2.3 | criterio |
|---|---|---|---|---|
| rama PPO 20:55 | −0,2 | −9,8 | −13,0 | **−11,4** |
| clon solo (sin PPO) | +3,5 | −10,8 | −18,2 | −14,5 |
| rama del clon 22:10 | −4,5 | −8,8 (0-2-6) | −16,8 | −12,8 |

  Las diferencias están dentro del ruido (±4–6), así que el clon no mejoró el resultado en esta
  hora. Además, la rama PPO venía mejorando de forma sostenida (v2.3: −90,8 → −18,8 → −13,0) y con
  la entropía sana (~2,3–2,6).
- **Recomendación**: volver a la rama PPO para la noche, restaurando striker y keeper de
  `respaldo_antes_clon/`. Esta hora del clon queda en los checkpoints y entra en el ranking de la
  mañana. Alternativa: seguir con el clon pero con la exploración del striker en 0,02, para frenar
  el colapso.

## Sesión 2026-10-18 (34) — corrida2 sigue desde el striker clonado

- Clon reentrenado con más datos y más épocas (9 partidos de 240 s, 32.400 decisiones, 40
  épocas). Precisión de validación: **90 % avance, 87 % lateral, 99,7 % giro** (antes 82/79/99).
- Primero frené el evaluador automático viejo, para que no arrancara al cortar el supervisor.
  Después corté 2 s tras el guardado de las 21:10:41 (8,21 h, 46 fases). La fase del striker
  del ciclo 24 no llegó a anotarse y se repite, ahora desde el clon.
- Respaldo del striker de PPO, el keeper y `run.json` en
  `models/runs/corrida2/respaldo_antes_clon/`. `striker.npz` reemplazado por el clon (solo pesos).
- **Relanzada a las 21:11:02** (parte 6, supervisor PID 6752), misma configuración: rivales
  ponderados, entropía 0,01 / 0,01, 8 workers, prioridad baja, hasta 07:00. El log confirma
  "Resumed striker (weights only)" (el clon, con Adam nuevo) y "Resumed keeper (+optimizer)".
  Arranca con entropía del striker 0,54 (el clon es casi determinista) y pérdida de valor alta (62)
  porque el crítico tiene que reajustarse.
- **Evaluador automático rearmado** (PID 28120) para el supervisor nuevo, con combinaciones de los
  ciclos 12, 19, 23 (último del striker de PPO) y final. El ranking de la mañana compara las dos
  ramas.
- Chequeo del clon programado para las ~22:10.

## Sesión 2026-10-18 (33) — Ajuste del ataque: imitación del striker v2.3 (sin cortar corrida2)

- **`scripts/imitar_striker.py`** (nuevo):
  - Graba (observación, acción) del striker rule-based v2.3 jugando de azul en el entorno del
    entrenamiento, con nuestro keeper DL y rivales NormalTeam / v1 / v2.3. Toma la acción cada 4
    frames, que es cuando decide la red.
  - Entrena la red del striker para copiarlo, partiendo de los pesos de corrida2.
  - Guarda `models/imitacion/striker_clon.npz` solo con pesos (si se usa para seguir con PPO,
    arranca con un Adam nuevo), más `datos_striker_v23.npz` e `imitacion.json`.
- Datos: 21.600 decisiones en 39 s (6 partidos de 240 s). Tras 15 épocas, precisión de validación
  82 % (avance), 79 % (lateral) y 99 % (giro). La pérdida seguía bajando: más épocas mejorarían.
- **Partidos** (clon + keeper de corrida2 de las ~21:00, corrección violeta, neto por par de
  partidos; entre paréntesis, goles a favor por partido de cada lado):

| striker | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| PPO corrida2 20:55 | −0,2 (5,0 / 3,5) | −9,8 (1,0 / 2,8) | −13,0 (0,2 / 0,2) |
| **clon de v2.3** | +3,5 (8,5 / 11,5) | −10,8 (4,2 / 5,0) | −18,2 (0,8 / 0,8) |

- Lectura: el clon **ataca bastante más** (contra v1 hace ~2,5 veces más goles) pero recibe más
  (goles de saque en contra contra v2.3: 6,6 contra 1,6), y el neto queda parecido. El keeper de
  corrida2 está acostumbrado al striker de PPO, no al clon.
- Opciones para la noche (a decidir con el equipo):
  1. Dejar corrida2 como está: defensa sólida, ataque casi nulo.
  2. Relanzar corrida2 con el striker inicializado desde el clon y seguir con PPO, con los mismos
     rivales ponderados y exploración 0,01. Los candidatos anteriores (ciclos 12 y 19) siguen en
     el ranking automático de la mañana, así que no se pierde nada.
  3. Subir los pesos densos de ataque en la recompensa (v4). No está probado: es más arriesgado
     para dejarlo solo de noche.

## Sesión 2026-10-18 (32) — Chequeo de las 20:52 y resumen general

- corrida2: 8,0 h, 45 fases. % de goles a favor por fase entre 22 y 38 %. Entropía del striker
  2,65 → 2,37 y del keeper ~2,4: siguen bajando despacio, sin saltos.
- Saque contra v2.3: **0 goles en contra en 13 saques**. El keeper va atrás el 70 % de las veces
  (x≈364 a los 2 s). El striker sigue sin ganar el primer toque (0 de 13; a 207 px al segundo).
- Partidos (corrección violeta, neto por par de partidos): NormalTeam −0,2 (3-2-3), v1 −9,8
  (0-0-8), **v2.3 −13,0** (0-0-8, el mejor hasta ahora; goles de saque en contra: 1,6).
- Evolución contra v2.3: −90,8 (18:41) → −18,8 (19:50) → −13,0 (20:55). Contra v1, −7,8 → −9,8,
  dentro del ruido. **La defensa se aprendió; el ataque contra los rule-based es casi nulo**
  (0,2 goles por partido contra v2.3, 1–2,8 contra v1).
- `analizar_fases.py` y `fases.png` regenerados (la etapa D junta todas las partes de corrida2).

## Sesión 2026-10-18 (31) — Chequeo de las 19:48: la curva se endereza

- Entrenamiento (6,84 h, 39 fases; desde el ciclo 18 con v2.3 ×4, v1 ×2, NT ×2): el % de goles
  a favor se mantiene en ~30 % aunque ahora la mitad de los partidos es contra v2.3. Los goles en
  contra por actualización bajan fase a fase: 4,0 → 3,7 → 3,5 en el striker y 4,2 → 3,4 en el
  keeper.
- **El keeper vuelve al arco en el saque**: su red elige atrás 50 % y derecha 64 % (la dirección
  correcta), y a los 2 s está en x≈341 contra v2.3 y x≈298 contra v1 (antes ~376–398). Goles de
  saque en contra en 300 s contra v2.3: **1** (a las 18:41 eran 19).
- El striker sigue perdiendo el primer toque contra v2.3 (9 de 9), pero ahora la defensa aguanta.
- **Partidos** (corrección violeta, neto por par de partidos, G-E-P en 8):

| modelo | NormalTeam | v1 | v2.3 | goles de saque en contra vs v2.3 |
|---|---|---|---|---|
| ~16:45 (ciclo 12) | −7,8 (1-1-6) | −5,8 | −28,0 | — |
| 18:41 (mezcla pareja) | +6,2 (7-1-0) | −31,8 | −90,8 | 40,6 |
| **19:50 (rivales ponderados)** | +1,0 (4-1-3) | −7,8 (**2-1-5**) | **−18,8** | **4,8** |

  Es el modelo más parejo hasta ahora, el mejor contra v2.3 y el primero que le gana partidos a
  v1. La diferencia con el de las 16:45 contra v1 (−7,8 contra −5,8) está dentro del ruido (±6,4).
- Se deja correr igual hasta las 07:00. Relancé el evaluador automático (PID nuevo, mismo
  supervisor) con las combinaciones **12, 19 y final**, para que el ranking de la mañana incluya
  este modelo aunque después cambie.

## Sesión 2026-10-18 (30) — Chequeo de las 18:41 y configuración para la noche

### Estado (5,95 h, 34 fases)
- Entrenamiento: % de goles a favor por fase 16–24 % → **33–35 %** (ciclos 16–17, los dos
  roles). Entropía del keeper con 0,01: 3,02 → 2,81 → 2,65.
- Keeper en el saque (`sonda_keeper_recompensa.py`): "atrás" 46 % (antes 33 %), entropía 2,76; a
  los 2 s está en x≈376 (antes ≈398). Empieza a aprender, lento.
- Striker en el saque: **retrocedió**. Va adelante el 9 % (a las 17:45 era el 67 %) y contra
  v2.3 pierde el primer toque en 28 de 29 saques, con 19 goles de saque en contra en 300 s.
- Partidos (corrección violeta, neto por par de partidos): NormalTeam **+6,2 (7-1-0)**, v1
  −31,8, v2.3 **−90,8** (40,6 goles de saque en contra). Volvió a sobreajustarse a NormalTeam.

### Causa y ajustes
- `train_dl.py` reparte los rivales por turno (`worker i -> lista[i % largo]`): con 8 workers y
  NT/v1/v2.3 quedaban 3/3/2. v2.3, el rival más duro, era el que menos se entrenaba, y la señal
  fácil de NormalTeam dominaba.
- `lanzar_corrida2.ps1`: `-Opponents` con pesos (los repetidos cuentan más). Default **v2.3 ×4,
  v1 ×2, NormalTeam ×2**. Cada rival va como argumento separado.
- Corte 2 s después del guardado de las 18:45:37 (5,95 h, 34 fases). **Relanzada a las
  18:45:44** (parte 5, supervisor PID 26084), entropía 0,01 / 0,01, 8 workers, prioridad baja,
  hasta 07:00.
- **`scripts/evaluar_al_terminar.py`** (nuevo, lanzado: PID 25608): espera a que muera el
  supervisor y, con 14 workers, evalúa 10 fines de fase + el final y las combinaciones de los
  ciclos 12 (candidato de las 16:45), 17 y final. Después corre `analizar_fases.py` y escribe
  `eval/mejor.txt`: el ranking por neto promedio **contra v1 y v2.3**. NormalTeam se muestra pero
  no decide, porque premia trucos que solo sirven contra él. Log en `eval/auto.log`.
- Si la PC se reinicia durante la noche, mueren el entrenamiento y el evaluador: hay que
  relanzarlos a mano.

## Sesión 2026-10-18 (29) — Keeper con exploración 0,01

- `scripts/lanzar_corrida2.ps1`: nuevo parámetro `-KeeperEntropy` (default **0.01**).
- Corte 2 s después del guardado de las 18:08:55. Hasta ahí: 5,43 h y 31 fases. La fase del
  keeper que estaba a medias (IT 60) se repite.
- **Relanzada a las 18:09:04** (parte 4, supervisor PID 19856): 8 workers, prioridad baja,
  exploración 0,01 para striker y keeper, hasta el lunes 07:00. Ahora ninguna fase usa 0,02.
- Para ver si funcionó: con `sonda_keeper_recompensa.py`, parte 1, la entropía del keeper en el
  saque tiene que bajar de ~3,14 y elegir "atrás" bastante más que el 33 % actual. Con
  `sonda_saque.py`, la x del keeper a los 2 s tiene que bajar de ~398.

## Sesión 2026-10-18 (28) — ¿Por qué el keeper no vuelve al arco? (sin cortar corrida2)

Nueva sonda `scripts/sondas/sonda_keeper_recompensa.py` (prioridad baja).

- **Parte 1 · red del keeper en el saque** (spawn x≈418, mirando a +x; para volver tiene que ir
  atrás y un poco a la derecha). **Las tres redes están prácticamente al azar en el saque**:

| red | entropía (máx. 3,30) | quieto / adelante / atrás |
|---|---|---|
| noche1 05:59 (v1) | 3,23 | 35 / 38 / 27 % |
| noche1 final (v2) | 3,22 | 39 / 22 / 39 % |
| corrida2 ahora (v3) | 3,14 | 35 / 32 / 33 % |

  En toda la noche y en corrida2, el keeper nunca aprendió qué hacer en el saque.
- **Parte 2 · cuánto paga la recompensa v3 al keeper** (240 s contra v2.3, entorno de
  entrenamiento, nuestro striker = red de corrida2, 2 semillas):

| forma de jugar | densa | goles (−5 c/u) | total | goles en contra | x mediana |
|---|---|---|---|---|---|
| al azar | −24,0 | −48,5 | −72,5 | 11,5 | 421 |
| quieto en el spawn | −25,4 | −58,0 | −83,4 | 12,5 | 418 |
| **volver y cubrir** (script) | **+21,3** | −13,5 | **+7,8** | **3,0** | 181 |
| keeper rule-based v2.3 | +12,5 | −12,5 | 0,0 | 2,5 | 216 |

- **Diagnóstico:** la recompensa **no** es el problema. Volver al arco paga ~80 puntos más que
  quedarse cada 4 minutos (la mitad por la parte densa, la mitad por recibir 4 veces menos
  goles), y por paso la señal es unas 4 veces más fuerte que la del striker. El script "volver y
  cubrir" recibe 3 goles contra 12,5 si se queda quieto. El problema es de aprendizaje:
  - **Exploración 0,02**: es el mismo síntoma del striker, que con 0,02 quedó al azar y aprendió
    recién con 0,01. La entropía media de fase del keeper está en ~2,4–2,6.
  - **Pocos saques**: el saque es una fracción chica de lo que vive el keeper (~12 saques cada 4
    minutos), así que esa situación casi no pesa en cada actualización.
- **Propuestas** (no aplicadas, corrida2 sigue igual):
  1. Exploración del keeper 0,02 → 0,01. Es lo mismo que destrabó al striker, sin tocar la
     recompensa.
  2. **Pre-entrenar al keeper por imitación**: grabar (observación, acción) del script "volver y
     cubrir" o del keeper v2.3, entrenar la red un rato para que copie y después seguir con PPO.
     Parte de un keeper que ya vuelve al arco. Lleva ~30–45 min de trabajo y sirve como "idea
     creativa" para la metadata.

## Sesión 2026-10-18 (27) — Chequeo de las 17:45 (5,03 h, 29 fases)

- **Striker** (exploración 0,01): por fin se decide. Entropía media de fase 3,00 → 2,90 → 2,61 →
  **1,68** (ciclos 12–15) y 24 % de goles a favor en el ciclo 15.
- **Saque contra v2.3** (`sonda_saque.py`): nuestro striker toca primero en **17 de 22 saques**
  (antes 0–1 de ~20). Al segundo está a 132 px de la pelota (antes ~291). En el saque su red va
  67 % adelante, 99 % a la derecha y gira 100 % a la izquierda (una carrera en curva), con
  entropía 0,90. Goles de saque en contra: 6 (a las 16:35 eran 10).
- **El keeper sigue sin volver al arco**: a los 2 s del saque está en x≈398. La regla de
  estancamiento lo marcó otra vez (ciclo 14).
- **Partidos** (con la corrección del violeta; neto por par de partidos, G-E-P en 8):

| modelo | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| corrida2 ~16:45 | −7,8 (1-1-6) | **−5,8** | **−28,0** |
| corrida2 17:45 | **+1,0 (6-0-2)** | −33,5 | −42,8 |

- Lectura: el striker más agresivo hace más goles (contra NormalTeam gana 6 de 8), pero contra
  v1 y v2.3 recibimos mucho más (v1: de ~3 a ~21 goles por partido): gana el primer toque y deja
  el arco expuesto, con un keeper que no se mueve de su spawn. El intervalo es de ±9–11, pero el
  cambio contra v1 está bien afuera del ruido.
- **Mejor modelo contra los rule-based hasta ahora: el de ~16:45**. Corresponde al fin del ciclo
  12: `checkpoints/striker_20261018_163446_IT0180_s1474560_keeper.npz` + `keeper_` (mismo tag),
  guardados a las 16:46:44. La evaluación de las 16:45 usó el `striker.npz` vigente, que es ese
  mismo par o el guardado anterior.

## Sesión 2026-10-18 (26) — Chequeo de las 16:35 y bug de la observación del equipo violeta

### Chequeo de corrida2 (3,73 h, 22 fases; striker con 0,01 desde el ciclo 10)
- Entrenamiento: la entropía del striker bajó 3,14 → 3,05 → 2,91 y su % de goles a favor subió
  9 → 15 → 19 % (ciclos 9 → 11). Va en la dirección buscada, pero es temprano.
- Saque: el striker sigue sin correr (a ~291 px de la pelota al segundo). Su red en el saque elige
  adelante 25 %, atrás 37 % y gira a la derecha 82 %. La carrera al saque todavía no se aprendió.
- El entorno de entrenamiento hace el mismo saque que el partido (`_apply_reset`: todos a su
  spawn y pelota al centro), solo que sin la pausa de celebración. No es una diferencia de entorno.

### Bug: la observación del violeta no está bien espejada (`game/keras_core.py`, del curso)
- Los partidos mostraban una asimetría enorme: **de violeta (derecha) el DL recibía 3–4 veces más
  goles** que de azul, y el entrenamiento siempre es de azul.
- `build_observation` "da vuelta" la cancha para el violeta invirtiendo x, vx y sumando 180° al
  ángulo (una rotación de 180°), pero **no invierte y ni vy**. El juego es simétrico por esa
  rotación: los spawns violetas son los azules rotados.
- Verificado: en el saque, el striker azul ve y=0,6 y el violeta y=0,4 en la misma situación. Con
  y e vy invertidas, las dos observaciones coinciden (diferencia máxima 0,007, por sensores apenas
  asimétricos).
- **Corrección en `soccer_team_DVF_DL.py`** (`_obs`; `DVF_DL_FIX_Y=0` la desactiva para comparar).
  No toca el motor del curso ni el entrenamiento, que siempre juega de azul.
- Mismo modelo (corrida2 16:35), 4 semillas por lado, ruido 3:

| rival | neto sin corrección | neto con corrección | goles recibidos de violeta |
|---|---|---|---|
| NormalTeam | −20,5 | −7,8 | 18,2 → 7,0 |
| v1 | −19,8 | −5,8 | 17,8 → 2,8 |
| v2.3 | −52,0 | −28,0 | 33,0 → 11,0 |

  (Neto **por par de partidos**, uno de cada lado: la columna "neto/2 part." de `benchmark.py`.
  `evaluar_corrida.py` informa por partido, o sea la mitad.)
- Reevaluación con la corrección (neto por par de partidos; G-E-P en 8 partidos):

| modelo | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| noche1 05:59 (v1, ciclo 28) | +4,8 (5-1-2) | −30,5 | −42,5 |
| noche1 final (v2, solo NT) | +171,8 (8-0-0) | −27,5 | −57,5 |
| **corrida2 16:35 (v3, mezcla)** | −7,8 (1-1-6) | **−5,8** | **−28,0** |

  Con la medición corregida, corrida2 es claramente el mejor modelo contra nuestros rule-based:
  pierde por 5,8 con v1, cuando los de noche1 perdían por ~28–30. El striker v1 del ciclo 28 le
  gana a NormalTeam.

- **Todas las evaluaciones DL anteriores a esta sesión subestimaban al equipo**, porque la mitad
  de los partidos se jugaba de violeta con la observación rota.
- Pendiente para la entrega de la red: si la cátedra corre nuestra red con su
  `build_observation`, esta corrección no se aplica. Hay que confirmar el formato de entrega o
  entrenar también de violeta.

## Sesión 2026-10-18 (25) — corrida2 con el striker en exploración 0,01

- `scripts/lanzar_corrida2.ps1`: nuevo parámetro `-StrikerEntropy`, que ahora vale **0.01** por
  defecto. El keeper sigue en 0,02 porque con ese valor sí aprende (entropía de 2,85 a ~2,4).
- Corte 1 s después del guardado de las 15:31:33. Hasta ahí corrida2 sumaba 2,87 h en 17 fases.
  La fase del keeper que estaba a medias se repite.
- **Relanzada a las 15:31:43** (parte 3, supervisor PID 26872): 8 workers, prioridad baja,
  entropía del striker 0,01 y del keeper 0,02, hasta el lunes 07:00. Esta vez el lanzador corrió
  en segundo plano y terminó solo, sin dejar una tarea colgada.
- Para ver si funcionó: en las próximas fases del striker, la entropía tiene que bajar de ~3,1.
  Después, `sonda_recompensa.py`, parte 1: en el saque debería ir hacia adelante bastante más
  que el 38 % actual.

## Sesión 2026-10-18 (24) — ¿Por qué el striker no va a la pelota? Red, recompensa o exploración

Pregunta del equipo: ¿es un problema del equipo / código o de las ponderaciones de la recompensa?
Nueva sonda `scripts/sondas/sonda_recompensa.py` (corrida con prioridad baja, sin cortar corrida2).

- **El código del equipo DL no es:** `soccer_team_DVF_DL.py` usa la misma observación
  (`build_observation`) y elige igual que el entrenamiento: muestrea la política cada 4 frames.
- **Parte 1 · qué decide cada red en el saque** (striker en su spawn, pelota adelante-izquierda):

| red | entropía (máx. 3,30) | adelante | izquierda | quieto |
|---|---|---|---|---|
| noche1 05:59 (v1, ciclo 28, exploración 0,01) | 1,52 | **88 %** | **88 %** | 11 % |
| noche1 final (v2, solo NT) | 1,50 | 19 % | 10 % | 65 % (gira a la derecha 100 %) |
| corrida2 ahora (v3, exploración 0,02) | **3,13** | 38 % | 45 % | 36 % |

  La red de corrida2 está casi al azar (95 % de la entropía máxima). Desaprendió lo que el
  striker v1 ya sabía hacer en el saque.
- **Parte 2 · cuánto paga la recompensa v3 cada forma de jugar** (240 s contra v2.3 en el entorno
  de entrenamiento, 2 semillas):

| forma de jugar | densa total | carrera al saque | goles a favor / en contra |
|---|---|---|---|
| al azar | −2,5 | 0,04 | 0 / 3 |
| quieto | −2,9 | 0,14 | 0,5 / 5 |
| perseguir la pelota (script simple) | **+25,8** | **3,9** | 7 / 8 |
| striker rule-based v2.3 | +19,0 | 2,3 | 0,5 / 6 |

- **Conclusión:** los pesos de la recompensa **apuntan bien**. Perseguir la pelota paga ~28 puntos
  más que moverse al azar cada 4 minutos, y la carrera al saque paga ~100 veces más. Pero por paso
  esa diferencia es chica (~0,008) frente al ruido de los goles (+20 / −1), y con exploración 0,02
  (0,05 en la etapa A) el premio por seguir siendo impredecible le gana a esa señal: la red vuelve
  al azar. Con 0,01 (etapa B) sí aprendió.
- Propuestas, en orden: (1) exploración del striker a 0,01; (2) si no alcanza, subir los pesos
  densos del striker (por ejemplo `W_APP_DELTA` 0,02 → 0,2) para que la señal sobresalga del ruido
  de los goles; (3) para la entrega, probar jugar con la acción más probable en lugar de muestrear.

## Sesión 2026-10-18 (23) — Chequeo de corrida2 a las 15:10 (2,36 h, 14 fases)

**Partidos** (`evaluar_corrida.py corrida2 --strikers final --keepers final`, 4 semillas por
lado, ruido 3, 3 procesos con el entrenamiento corriendo). Neto por partido:

| modelo | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| noche1 final (v2, striker solo NT) | +84,8 | −18,9 | −31,9 |
| corrida2 15:10 (v3, mezcla) | −7,5 | **−12,2** | **−17,0** |

- **Mejora en defensa:** goles de saque recibidos contra v2.3: 23,9 → 7,9 por par de partidos.
  La sonda de saques (300 s) no da ningún gol en contra en menos de 3 s contra v2.3 (antes: 8)
  ni contra v1.
- **Empeoramiento en ataque:** hace 0–1,5 goles por partido y perdió el truco contra NormalTeam.
  El striker **no corre al saque**: al segundo sigue a ~280 px de la pelota (arranca a ~293).
  La recompensa de carrera todavía no le hizo efecto.
- **Estancamiento del striker:** entropía ~3,14 en las 7 fases, igual que en la etapa A con 0,05.
  Con 0,02 vuelve a explorar demasiado. En la etapa B aprendió recién con 0,01.
- El keeper sí aprende con 0,02: la entropía bajó de 2,85 a ~2,4.
- Nuevo: la pelota queda quieta en esquinas el 17,8 % del tiempo, 15,4 % de nuestro lado
  (noche1 final: ~9 %).
- **Ojo al comparar:** desde las 13:06 corre con 8 workers, así que cada actualización junta
  8×256 pasos en vez de 14×256. Los goles por actualización bajaron por eso, no porque el equipo
  haya cambiado. `analizar_fases.py` y la regla de estancamiento comparan por actualización;
  entre partes con distinta cantidad de workers solo vale el % de goles a favor.

## Sesión 2026-10-18 (22) — Apagado brusco de la PC; lanzador más liviano

- **La PC se apagó de golpe ~12:55** con `corrida2` corriendo (14 workers) y el equipo usando
  otras apps. Visor de eventos: Kernel-Power 41 + EventLog 6008 (apagado inesperado, sin
  pantallazo azul). Ya había pasado el **16/10 14:05 y el 17/10 03:35**, antes del entrenamiento
  largo. Ese patrón (corte sin bugcheck) apunta a temperatura o alimentación más que a RAM: la
  falta de RAM cierra programas, no apaga la PC.
- **Reloj desfasado**: después del corte Windows quedó **12,95 h atrás** (marcaba 00:06 con la
  hora real ~12:58, medido con `w32tm /stripchart` contra time.windows.com). Si Windows corrige
  la hora a mitad de una fase, `run.json` anota una fase de 13 h y la metadata sale mal.
- Estado de `corrida2`: 3 fases completas (0,48 h). Pesos guardados 12:53:36, a mitad de la fase
  del keeper del ciclo 2, que se repite al relanzar.
- **`scripts/lanzar_corrida2.ps1`**:
  - `-Workers` (default **8** de 16 núcleos) y prioridad **BelowNormal**, que heredan los workers,
    para que la PC siga usable y caliente menos.
  - No lanza si el reloj está desfasado más de 5 min respecto de internet (probado: frenó con el
    desfase de 12,95 h sin lanzar nada).
  - Ahora está guardado en UTF-8 con BOM para que PowerShell 5.1 muestre bien los acentos.
- **Relanzada a las 13:06**, con el reloj ya sincronizado, `-Workers 8` (parte 2, supervisor PID
  12440). Los 11 procesos quedaron en BelowNormal. Rinde ~2.245 pasos/s, casi lo mismo que con
  14 workers. La CPU total sigue en ~77 % (el paso de entrenamiento de TensorFlow usa varios
  núcleos), pero con prioridad baja las otras apps pasan primero.
- Nota: la herramienta que lanzó el `.ps1` quedó esperando porque el supervisor heredó la
  salida. No es un problema: conviene lanzarlo en segundo plano o desde una terminal propia.

## Sesión 2026-10-18 (21) — Corrida 2 lanzada + análisis de todo el entrenamiento

- **`corrida2` lanzada a las 12:18** con `scripts/lanzar_corrida2.ps1` (supervisor PID 13836,
  hasta el lunes 07:00). Primeras iteraciones OK: 14 workers, rivales mezclados, entropía 0,02.
- **`scripts/analizar_fases.py`** (nuevo): lee los `training.log`, arma una fila por fase y las
  agrupa en etapas comparables (misma recompensa y rivales). Escribe
  `models/runs/_analisis/fases.md` y `fases.png` (% de goles a favor y entropía por fase).
- Resumen por etapa (goles por actualización; % = goles a favor sobre el total):

| etapa | striker | keeper |
|---|---|---|
| A · v1, mezcla, ent 0,05 | 0,8 a favor / 7,2 en contra (10 %), entropía 3,26 → 3,25 | 10 %, en contra 11,6 → ~6 |
| B · v1, striker solo NT, ent 0,01 | 31 % (+12 pts), entropía 3,16 → 1,90 | 15 %, en contra ~4,5 → ~8,8, entropía ~3,0 |
| C · v2, striker solo NT | 88 % (+31 pts) | 50 %, en contra 9,1 (peor que en B) |
| D · v3, mezcla, ent 0,02 (1 fase) | 34 % contra la mezcla (A: 10 %) | — |

- Partidos reales (la vara que importa): v1 → todas las combinaciones pierden −3 a −9 contra
  NormalTeam; v2 final → +84 contra NormalTeam, −18 contra v1 y −32 contra v2.3.

## Sesión 2026-10-18 (20) — Corrida 2 preparada: rivales mezclados y defensa del saque (sin lanzar)

### Diagnóstico del saque (`scripts/sondas/sonda_saque.py`, modelo final de noche1 como azul, 300 s)
| rival | saques | gol <3 s a favor / en contra | primer toque del rival | keeper x a 0,5 / 1 / 2 s |
|---|---|---|---|---|
| v2.3 | 19 | 0 / 8 | 18 de 19 | 416 / 415 / 404 |
| v1 | 30 | 4 / 3 | 30 de 30 | 416 / 410 / 392 |
| NormalTeam | 53 | 49 / 0 | 53 de 53 | 416 / 413 / 384 |

- El striker DL sigue a ~190 px de la pelota al segundo, cuando arrancó a ~290: casi no corre.
- El keeper se queda en su spawn (x≈418) durante el saque; la línea de gol está en 127.
- Contra NormalTeam ganamos igual porque, después del primer toque de ellos, nuestro striker
  saca un tiro que su arquero no ataja. v1 y v2.3 no dejan esa pelota.

### Recompensa v3 (`dvf_rewards.py`, `REWARD_VERSION = "v3"`)
- **Estado de saque**: pelota a menos de 40 px del punto central y a menos de 40 px/s
  (`_en_saque`). Se evalúa con la pelota al principio del paso.
- **Striker, carrera al saque** (`W_KICKOFF_RACE = 1.5`): potencial de acercarse a la pelota
  mientras dura el saque, acotado a ~+0,26 por saque (unas 20 veces el `W_APP_DELTA` general).
- **Keeper**: castigo por estar lejos del arco más temprano y más fuerte (`W_KEEPER_AWAY` 0,004 →
  0,006, libre hasta x≈251 en vez de 341, máximo en x≈451 en vez de 641) y **x3 durante el
  saque** (`KICKOFF_AWAY_MULT`). Parado en el spawn: −0,016 por paso en el saque (v2: −0,001).
- Casos sintéticos OK; prueba chica de `train_dl.py` (3 workers, rivales mezclados, v3 en
  `run.json`) OK y borrada.

### Corrida 2 (lista, NO lanzada)
`scripts/lanzar_corrida2.ps1`: supervisor oculto, `--run corrida2 --init-from models/runs/noche1`,
striker y keeper contra NormalTeam + v1 + v2.3, entropía 0,02 para los dos (el striker final
quedó en ~1,6 y tiene que volver a explorar), hasta el lunes 07:00. No lanza si ya hay un
`train_dl.py` corriendo. Sintaxis verificada sin ejecutarlo.

## Sesión 2026-10-18 (19) — Evaluación anticipada: combinar striker y keeper de ciclos distintos

Estado de `noche1` a las 05:39 (8,6 h, ciclo 28, sin caídas desde las 23:34): el striker por fin
converge (entropía 3,25 → 2,26 en los ciclos 26–27, goles a favor ~0,5 → ~1,8 por actualización),
pero el keeper empeoró desde el ciclo 11 (goles en contra ~4,5 → ~8,8; la regla de estancamiento
lo marcó varias veces). Conclusión: el mejor par probablemente mezcla ciclos.

- **`scripts/evaluar_corrida.py`**: opciones `--strikers` y `--keepers` (números de ciclo o
  `final`) que evalúan todas las combinaciones (`S<c>_K<c>`). El checkpoint de un ciclo es el
  último de su fase de keeper (ahí los dos ya entrenaron). Las etiquetas de los checkpoints se
  aparean con el `start` de `run.json` con 10 s de tolerancia (la etiqueta se toma ~1 s después:
  sin tolerancia el primer intento mezclaba fases de ciclos vecinos, visto en el `--dry-run`).
  Las combinaciones escriben `eval/resumen_combos.md` (no pisan `resumen.md`).
- Corriendo con el entrenamiento activo, liviano (3 procesos, solo NormalTeam, 4 semillas por
  lado, ruido 3): strikers 14 19 26 27 × keepers 10 11 17 23. Salida en
  `models/runs/_salidas/eval_combos_noche1.txt`.

### Resultado de la evaluación (05:59, `eval/resumen_combos.md`)
Las 16 combinaciones (strikers 14/19/26/27 × keepers 10/11/17/23) **pierden contra NormalTeam**:
neto entre −2,8 y −8,8 por partido, sin una ganadora clara (las diferencias entran en el ruido).
Los números del entrenamiento (goles por actualización) no predicen bien el partido real.

### Diagnóstico de la recompensa (sonda `scripts/sondas/sonda_keeper.py`, DL vs NormalTeam, 180 s)
- Keeper del ciclo 11: mediana x≈380, 40 % del tiempo con x>400 (la línea de gol está en 127).
  Keeper del ciclo 27: mediana x≈347, 22 %. **A los 2 s del saque ambos siguen en x≈400**, al
  lado del spawn (418): no vuelven al arco.
- Causa en `dvf_rewards.py` (v1): **no hay ningún castigo por gol recibido**. Además, volver
  del spawn al punto ideal pagaba apenas +0,11 (W_KEEPER_LINE 0,8), mientras que cada
  "atajada" pagaba +1/+1,5 **en cualquier lugar de la cancha**. El keeper aprendió a jugar de
  mediocampista: más recompensa con más goles en contra (lo que se vio en la curva).

### Recompensa v2 (`dvf_rewards.py`, `REWARD_VERSION = "v2"`)
1. Gol recibido: keeper −5, striker −1 (`KEEPER_CONCEDE`, `STRIKER_CONCEDE`).
2. Atajadas solo con la pelota en nuestro tercio (`SAVE_ZONE_X = 500`).
3. `W_KEEPER_LINE` 0,8 → 2,0 (volver al arco ahora paga ~0,28).
4. Castigo por paso con el keeper lejos del arco (`W_KEEPER_AWAY = 0,004`, libre hasta x≈341,
   máximo desde x≈641).
- Casos sintéticos: concede −5/−1, gol +20, atajada en el medio no paga (−0,005) y en zona
  propia paga +1,5, castigo por distancia 0 → −0,004 según x.
- `train_dl.py`: anota la versión en `run.json` (config y cada fase) y la regla de
  estancamiento solo compara fases con la misma versión.

### Relanzamiento de `noche1` (06:01)
- Corte 1,4 s después del guardado de las 05:59:30 (fin de la fase del keeper del ciclo 28; esa
  fase no llegó a anotarse en `run.json`, así que se repite con la recompensa nueva).
- Respaldo de modelos, `run.json`, `dvf_rewards.py` y `train_dl.py` en
  `models/runs/noche1/respaldo_0600/`.
- Se sigue con los modelos actuales. El striker del ciclo 28 es el mejor de la noche en
  entrenamiento (5,5 goles a favor por actualización, entropía 1,9) y todavía no se probó en
  partidos. No se cambió el keeper de arranque porque la sonda y la evaluación no coincidían.
- Prueba chica (`--run prueba_v2`, 2 workers) antes de relanzar: OK; se borró.
- Supervisor nuevo PID 25736 (parte 3), mismos argumentos más `--keeper-entropy 0.02`: la
  entropía del keeper nunca bajó de ~3,0 con 0,05 y el striker recién convergió con 0,01.
  Hasta las 10:30 (`until.txt`).

### Corte final de `noche1` (09:56, pedido del equipo: "suficiente entrenamiento por ahora")
- Corte 1 s después del guardado de las 09:56:15 (a mitad de la fase del striker del ciclo 41;
  esa fase no figura en `run.json`). Total: **12,57 h**, 80 fases. No queda ningún proceso.
- Con v2 (ciclos 28–40): el **striker** pasó de ~5 a **~35 goles a favor por actualización**
  contra NormalTeam, con ~2–2,5 en contra; entropía ~2,4–2,7. El **keeper** no mejoró: ~7–11
  goles en contra por actualización, entropía ~2,8–3,0.
- **⚠ Sospechoso:** la última línea del log da 3190 goles a favor contra 93 en contra en 60
  iteraciones de la fase del striker. Es demasiado bueno: puede ser una jugada real repetible
  (por ejemplo, gol directo desde el saque) o un exploit del entorno de entrenamiento. **Antes
  de usarlo hay que verificarlo en partidos reales** con `evaluar_corrida.py` / benchmark.

### Verificación del modelo final (benchmark, 4 semillas por lado, ruido 3 y 0)
`evaluar_corrida.py noche1 --strikers 27 final --keepers final` (neto por partido):

| punto | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| striker c27 (v1) + keeper final | −2,4 / −4,2 | −16,6 / −15,1 | −31,8 / −37,1 |
| striker final (v2) + keeper final | **+84,8 / +84,2** | −18,9 / −18,1 | −31,9 / −32,2 |

- Los goles son **reales pero solo contra NormalTeam**. En los 8 partidos, todos nuestros goles
  (57 a 112 por partido) entran a los ~2,1 s del saque: un tiro directo desde el saque que el
  arquero de NormalTeam no ataja. Contra v1 y v2.3 no funciona: ganan ellos el saque (v2.3 hace
  23,9 goles de saque por par de partidos).
- Es **sobreajuste al rival**: desde el ajuste de la sesión 17 el striker entrena solo contra
  NormalTeam. El keeper sigue siendo el punto débil.
- Para la próxima corrida: striker contra los tres rivales (o al menos con v1 y v2.3) y trabajar
  el saque defensivo.
- Nota: esta corrida pisó el `eval/resumen_combos.md` de las 16 combinaciones; esos números
  quedan en la tabla de arriba (sesión 19) y en los JSONL `eval/S*_K*_j3.jsonl`.

## Sesión 2026-10-17 (18) — Herramientas para el domingo y el lunes: evaluación y metadata

Sin tocar nada de lo que usa el entrenamiento (train_dl, dvf_rewards, equipos): `noche1` sigue.

- **`scripts/evaluar_corrida.py <run>`** (nuevo): junta los pasos 3 y 4 de "Domingo a la mañana".
  Toma el último checkpoint de cada fase (pares `striker_`/`keeper_` con la misma etiqueta),
  elige `--puntos` repartidos parejo (default 5) más el modelo final, y para cada uno corre
  `benchmark.py soccer_team_DVF_DL` con `DVF_DL_STRIKER`/`DVF_DL_KEEPER` contra NormalTeam, v1
  y v2.3, ambos lados, ruido 3 y 0. Guarda JSONL y salida en `models/runs/<run>/eval/` y la
  tabla de neto por partido (± ~95 %) en `eval/resumen.md`. `--dry-run` solo lista los puntos.
- **`scripts/metadata_entrega.py <run> [<run>...]`** (nuevo): arma la planilla de metadata
  desde `run.json` (horas sumadas, núcleos, épocas) y el `.npz` (capas = ocultas + salida = 3;
  neuronas = suma de sesgos = 256+128+3+3+3+1 = 394, coincide con la convención de la planilla).
  Escribe `entrega/metadata_DVF.md` y `.csv` (utf-8 con BOM para que Excel lo abra bien).
  Las ideas creativas están en la constante `IDEAS` del script.
- Probado: metadata de `noche1` en el scratchpad (2.6 h, 16 núcleos, 4 épocas, 3 capas, 394
  neuronas); evaluación chica (2 puntos, 1 semilla, 20 s, 2 procesos) sin fallas; se borró la
  carpeta `eval/` de la prueba para que el domingo arranque limpia.
- `PLAN_ENTREGA.md`: atajo agregado en el paso 4 de "Domingo a la mañana".

## Sesión 2026-10-17 (17) — Striker estancado: rivales y exploración por rol + regla automática

**Archivos:** `scripts/train_dl.py`.

### Diagnóstico (fases 1–5 de `noche1`, ~2 h)
| Rol | Entropía media por fase | Métrica |
|---|---|---|
| Striker | 3.258 → 3.236 (casi nada; el máximo es 3.30) | goles a favor por actualización 0.67 → 0.60–1.07, plano |
| Keeper | 3.211 → 3.040 | goles en contra por actualización 11.6 → 5.9; recompensa −0.1 → +4.0 |

Hipótesis:
- Contra v2.3 y v1 (buenos arqueros) el striker casi nunca convierte, así que recibe poca señal.
- Con exploración 0.05 esa señal no alcanza para que la política se decida. El keeper sí se
  decide porque su recompensa de posicionamiento da señal en cada paso.

### Cambios
- **Configuración por rol:** `--striker-opponents`, `--keeper-opponents`, `--striker-entropy`
  y `--keeper-entropy`. La entropía se fija en el entrenador del curso (`entropy_coef`) al
  empezar cada fase. Cada fase registra en `run.json` sus rivales, su coeficiente y sus
  estadísticas (`stats`: entropía media, goles a favor y en contra por actualización).
- **Regla automática de estancamiento** (`_check_plateau`):
  - Compara las últimas 3 fases del rol con la misma configuración.
  - Si la entropía bajó menos de 0.01 y la métrica no mejoró (striker: +0.10 goles a favor
    por actualización; keeper: −0.30 goles en contra), escribe `!!! ESTANCAMIENTO` en el log y
    lo agrega a `run.json` → `plateaus`. Solo avisa; no cambia el entrenamiento.
- Corregido un choque de nombres (`extra`) y las estadísticas pasan a `float` (`float32` de
  numpy no se puede guardar en JSON; lo detectó la prueba).

### Pruebas
- **Corrida chica:** la fase del striker jugó solo contra NormalTeam con 0.01, la del keeper
  contra los tres rivales con 0.05, y las `stats` quedaron en `run.json`.
- **Regla, 5 casos sintéticos:**
  - Striker estancado → avisa.
  - Striker que mejora goles → no avisa.
  - Striker con entropía que baja → no avisa.
  - Configuración distinta → no compara.
  - Keeper estancado → avisa.

### Relanzamiento de `noche1` (23:33)
Se cortó 1 s después del guardado de las 23:33:45. Se detuvieron el encadenador, el supervisor
y el entrenamiento, y se lanzó un supervisor nuevo:
```
--run noche1 --until 2026-10-18T10:30 --phase-steps 1500000 --striker-opponents NormalTeam --striker-entropy 0.01
```
Siguió en el ciclo 8 keeper. Desde el ciclo 9, las fases del striker son contra NormalTeam con
0.01. Ya no hace falta el encadenador, porque este supervisor llega solo a las 10:30. Salida en
`models/runs/_salidas/noche1_parte2_*.txt`.

---

## Sesión 2026-10-17 (16) — Workers que mueren: se reemplazan en caliente

**Archivos:** `scripts/train_dl.py`.

### Diagnóstico (visor de eventos de Windows, "Application Error" de python.exe)
| Hora | Módulo | Código | Qué era |
|---|---|---|---|
| 20:22:12 | python310.dll | 0xc0000005 | Un worker del **primer** lanzamiento (el que se "congeló") |
| 20:52:02 | desconocido | 0xc0000005 | El proceso principal (sesión 14) |
| 21:12:53 | python310.dll | 0xc0000005 | Un worker; watchdog a las 21:14:54 |
| 21:34:09 | python310.dll | 0xc0000005 | Un worker; watchdog a las 21:36:13 |

- **Hay crashes nativos intermitentes**, más o menos uno cada 20 min entre 15 procesos. La causa
  de fondo (C de Python/pymunk/TensorFlow) no se pudo aislar.
- **Corrección de la sesión 10:** el congelamiento de las 20:22 **no** fue la consola
  bloqueada por la salida, sino este mismo crash de un worker (el bucle del curso esperaba sin
  timeout). Redirigir la salida sigue siendo una buena práctica, pero la causa real era esta.
- **El watchdog actuaba pero era caro:** esperaba 120 s y reiniciaba la fase desde el último
  guardado. Además, el tope de 5 reintentos contaba toda la historia de `run.json`, así que tras
  5 caídas en la noche cualquier falla cortaba todo.

### Cambios
- **Reemplazo en caliente:**
  - Cada 5 s sin resultados se revisa si murió algún worker. Si murió, se crea otro con el
    mismo rival y los pesos de esta iteración, y la iteración sigue (~15 s de arranque).
  - Se registra en `training.log` (`!!! worker N (rival) murió (código ...); reemplazado`).
  - `WorkersPerdidos` (reiniciar la fase) queda solo para cuando nadie murió y no llega nada
    en 120 s.
- **El tope de 5 reintentos cuenta solo los del lanzamiento actual.**

### Prueba
Corrida chica de 3 workers (borrada). Se mató un worker a mitad de la fase: se reemplazó
(`worker 0 (NormalTeam) murió ... reemplazado`) y la fase siguió **sin reiniciarse**; el
ciclo terminó completo.

### Aplicación a `noche1` (22:28, pedido del equipo)
Se cortó `train_dl.py` 3 s después del guardado de la iteración 60 (`.npz` de las 22:28:14),
así que no se perdió entrenamiento. El supervisor eliminó los 14 workers huérfanos y relanzó a
las 22:28:33 con el código nuevo. Siguió correctamente en **ciclo 5 keeper**, porque la última
fase completa era el ciclo 5 striker. El corte costó ~40 s.

---

## Sesión 2026-10-17 (15) — `noche1` extendida hasta las 10:30 sin cortarla

**Archivos:** `scripts/train_dl.py` y `scripts/supervisar_entrenamiento.py` (modificados),
`scripts/encadenar_corrida.py` (nuevo), `models/runs/noche1/until.txt` (nuevo).

Pedido: que el entrenamiento termine el domingo ~10:30 en vez de 07:15, sin interrumpirlo.
El proceso que corre ya tiene su hora límite cargada en memoria, así que:

1. **`scripts/encadenar_corrida.py`:**
   - Espera a que termine el supervisor actual (PID 12736, ~07:15–07:25) y lanza uno nuevo
     con `--until 2026-10-18T10:30`.
   - Verifica el PID por línea de comando, por si Windows lo reusara.
   - Escribe en `supervisor.log`.
   - Lanzado a las 21:24 (PID en `models/runs/_salidas/noche1_encadenador_pid.txt`).
2. **Alternancia continua al relanzar** (`train_dl.py`): la próxima fase sale de la última
   fase completa de `run.json`. Antes, cada lanzamiento arrancaba por el striker, y después de
   una fase de striker venía otra de striker.
3. **`until.txt`:** si existe `models/runs/<run>/until.txt`, manda sobre `--until`.
   `train_dl.py` lo relee antes de cada fase y el supervisor antes de cada intento. Sirve para
   mover la hora de fin en caliente en futuros lanzamientos. Para noche1 dice `2026-10-18T10:30`,
   así que si hay un crash antes de las 07:15, el relanzamiento ya usa la hora nueva.

**Pruebas** (corridas chicas de 2 workers, borradas):
- Ciclo normal: correcto.
- Relanzado después de una fase de striker: sigue con keeper en el mismo ciclo.
- `until.txt` en el pasado: no arranca.
- Encadenamiento de punta a punta: la parte 1 terminó a su hora y la parte 2 arrancó sola,
  siguiendo con ciclo 2 striker → keeper.

**Horas esperadas de `noche1`:** 20:24–20:52 y 21:11–10:30, unas 13.8 h de entrenamiento
(~130M pasos), menos unos 20 s en el encadenamiento.

---

## Sesión 2026-10-17 (14) — `noche1` se cayó a las 20:52: crash nativo; supervisor y guardado atómico

**Archivos:** `scripts/train_dl.py` (modificado), `scripts/supervisar_entrenamiento.py` (nuevo).

### Qué pasó
- El log de `noche1` se cortó a las **20:52:02** (ciclo 2, fase striker, iteración 100, justo
  después de un guardado).
- El **visor de eventos de Windows** registra a esa hora: *Application Error, python.exe,
  exception code 0xc0000005* (access violation en un módulo nativo). Es un crash de
  TensorFlow/C, no de Python, y por eso no hay traza en stderr.
- **Murió el proceso principal**; 11 de los 14 workers quedaron huérfanos esperando órdenes
  y se eliminaron a mano.
- Los `.npz` del guardado de las 20:52:02 quedaron sanos (se verificó que cargan).
- La causa exacta del crash nativo no se pudo determinar. RAM: 15.2 GB en total.

### Cambios
1. **Watchdog de workers** (lo agregó la sesión lateral "btw: en qué fase del proceso de ML
   estamos…", 20:59):
   - `result_q.get(timeout=120)`. Si los workers dejan de responder, se lanza
     `WorkersPerdidos` y la fase se repite desde el último guardado (hasta 5 veces).
   - Los workers que quedan vivos se terminan al salir. Ella lo probó con `prueba_wd`
     (borrada).
2. **Guardado atómico** (`_safe_save`): cada `.npz` se escribe a un temporal y se renombra con
   `os.replace`. Un crash a mitad del guardado ya no puede dejar un modelo roto.
3. **`--until <ISO>`**: hora límite absoluta, así un reinicio no corre el final de la corrida.
4. **Supervisor** `scripts/supervisar_entrenamiento.py`:
   - Relanza `train_dl.py` si se cae; la corrida sigue desde el último guardado y `run.json`
     acumula las fases.
   - Antes de relanzar elimina los workers huérfanos del intento caído.
   - Registra todo en `models/runs/<run>/supervisor.log`.

### Pruebas
Corridas cortas de 4 workers, borradas después. En cada una se mató el proceso de
entrenamiento a mano a mitad de una fase.
- **Primera:** el supervisor relanzó en 15 s y la corrida siguió hasta `--until`, donde terminó
  con código 0. Pero eliminó 0 huérfanos: el filtro miraba la ruta del ejecutable, y los workers
  corren con el intérprete base, no el del venv.
- **Segunda, con el filtro corregido** (busca la ruta del proyecto en la línea de comando):
  eliminó los 4 huérfanos y relanzó.

### `noche1` relanzada (21:11) bajo el supervisor
```
Start-Process .\env\Scripts\python.exe -ArgumentList 'scripts\supervisar_entrenamiento.py','--run','noche1','--until','2026-10-18T07:15','--phase-steps','1500000' -RedirectStandardOutput models\runs\_salidas\noche1_stdout.txt -RedirectStandardError models\runs\_salidas\noche1_stderr.txt -WindowStyle Hidden
```
Continúa en el ciclo 2 (striker) desde el guardado de las 20:52. Se perdieron ~20 min. PID del
supervisor en `models/runs/_salidas/noche1_supervisor_pid.txt`.

---

## Sesión 2026-10-17 (13) — Archivo de entrega del rule-based: `entrega/soccer_team_DVF.py`

**Archivos nuevos:** `entrega/soccer_team_DVF.py`. Es el que se sube; nombre decidido por el
equipo según la Anleitung, `soccer_team_<teamname>.py`.

### Chequeo de reglas (HowTo_RuleBased_Code_Run_And_Submit.MD)
| Regla | Estado |
|---|---|
| Nombre `soccer_team_<teamname>.py` | ✅ `soccer_team_DVF.py` |
| Integrantes en la cabecera | ✅ Diego, Valentino, Fernando (solo nombres; ¿agregar apellidos?) |
| Lógica en `default()`, solo sensores + move/turn | ✅ Nunca escribe la física. ⚠️ **Lee** `body.position/velocity/angle` en 14 lugares (duda abierta con los asistentes) |
| Apariencia propia en `get_team_appearance()` | ✅ Coral (1.00, 0.35, 0.55), "DVF". Antes era dorado, casi igual que NormalTeam |
| Autocontenido | ✅ Solo `math` y `game.player` |
| `striker = Striker()` / `keeper = Keeper()` al final | ✅ |

### Cambios respecto de `soccer_team_DVF_v2.py` (v2.3)
- **Cabecera nueva en inglés:** equipo, comportamiento e historial 2.0–2.3, sin referencias a
  archivos del repo que los correctores no tienen.
- **Apariencia:** color y rótulo nuevos.
- **Lógica:** sin cambios. Verificado con 16 partidos con las mismas semillas: **16/16
  marcadores idénticos** a v2.3.

`soccer_team_DVF.py` (v1) en la raíz sigue igual: el entrenamiento lo importa como rival. Al
subir, usar el archivo de `entrega/`.

---

## Sesión 2026-10-17 (12) — Cambio de fecha: rule-based y metadata vencen el lunes 10:00

**Archivos:** `PLAN_ENTREGA.md`.

- La plataforma muestra "Rule-Based: Python source code (soccer_team.py) — Fällig: Montag,
  19. Oktober 2026, 10:00". Según entendemos, la metadata también vence ese día y hora.
- Plan reorganizado:
  - El entrenamiento se cierra el **lunes ~07:00**: `noche1` + una segunda corrida desde el
    domingo a la mañana, ~33 h en total.
  - El rule-based se sube el **domingo** si el chequeo de reglas da bien.
  - La metadata se completa el lunes entre 07:00 y 09:30.
- El archivo a subir se arma en `entrega/`. No se renombra nada mientras se entrena, porque
  `scripts/train_dl.py` importa `soccer_team_DVF` y `soccer_team_DVF_v2` como rivales.

---

## Sesión 2026-10-17 (11) — Herramientas para evaluar la red (listas para el domingo)

**Archivos nuevos:** `soccer_team_DVF_DL.py`, `scripts/plot_training.py`.
**Modificado:** `scripts/benchmark.py`.

- `soccer_team_DVF_DL.py`: nuestro equipo DL, basado en la plantilla `soccer_team_DeepLearning.py`
  del curso.
  - Por defecto carga `models/DVF_striker.npz` y `models/DVF_keeper.npz`, los que se van a
    entregar.
  - Con `DVF_DL_RUN=<run>` carga una corrida de `scripts/train_dl.py`.
  - Con `DVF_DL_STRIKER` + `DVF_DL_KEEPER` carga un checkpoint puntual.
  - Apariencia propia: naranja, "DVF".
- `scripts/plot_training.py <run>`: la misma figura que la celda "Training Curves" del notebook
  (recompensa, goles, pérdidas y entropía), con bandas por fase striker/keeper →
  `models/runs/<run>/training_curve.png`.
- `scripts/benchmark.py`: también fija la semilla de numpy por partido. Los equipos DL
  muestrean acciones con numpy y sin esto las corridas no eran reproducibles.
- **Probado** con el estado parcial de `noche1` a los ~10 min:
  - La curva se genera bien.
  - El equipo DL juega en el benchmark (−5.0 vs NormalTeam en 2 partidos de 60 s). A esa
    altura la red es casi aleatoria (entropía 3.23 de un máximo de 3.30).
- Disco: un checkpoint cada ~100 s, ~370 MB en la noche, con 105 GB libres.
- Pasos y criterios para decidir la segunda noche: `PLAN_ENTREGA.md`, sección "Domingo a la
  mañana".

---

## Sesión 2026-10-17 (10) — Script de entrenamiento DL + corrida nocturna `noche1`

**Archivos nuevos:** `scripts/train_dl.py`. El rule-based queda en **v2.3** (decisión del
equipo).

### Qué hace `scripts/train_dl.py`
Usa la infraestructura del curso (`setup_dl_notebook.py`, sin modificarla) y agrega:
- **Recompensa DVF** (`dvf_rewards.compute_reward`, sesión 8).
- **Entrenamiento alternado** striker/keeper, como pide la cátedra. Cada fase actualiza solo
  un rol y el otro juega congelado. Se verifica con una huella (hash) de los pesos de cada rol
  que queda en el log al final de cada fase.
- **Rivales mezclados** entre los workers (por defecto NormalTeam, DVF = v1, DVF_v2 = v2.3).
- **Ruido en el saque** (±5 px) y **reinicio por pelota quieta en cualquier lugar** (como la
  ventana), además del reinicio por esquina del curso.
- **Bucle paralelo propio** (`_run_parallel_dvf`): copia del bucle del curso con dos cambios:
  1. Solo actualiza el rol que entrena.
  2. Registra pl/vl/ent de ese rol; el original siempre mostraba los del striker, y en una
     fase de keeper quedaba `ent=0.000`.

  Marca la fase en `opp=fase-<rol>`, así la celda de curvas del notebook pinta una banda por
  fase.
- **Una carpeta por corrida:** `models/runs/<run>/` con `striker.npz`, `keeper.npz`,
  `checkpoints/`, `training.log` y `run.json` (configuración, fases, horas y huellas, para la
  planilla de metadata).

### Prueba rápida (2 fases de 50k pasos, 14 workers)
- Corre de punta a punta y guarda los modelos.
- Durante la fase del keeper la huella del striker no cambia (`d215ef342f` → `d215ef342f`)
  y la del keeper sí.
- Velocidad en régimen: **~2 900 pasos/s** (≈ 10M pasos/hora), más ~15 s de arranque de los
  workers por fase.

### Corrida nocturna `noche1` (relanzada 2026-10-17 20:24)
- Fases de 1.5M pasos (~9 min), alternando striker → keeper, primero el striker.
- Rivales NormalTeam/v1/v2.3, desde pesos aleatorios.
- Sin fases nuevas después de 11 h. Se esperan ~70 fases y ~100M pasos.

**Incidente y arreglo.** El primer lanzamiento (20:21) en una pestaña de terminal de la app
**se congeló a los 20 s**. Cada gol de los 14 workers imprime una línea y, en una pestaña que
nadie lee, la escritura a la consola se bloquea y frena todo el bucle. Se cortó, se borró
(tenía 2 iteraciones) y se relanzó como proceso oculto, con la salida redirigida a archivos:

```
Start-Process .\env\Scripts\python.exe -ArgumentList 'scripts\train_dl.py','--run','noche1','--hours','11','--phase-steps','1500000' -RedirectStandardOutput models\runs\_salidas\noche1_stdout.txt -RedirectStandardError models\runs\_salidas\noche1_stderr.txt -WindowStyle Hidden
```

- PID en `models/runs/_salidas/noche1_pid.txt`.
- Progreso en `models/runs/noche1/training.log` (~2 300 pasos/s y subiendo a los 2 min).
- Para cortarlo antes de tiempo: matar los procesos `python` del proyecto. Los modelos quedan
  guardados del último checkpoint (cada 20 iteraciones, ~2 min) o del final de la fase.

---

## Sesión 2026-10-17 (9) — Esquinas: medidas, diagnosticadas y NO resueltas en el rule-based

**Archivos:** `scripts/benchmark.py` (métrica de esquinas), `experimentos/soccer_team_DVF_v24_banda.py`
(nuevo; experimento, no se entrega), `soccer_team_DVF_v2.py` (sigue en v2.3; solo una nota
en el docstring). También se creó la guía para el equipo (Claude Doc "Guía del equipo DVF").

### Medición
El benchmark ahora informa el % de tiempo con la pelota **lenta (< 60 px/s) en una esquina**
(a menos de 150 px de una banda y de una línea de fondo):

- v2.3 vs v1 y NormalTeam: **~33 % con ruido, ~36 % sin ruido**.
- Casi todo (25–31 %) está del lado rival, en la esquina **delantera-derecha del atacante**:
  abajo a la derecha cuando jugamos de izquierda, arriba a la izquierda cuando jugamos de
  derecha. Es lo que se ve en la ventana.

### Diagnóstico (rastreo cuadro a cuadro)
- **Causa 1:** con la pelota contra la banda, el delantero entra en la rama de "órbita" (arco
  rival a un costado, pelota a < 90 px). Ahí solo se mueve de costado, sin avanzar, y ese paso
  lateral iba **contra la pared**.
- **Causa 2 (la que pesa):** muchas pelotas quedan **encajadas** entre la banda, el chaflán de
  la esquina y el arquero rival. No hay dirección en la que se pueda empujar; las destraba el
  reinicio del motor por pelota trabada.

### Experimento v2.4 "jugada de banda" (no adoptado)
- **Qué hace:** con la pelota pegada a una banda cerca de una esquina, el delantero se pega a
  la pared detrás de ella y la empuja paralela a la banda. La posición de la pelota se estima
  con distancia + sector. Se mueve en 8 direcciones sin girar (`_move_toward`) y la rodea por
  el lado de la cancha si está adelantado.

| Variante (12 semillas/lado) | Con ruido vs v1 / NT | Sin ruido vs v1 / NT | Esquinas |
|---|---|---|---|
| v2.3 (actual) | +5.6 / +9.8 | +8.1 (izq 1–3) / +15.0 | 33–36 % |
| v2.4 empuje hacia el ataque | +3.5 / +8.9 | **+14.6 (izq 2.9–1.5)** / +12.0 | 31–37 % |
| v2.4 empuje hacia afuera | +2.4 / +6.9 | +9.2 / +6.0 (pierde 0–3 de un lado) | 24–26 % (más de nuestro lado) |
| v2.4 + retroceso si se encaja | +2.5 / +8.5 | +12.5 / +5.0 (0-0 de un lado) | 30–35 % |

Cara a cara v2.4 (ataque) vs v2.3, 16 semillas: **+0.3 ± 1.2** con ruido y **−0.6 ± 0.3** sin
ruido.

**Decisión:** el equipo queda en **v2.3**. La jugada de banda no baja el tiempo en esquinas,
empata con v2.3 y empeora contra NormalTeam sin ruido. Su única ventaja clara es sin ruido
contra v1 (gana también de izquierda). Queda guardada en `experimentos/` con el retroceso
desactivado, por si en el torneo aparecen rivales parecidos a v1.

### Para el DL
La recompensa ya castiga la pelota quieta en esquinas (refine 6, sesión 8). Es el lugar
natural para atacar esto, porque la red puede aprender a no llevar la pelota ahí.

---

## Sesión 2026-10-17 (8) — Revisión y corrección de la función de recompensa (DL)

**Archivos nuevos:** `dvf_rewards.py`. Es una copia literal de la celda de recompensa de
`Soccer DeepLearning.ipynb`, con nuestros cambios marcados "DVF (2026-10-17)". El notebook
del curso no se tocó.

### Bugs encontrados
1. **Orientación al revés (bug de la recompensa base del curso).** El frente del jugador
   en este motor es `(sin a, −cos a)`, es decir `body.angle − 90°`. `W_FACE_BALL` y
   `W_SHOOT_ALIGN` usaban `(cos a, sin a)`, que es el eje lateral. Probado en simulación con
   un striker azul en angle = 90°:
   - Pelota adelante (sector 3) → `W_FACE_BALL` pagaba **0**. Pelota a la derecha (sector 7)
     → pagaba el **máximo**.
   - Mirando al arco rival → `W_SHOOT_ALIGN` pagaba **0**. Mirando hacia arriba (−y) →
     pagaba el **máximo**.

   Los dos le enseñaban a la red a ponerse de costado.
2. **Premio por quedarse quieto.** Ya corregida la orientación, la auditoría mostró que un
   delantero Passive cobraba **+2.6** en 180 s, más que NormalTeam (−2.4). El culpable
   principal era `W_SHOOT_ALIGN` (+4.48 estando quieto, contra +4.78 de v2.3). Era el término
   denso más grande y se cobraba parado. Es el atractor de "congelarse" del que avisa el
   notebook.
3. **Arquero dentro del arco.** Con `KEEPER_STANDOFF = 90`, el punto ideal quedaba en x = 121,
   dentro del arco (línea de gol x = 127, gol con la pelota en x < 117).

### Cambios
- Frente corregido en los dos términos de orientación.
- `W_FACE_BALL` y `W_SHOOT_ALIGN` escalados por la velocidad propia (`FACE_SPEED_REF = 200`).
  `W_SHOOT_ALIGN` además solo paga **detrás de la pelota**.
- `KEEPER_STANDOFF = 160` (x ≈ 191, unos 65 px delante de la línea).
- *Refine* implementados, uno por problema observado:
  - **2 anti-freeze** (striker, 0.0005·|v|/400 por paso).
  - **6 esquinas** (striker, −0.003 por paso con la pelota lenta en una esquina). Es lo que
    se ve en la ventana. En el entrenamiento una esquina trabada solo reinicia la pelota sin
    costo.
  - **8 trayectoria** (keeper, potencial hacia el punto donde el tiro cruza su línea; la
    suma se telescopa).
- No implementados: chase, stance, advance/strike-to-centre, intercept y clearance. Ya los
  cubren el delta de acercamiento, el dribble, la orientación corregida, `W_KICK_FWD` y las
  atajadas. Quedan como opciones si la curva lo pide.

### Verificación
**Auditoría** (180 s vs NormalTeam; la política indicada juega como agente):

| Política | Striker: original → nueva | Arquero: nueva |
|---|---|---|
| v1 (6 goles) | +149.7 → +153.2 | +40.8 (18 atajadas = +18.0, trayectoria +1.1) |
| v2.3 (0 goles) | +5.9 → +5.7 | −2.6 |
| NormalTeam | −2.4 → −2.1 | −2.7 |
| **Passive (quieto)** | +0.2 → **−1.9** | −3.1 |

Quieto ahora da negativo y el orden de las políticas es razonable. Además, 7 casos
sintéticos con respuesta conocida pasan: dirección de la orientación, quieto contra
corriendo, esquina, arquero hacia el punto de cruce o alejándose, pelota alejándose y la
firma de la llamada del entrenamiento.

### Pendiente (entorno de entrenamiento, no recompensa)
El entrenamiento del curso saca siempre del centro exacto (saque determinista: riesgo de que
aprenda un único saque contra un rival fijo) y solo reinicia por esquina trabada, no por
pelota quieta como la ventana. Se agrega en el script de entrenamiento (B1).

---

## Sesión 2026-10-17 (7) — v2.3: jugada de saque (PLAN A2)

**Archivos:** `soccer_team_DVF_v2.py` (v2.3.0), `PLAN_ENTREGA.md`.

### Problema
En la ventana (y en el torneo) la pelota sale exactamente del centro y cada saque es una
carrera determinista. Hay ~13–17 reinicios por partido, así que el saque pesa mucho. v2.2
vs v1 sin ruido: de izquierda recibía el gol de saque el 100 % de las veces.

### Jugada (`Striker._kickoff_play`, `_TeamTactics.kickoff_play_ticks`)
En cada saque (detectado por `_TeamTactics`), durante hasta `KICKOFF_PLAY_TICKS = 120`:
1. Girar hasta mirar exactamente al centro del arco rival. El frente del cuerpo empuja la
   pelota en esa dirección.
2. Avanzar a fondo y, a la vez, moverse de costado hasta quedar sobre la línea de la pelota
   (Y=440, tolerancia 6 px).
3. Terminar cuando la distancia a la pelota empieza a crecer, es decir cuando hubo contacto
   (nuestro o del rival).

Usa `body.position` y `body.angle` solo para leer, y la posición conocida de la pelota en
el saque (697.5, 440).

### Pruebas
- **Saques aislados** (gol en 3 s):
  - Sin ruido, de izq vs v1/v2.1: en contra 100 % → **0 %**.
  - Con ruido, de izq: en contra 12 % → **0 %**.
  - De der: igual o mejor (100 % / 14 %).
- **Punto de tiro** (`KICKOFF_SHOT_OFFSET`, lejos del spawn del arquero rival): probado
  0/80/130/180 px. **0 es lo mejor**: con otros valores se pierde el 100 % de goles de saque
  como violeta.
- **Partidos** (16 semillas por lado, con reinicio por pelota trabada):

| v2.3 vs | Con ruido | Sin ruido (torneo) |
|---|---|---|
| v1 | **+5.6 ± 1.8** (26-4-2); v2.2 daba +2.1 | +8.0 (16-0-16), izq 1–3 (v2.2: 1–9) |
| NormalTeam | +9.1 ± 1.7 (31-1-0); v2.2 daba +12.2 | +15.0 (32-0-0) |
| v2.1 | +4.6 ± 1.3 (26-3-3) | +19.1 (32-0-0) |
| v2.2 | **+3.4 ± 1.6** (19-8-5) | +30.5 (25-7-0) |

Goles de saque en contra: de 2.4 a **0.2 por partido** con ruido, y 0 sin ruido.

### Pendiente / costo
- Contra NormalTeam se gana por algo menos (+9.1 vs +12.2): v2.2 le hacía goles de saque
  que v2.3 ya no hace. Igual gana 31 de 32.
- Sin ruido, de izquierda contra v1 todavía se pierde 1–3, ahora por goles en juego abierto.
- La parte del delantero en el "repliegue tras gol rápido" quedó casi siempre tapada por la
  jugada de saque. El arquero sí lo sigue usando.

---

## Sesión 2026-10-17 (6) — v2.2: delantero "colgado" + benchmark como la ventana + plan

**Archivos:** `soccer_team_DVF_v2.py` (v2.2.0), `scripts/benchmark.py`,
`docs/BENCHMARK.md`, `PLAN_ENTREGA.md` (nuevo).

Contexto: **v2 es el equipo principal**; v1 (`soccer_team_DVF.py`) fue una primera versión
de un compañero y queda como rival de referencia.

### Bug: el delantero de v2 se quedaba en el área rival
- **Síntoma** (visto en la ventana): no se acercaba a la pelota ni volvía a defender.
- **Causa:** el anti-autogol iba *antes* del paso "pelota lejos → correr hacia ella" y se
  aplicaba a cualquier distancia. Con la pelota entre el delantero y su propio arco, este
  veía el arco rival atrás (sector 7/8) o el propio adelante y se negaba a avanzar: solo se
  movía de costado. Además oscilaba en Y=220 entre `move_downfield` y `_strafe("right")`.
- **Medido** con un detector (>300 px de la pelota, más cerca del arco rival que ella, sin
  acercarse durante ≥3 s): **17–25 episodios por partido → 0**.
- **Fix:** primero "pelota lejos → avanzar". El anti-autogol se aplica solo cerca de la
  pelota y la rodea (lateral + acercarse hasta `FORWARD_MIN_DIST`). El lado de la órbita lo
  elige `_orbit_side()`, que tiene en cuenta las paredes (`WALL_MARGIN = 220`) y fija el
  lado `ORBIT_LOCK_TICKS = 60` para no oscilar.

### Benchmark: emulación del reinicio por pelota trabada
El juego con ventana reinicia si la pelota queda 3 s quieta (y tras una cuenta 3-2-1); en
headless no. Sin esa emulación, v2.2 vs NormalTeam sin ruido daba 32 empates 0-0/1-1
idénticos. Ahora se emula por defecto (`--no-stuck-reset` lo desactiva), con unos 12–15
reinicios por partido.

### Resultados (16 semillas por lado, con reinicio por pelota trabada)
| | v2.1 | **v2.2** |
|---|---|---|
| Con ruido vs v1 | −1.1 ± 2.2 (13-5-14) | **+2.1 ± 2.1** (21-3-8) |
| Con ruido vs NormalTeam | +4.9 ± 2.3 (21-2-9) | **+12.2 ± 1.8** (31-0-1) |
| Con ruido vs v2.1 | — | **+2.4 ± 2.1** (19-2-11) |
| Sin ruido vs v1 | 16-0-16 | 16-0-16 (der 15.1–0.9 / izq 1.1–9.1) |
| Sin ruido vs NormalTeam | 16-16-0 | **32-0-0** |

**"Siempre gana el derecho" en la ventana:** sin ruido cada saque es determinista y hay ~13
reinicios por partido. Contra un rival con el mismo delantero (v1, v2.1), el de la derecha
gana siempre el saque exacto. Contra un rival distinto (NormalTeam), v2.2 gana de los dos
lados. Próximo paso en `PLAN_ENTREGA.md` (A2: jugada de saque).

### Plan
`PLAN_ENTREGA.md`: plan paso a paso hasta el martes 2026-10-20 para los tres entregables
(rule-based, metadata ML y red entrenada).

---

## Sesión 2026-10-17 (5) — `run.py`: equipos por línea de comandos

**Archivos:** `run.py`

Ahora `run.py` acepta dos argumentos opcionales (izquierda y derecha), así se puede jugar de
los dos lados sin editar el archivo:
```bash
env/Scripts/python.exe run.py soccer_team_DVF soccer_team_DVF_v2   # v2 a la derecha
env/Scripts/python.exe run.py soccer_team_DVF_v2 soccer_team_DVF   # v2 a la izquierda
```
Sin argumentos usa los imports de siempre. No sirve para espejos (el mismo módulo dos
veces comparte instancias): para eso está `scripts/benchmark.py`. Recordar que se entrega
solo el archivo del equipo, así que este cambio es solo para uso local.

---

## Sesión 2026-10-17 (4) — Banco de pruebas en el proyecto

**Archivos nuevos:** `scripts/benchmark.py`, `docs/BENCHMARK.md`. Ningún equipo modificado.

### Qué hace
`scripts/benchmark.py` reúne en una sola herramienta los scripts sueltos de las sesiones
2–3:
- Partidos headless en **ambos lados**, con **semillas fijas** (`--seeds`) y **ruido ±3 px**
  en el saque (`--jitter`).
- Un **proceso nuevo por partido**, para que el estado de módulo de los equipos no se
  arrastre.
- Modo **saques aislados** (`--kickoff-trials`) y **espejo** (`--vs` con el mismo equipo).
- Resumen con neto cada 2 partidos ± intervalo ~95 % y aviso "(dentro del ruido)", más
  `--out` para guardar los resultados crudos en JSONL.
- Acepta nombres de módulo o rutas `.py`, así se pueden probar variantes sin tocar el
  archivo real.

Uso y lectura de la salida: `docs/BENCHMARK.md`.

### Validación
Reproduce exactamente las mediciones de la sesión (3): v2.1 vs v1 −0.8 ± 1.6, vs
NormalTeam +2.9 ± 1.9, espejo v1 1.6–2.0. En 200 saques aislados recibe 21/200, contra
22/200 con el script anterior. Tiempos: 32 partidos ≈ 26 s y 400 saques ≈ 45 s, con 14
procesos.

### Matiz a la corrección de la sesión (3)
Con ruido, el **primer toque** se reparte cerca de 50/50, pero los **goles de saque**
siguen yendo casi solo para el **lado derecho** (v2.1 vs v1: 20/200 a favor como der, 21/200
en contra como izq, 0 en el resto). Hay entonces una asimetría real, aunque pequeña: en
partidos completos son ~0.4 goles por partido (espejo v1: −0.4 ± 1.3, dentro del ruido).
Sigue valiendo la regla: **evaluar siempre en los dos lados**.

---

## Sesión 2026-10-17 (3) — Guardia de saque del arquero: probada y REVERTIDA

**Archivos:** `soccer_team_DVF_v2.py`. Queda en v2.1; solo se agregó una nota en el
changelog del docstring.

### Qué se probó
Durante ~2.5 s después de cada saque (`KICKOFF_GUARD_TICKS = 150`), el arquero se ubica en
la banda Y 420–460, el centro del arco, en vez de quedar en su spawn (Y=352 azul / 528
violeta). Variantes probadas:
- **Home / hold / profunda:** se centra ignorando la pelota, retrocediendo hasta 220 px del
  arco, sin retroceder o hasta 110 px.
- **Híbrida:** se centra solo con la pelota justo enfrente (sector 3) y en los demás casos la
  sigue como en v2.1.

Código de la híbrida, por si se quiere retomar (en `Keeper.default`, después del seguimiento
lateral):
```python
elif _TeamTactics.is_kickoff_guard():      # pelota en sector 3
    if py < 420: self.move_downfield()
    elif py > 460: self.move_upfield()
```

### Hallazgo clave: el saque es caótico
Los dos delanteros llegan a la pelota casi al mismo tiempo, y unos pocos píxeles deciden
para dónde sale. Cambiar algo lejos de la jugada (la posición de nuestro arquero) alcanza
para cambiar el orden en que pymunk resuelve los contactos, y con eso el resultado. Sin
ruido, un saque concreto da siempre lo mismo (40/40), así que **medir sin ruido engaña**.
Desde ahora el banco de pruebas mueve la pelota ±3 px en cada saque.

### Resultados con ruido
Saques aislados (goles de saque recibidos):

| Variante | Como azul (200) | Como violeta (200) |
|---|---|---|
| **v2.1** | 22–23 | 1–4 |
| Guardia híbrida | 39 | 14 |
| Guardia home (sobre 100) | 20/100 (v2.1: 11–12) | 11/100 (v2.1: 1) |

Partidos completos (8 por lado, neto cada 2 partidos):

| | vs v1 | vs NormalTeam |
|---|---|---|
| **v2.1** | −0.8 | +2.9 |
| Guardia híbrida | −1.5 | +4.4 |

**Decisión:** se revierte. Los saques aislados, que son la medición más precisa, muestran que
centrar al arquero empeora claramente la defensa del saque. Los partidos completos son mixtos
y caen dentro del ruido.

### ⚠ Corrección de la sesión (2)
- El gran "sesgo del lado derecho" **desaparece con ruido**: v1 vs v1 queda 13–16 sumando
  8 partidos, y el primer toque se reparte cerca de 50/50. Era sobre todo el caos del saque
  exacto. (Matizado en la sesión (4): queda un sesgo chico en los goles de saque.)
- El desfase `POSITION_GOAL_BLUE = (31, 400)` existe, pero **no está probado que sea "la
  causa"**. Es una de muchas perturbaciones que inclinan la moneda del saque.
- **v2.1 vs v1 queda en −0.8** con ruido, o sea empate dentro del ruido, y no +3.6. El fix
  del arquero sigue siendo correcto: el arquero violeta ya no se aleja de la pelota.

---

## Sesión 2026-10-17 (2) — Investigación: sesgo de lado y "caída" del ataque violeta

> ⚠ Las conclusiones numéricas de esta sesión se midieron **sin ruido** en el saque y están
> corregidas en la sesión (3).

**Archivos de equipo modificados:** ninguno (solo análisis). Los scripts de prueba quedaron
en el scratchpad de la sesión, fuera del proyecto.

### Método
- 96 partidos headless de 300 s con semillas fijas, 8 por cruce y en ambos lados.
- Partidos espejo (v1 vs v1, v2.1 vs v2.1) para medir el sesgo de la cancha.
- Ablación de v2: viejo, solo fix del arquero (`kfix`), solo fix de upfield/downfield
  (`sfix`) y v2.1 completo.
- Cada gol se registra con el tiempo desde el saque. Además, 40 saques aislados por
  hipótesis.

### Hallazgo 1 — La cancha favorece al lado derecho (violeta)
| Espejo | Total izq–der |
|---|---|
| v1 vs v1 | 0.9 – 5.5 |
| v2.1 vs v2.1 | 0.1 – 5.6 |

- De todos los goles medidos, el violeta hizo **291 en menos de 2 s** después del saque y el
  azul **1**.
- En 40 saques aislados v1 vs v1, el violeta gana el primer toque y mete gol **40/40**. Es
  una carrera determinista: la semilla no cambia nada.
- **Causa en el motor:** `game/playground.py` usa `POSITION_GOAL_BLUE = (31, 400)`, pero
  `POSITION_GOAL_PURPLE = (1368, 440)`. El punto simétrico sería (27, 440). Con ese único
  cambio, en la simulación el azul gana los 40 saques. Los 40 px de diferencia rompen la
  simetría y deciden la carrera del saque. El arquero azul también se ubica centrado en
  Y≈400 en lugar del centro real del arco (≈442).
- Como el motor es de la cátedra, **no lo tocamos**. Conviene avisarle al docente.

### Hallazgo 2 — v2 "pierde a la izquierda" por el lado, no por v2
Los strikers de v1 y v2 son casi iguales, así que el que juega a la derecha gana el saque.
Sumando los dos lados (goles a favor – en contra cada 2 partidos):

| v2 contra v1 | Como violeta | Como azul | **Neto** |
|---|---|---|---|
| v2 viejo | 14.0 – 8.5 | 1.2 – 6.9 | **−0.2** |
| solo kfix | 6.2 – 1.1 | 1.9 – 6.8 | +0.2 |
| solo sfix | 12.8 – 7.0 | 2.8 – 6.1 | +2.5 |
| **v2.1** | 7.4 – 1.0 | 2.8 – 5.6 | **+3.6** |

Con los dos fixes, v2.1 es la mejor variante y la única que le gana claramente a v1.

### Hallazgo 3 — La "caída" del ataque violeta es un artefacto
Cada gol en contra genera un saque nuevo, y el violeta casi siempre lo convierte en menos de
5 s. Con el arquero viejo, el violeta recibía 8.5 goles y hacía 8.4 goles de saque. Con el
arquero arreglado recibe 1.0 y hace 2.9 de saque. **Menos goles en contra significa menos
saques, y eso significa menos goles de saque.** En juego abierto el ataque casi no cambió
(5.6 → 4.5).

### Advertencias
- 8 partidos por cruce: los números son tendencias, no valores exactos.
- En headless no corre el "stuck watch" del motor (reinicio si la pelota queda trabada ~3 s).
  En el juego con ventana hay **más** saques, así que el saque pesa todavía más.
- La métrica "autogol" (último jugador cerca de la pelota) confundía los roces del arquero
  con autogoles. Por eso se descartó y se usa el tiempo desde el saque.

---

## Sesión 2026-10-17 — Fix de movimientos dependientes del lado (v2.1.0)

**Archivos:** `soccer_team_DVF_v2.py`

### Problema
Los sensores (`view_field`) son **relativos a la mirada del jugador**: los sectores 0–2
significan "a mi izquierda". Para el azul (mira hacia +X) eso es −Y, pero para el violeta
(mira hacia −X) es +Y.

- **Arquero:** v2 traducía "pelota a la izquierda" a `move_upfield()` (siempre −Y). Con el
  equipo violeta el arquero se alejaba de la pelota y se quedaba pegado al poste contrario.
  Como en `run.py` v2 juega a la derecha (violeta), las pruebas v1 vs v2 estaban sesgadas.
- **`move_upfield` / `move_downfield`:** elegían izquierda/derecha según el color del
  equipo, lo que solo es correcto con la orientación inicial. El delantero gira libremente,
  así que el rodeo anti-autogol y la defensa de saque podían ir para cualquier lado.

### Cambios
- `_Sensors._strafe_dy(side)`: nuevo. Calcula con `body.angle` (solo lectura) hacia dónde
  en Y mueve un paso lateral.
- `_Sensors._move_world_y(sign)`: nuevo. Paso lateral hacia +Y/−Y real; no hace nada si el
  jugador mira a lo largo del eje Y (`LATERAL_MIN_DY = 0.3`).
- `move_upfield` / `move_downfield`: ahora usan `_move_world_y`.
- `Keeper.default`: sigue a la pelota con `move_left` / `move_right` (como v1) y frena solo
  si ese paso lo saca de entre los postes (`POST_TOP_Y` / `POST_BOTTOM_Y`).

### Verificación
**Escenario del arquero violeta** (pelota fija a un costado del arco, 90 ticks):

| Versión | Pelota en Y=620 | Pelota en Y=260 |
|---|---|---|
| v2 viejo | 440 → 233 (se aleja) | 440 → 649 (se aleja) |
| v2.1 | 440 → 632 (va hacia la pelota) | 440 → 242 (va hacia la pelota) |

Nota: el límite de postes deja de empujar en 265/615, pero por inercia el arquero se pasa
unos 20 px.

**Partidos headless** (300 s, 4 partidos por cruce; resultado promedio, v2 primero):

| Cruce | v2 viejo | v2.1 |
|---|---|---|
| v2 a la derecha (violeta) vs v1 | 13.0 – 7.5 | 7.5 – 2.0 |
| v2 a la izquierda (azul) vs v1 | 2.0 – 8.75 | 0.75 – 6.25 |
| v2.1 vs NormalTeam (izq / der) | — | 1–1 (x4) / 3–0 (x4) |

- Como violeta, v2.1 recibe muchos menos goles (7.5 → 2.0), pero también hace menos
  (13 → 7.5). La diferencia de gol queda igual (+5.5).
- **Hallazgo:** v2 (viejo y nuevo) **pierde contra v1 cuando juega a la izquierda**. La
  ventaja de v2 que se veía en `run.py` dependía del lado de la cancha. Hay que evaluar
  siempre en los dos lados.

### Respaldo
Versión anterior guardada fuera del proyecto (scratchpad de la sesión) para comparar.
