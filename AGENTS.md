# AGENTS.md — contexto para asistentes de IA (equipo DVF, Robotic Soccer)

> Leé este archivo **entero** antes de tocar nada. Después leé `docs/CONTEXTO_DL.md` si vas a
> entrenar o evaluar la red, y las 3–4 sesiones más nuevas de `CHANGELOG.md` (están arriba).
> Actualizado: 2026-10-25 (sesión 63). Empezá por `EMPEZAR_ACA.md` si sos una persona.

## 1. Qué es este proyecto

Praktikum "Robotic Motions" (Reutlingen University). Fútbol 2 contra 2 simulado con pymunk: cada
equipo tiene un **striker** y un **keeper**. Equipo **DVF** = Diego, Valentino y Fernando.

- **Rule-based**: entregado (`entrega/soccer_DVF.py` = nuestra v2.3). En el torneo rule-based DVF
  perdió en la semifinal.
- **Deep Learning (PPO)**: la entrega es **opcional, a fin de semestre**. Es lo que se está
  entrenando ahora (corrida5).
- **Formato del torneo**: partidos de **1 minuto**; si hay empate, **gol de oro**. La final dura
  **3 minutos**. Todo se evalúa en ese formato.

Idioma del equipo: **español** (rioplatense). Los comentarios de código y los documentos van en
español.

## 2. Reglas de trabajo (obligatorias)

1. **Comentar cada cambio** en el código: qué y por qué, con la sesión/fecha, por ejemplo
   `# DVF (2026-10-25, sesión 61): ...`.
2. **Registrar cada sesión en `CHANGELOG.md`**, arriba de todo, como "Sesión AAAA-MM-DD (N) —
   título". Qué se cambió, qué se midió (con números) y qué se decidió.
3. **No modificar archivos del curso**: `game/`, `setup_dl_notebook.py`, `setup_game_notebook.py`,
   los notebooks y `soccer_team_NormalTeam.py`/`Passive`/`ManualControl`/`DeepLearning`. Si hay que
   cambiar el comportamiento del entorno, se parchea desde `scripts/train_dl.py` a nivel de módulo.
4. **No renombrar** `soccer_team_DVF.py` (v1), `soccer_team_DVF_v2.py` (v2.3) ni
   `soccer_team_NormalTeam.py`: el entrenamiento los importa como rivales con los nombres `DVF`,
   `DVF_v2` y `NormalTeam`.
5. **Decidir con partidos, no con los números del entrenamiento.** El % de goles del log de
   entrenamiento engañó varias veces. Ver §6.
6. **Cuidar la PC**: prioridad baja (BelowNormal) y pocos workers. En una PC de 16 núcleos: **6
   workers si alguien la está usando** (10 ya la deja "al palo") y hasta 8 si nadie la usa. La PC
   de Valentino tuvo apagones bruscos por temperatura con 14 o más.
7. Archivos de texto con fin de línea **LF**. Los `.ps1` en **UTF-8 con BOM** (PowerShell 5.1).
8. No borrar datos de corridas ni checkpoints sin preguntar.

## 3. Entorno (Windows)

- Python **3.10** en un venv en `env\` (`env\Scripts\python.exe`). Paquetes: `requirements.txt`
  (TensorFlow 2.x, numpy < 2.3, pymunk 6.11, pygame 2.6, moderngl, cloudpickle, matplotlib).
- **Antes de entrenar en una PC nueva**: `python scripts\verificar_entorno.py`. Revisa versiones,
  imports, un partido corto, el equipo DL y un entrenamiento mínimo.
- La ruta del proyecto tiene espacios ("robotic motions"): **siempre entre comillas**.
- Los workers de multiprocessing (spawn) corren con el **intérprete base de Python**, no con el del
  venv. Para encontrarlos o matarlos, filtrar por la línea de comando: llevan
  `spawn_main(parent_pid=<PID de train_dl>`, y ese PID queda en `models/runs/<run>/train_pid.txt`.
- `training.log` está en cp1252: para buscar con grep, `grep -a`.

## 4. Mapa de archivos

| Archivo | Qué es |
|---|---|
| `soccer_team_DVF_v2.py` | Rule-based **v2.3** (el mejor). Igual a `entrega/soccer_DVF.py`. Lee `body.*`, nunca lo escribe. |
| `soccer_team_DVF.py` | Rule-based v1.1 (rival de referencia). |
| `experimentos/` | Rule-based probados y no adoptados: v2.4 (banda) y v2.5 (ideas del torneo, interruptores `DVF25=`). |
| `soccer_team_DVF_DL.py` | **Equipo DL** (carga `.npz`). Variables: `DVF_DL_STRIKER` + `DVF_DL_KEEPER` (rutas) o `DVF_DL_RUN=<corrida>`; `DVF_DL_ARGMAX=1` (determinista, por defecto muestrea); `DVF_DL_FIX_Y=0` (desactiva la corrección del violeta). |
| `dvf_rewards.py` | Recompensa. **`REWARD_VERSION = "v4"`**. Subir la versión cada vez que se cambia. |
| `scripts/train_dl.py` | Entrenamiento PPO (fases alternadas striker/keeper, workers en paralelo, rivales con pesos, parches del entorno). |
| `scripts/supervisar_entrenamiento.py` | Relanza `train_dl` si Windows lo tira (crash nativo 0xc0000005). |
| `scripts/lanzar_corrida.ps1` / `cortar_corrida.ps1` | Lanzar una corrida (`-Desacoplado`) o cortarla después de un guardado, sin tocar otras. |
| `scripts/benchmark.py` | **Evaluación oficial**: ambos lados, ruido en el saque, semillas, `--duration 60 --gol-de-oro`. |
| `scripts/chequeo_completo.py` | Chequeo de una corrida: curva, formato torneo de 1 y 3 min, % de espaldas, saques → informe `.md`. |
| `scripts/monitorear.py` | Monitor periódico (desacoplado) → `models/runs/<run>/monitoreo.md`. |
| `scripts/imitar_equipo.py` | Imitación de la v2.3 (striker + keeper + valor) → `models/imitacion/equipo_v23/`. |
| `scripts/protocolo_corte.py` | Vigilante de cortes de internet: foto del estado, respaldo, cuarentena (`PROTOCOLO_CORTE.md`). |
| `scripts/sondas/` | Diagnósticos: espaldas, saques, keeper, recompensa. |
| `run.py` | Partido **en ventana**: `python run.py <izq> <der> --duracion 60 --gol-de-oro`. |
| `models/runs/<run>/` | Una corrida: `striker.npz`, `keeper.npz`, `run.json` (fases, horas, config), `training.log`, `checkpoints/`, `chequeos/`. |

## 5. Estado del Deep Learning (lo más importante) — al 25/10/2026 13:16

- **Última corrida: `corrida5`** (detenida y guardada: 2,46 h, 14 fases). Arranca de la
  **imitación del equipo v2.3** (`models/imitacion/equipo_v23`). Configuración:
  - recompensa v4;
  - lr 1e-4;
  - entropía del striker 0,015 y del keeper **0,01** desde las 13:14 del 25/10 (antes 0,015: su
    entropía subía y volvía peor al arco en el saque);
  - rivales v2.3 ×3, v1 ×2, NormalTeam ×1 (con 6 workers);
  - un saque nuevo cada 60 s sin gol.
  Para seguirla: `models/runs/corrida5/striker.npz` y `keeper.npz`, que traen el estado de Adam.
- **Mejor par medido**: `models/runs/corrida5/chequeos/20261024_1401_{striker,keeper}.npz`
  (1,43 h). En 1 min con gol de oro, G-E-P en 32 partidos:

| par | NormalTeam | v1 | v2.3 |
|---|---|---|---|
| **corrida5 24/10 14:01 (mejor)** | 30-0-2 | 27-0-5 | 7-3-22 |
| corrida5 25/10 13:02 (`monitoreo/1302_*`) | 29-0-3 | 21-2-9 | 6-0-26 |
| rule-based v2.3 (referencia) | 30-0-2 | 27-0-5 | 13-6-13 |

  Contra NormalTeam y v1 ya está al nivel del rule-based v2.3.
- **`entrega/red_DL/`** tiene el modelo VIEJO (corrida3). Corre de espaldas el 92 % del tiempo y es
  peor en todo. **No se usa de base.** Se reemplaza cuando se elija el modelo final.
- **Pendientes**:
  - mejorar contra v2.3;
  - que el keeper vuelva más rápido al arco en el saque;
  - mantener la carrera del saque del striker (el 25/10 ganaba 6 de 10 primeros toques contra
    v2.3);
  - vigilar el % de carrera de espaldas (8–16 %; casi 0 % yendo hacia la pelota).

## 6. Lecciones aprendidas (no repetir errores)

1. **Bug de la observación del violeta** (`game/keras_core.py`, del curso): no invierte la
   posición y ni la velocidad y. La corrección vive en `soccer_team_DVF_DL.py` (`_obs`).
   **Entrenar siempre de azul** (como hace `train_dl`); la red juega de violeta gracias a esa
   corrección.
2. **El % de goles del entrenamiento no predice los partidos.** Elegir modelos con
   `benchmark.py`, en formato torneo, ambos lados, **16 o más semillas** (con 4 el ruido es de
   varios goles), sobre **copias fijas** de los `.npz` (durante el entrenamiento cada partido
   cargaría un guardado distinto).
3. **Correr de espaldas**: la hitbox es un cuadrado simétrico de 70 px y avanzar o retroceder
   acelera igual, así que PPO aprende a retroceder hacia la pelota para no girar. Lo frena la
   recompensa v4 (`W_FRENTE`). Medir con `scripts/sondas/sonda_espaldas.py`.
4. **Entropía (exploración)**: con 0,02–0,05 la red queda al azar; con 0,01, desde imitación,
   colapsa (entropía ~0,2) y empeora. corrida5 usa 0,015 con lr 1e-4.
5. **Rivales con pesos**: la lista `--opponents` se reparte por turno entre los workers (los
   repetidos pesan más). Repartidos parejo, la red se sobreajusta a NormalTeam; hay que darle más
   peso a v2.3.
6. **Más horas no es mejor**: PPO alternado puede desestabilizar un buen modelo. Guardar
   candidatos y elegir por benchmark.
7. **La forma del jugador** (`shape` en `get_team_appearance`) es solo visual: la hitbox es la
   misma para todos.
8. **Reloj de Windows**: después de un apagón quedó 13 h atrás, y eso arruina las horas de
   `run.json`. `lanzar_corrida.ps1` no lanza si el reloj está desfasado.
9. Lanzar los procesos largos **desacoplados** (`-Desacoplado`): si no, mueren al cerrarse la app
   que los lanzó.

## 7. Comandos típicos

```powershell
# Verificar una PC nueva
env\Scripts\python.exe scripts\verificar_entorno.py

# Seguir corrida5 (retoma del último guardado; -Hasta = hora de fin)
powershell -ExecutionPolicy Bypass -File scripts\lanzar_corrida.ps1 -Run corrida5 -InitFrom models\imitacion\equipo_v23 -Workers 10 -StrikerEntropy 0.015 -KeeperEntropy 0.015 -Lr 1e-4 -Hasta 2026-10-26T08:00 -Desacoplado
# (-Workers 6 si se está usando la PC)

# Cortar después de un guardado
powershell -ExecutionPolicy Bypass -File scripts\cortar_corrida.ps1 -Run corrida5

# Chequeo completo (prioridad baja)
env\Scripts\python.exe scripts\chequeo_completo.py --run corrida5 --workers 10

# Partido en ventana, formato torneo, con un par concreto
$env:DVF_DL_STRIKER="ruta\striker.npz"; $env:DVF_DL_KEEPER="ruta\keeper.npz"
env\Scripts\python.exe run.py soccer_team_DVF_DL soccer_team_DVF_v2 --duracion 60 --gol-de-oro
```

## 8. Si entrenás en OTRA PC (Diego, Fernando)

- Usá un **nombre de corrida propio**, por ejemplo `corrida6_diego`, para no pisar `corrida5`.
  Para arrancar desde lo último de corrida5: `-InitFrom` apuntando a una carpeta con su
  `striker.npz` y `keeper.npz`.
- Para compartir: comprimí `models/runs/<tu corrida>/` **sin** `checkpoints/`, más los `chequeos/`
  que quieras proponer como candidatos.
- Registrá tu sesión en `CHANGELOG.md` con tu nombre.
- Detalle paso a paso: `docs/CONTEXTO_DL.md`.
