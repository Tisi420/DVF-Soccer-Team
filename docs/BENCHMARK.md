# Banco de pruebas (`scripts/benchmark.py`)

Herramienta del equipo DVF para comparar equipos de forma **justa y repetible**: muchos
partidos headless, en **los dos lados** de la cancha, con **semillas fijas** y un pequeño
**ruido en el saque**.

> Usá siempre el Python del entorno virtual del proyecto (`env/`), desde la raíz del
> proyecto.

---

## Uso rápido

```bash
# v2 contra v1 (8 partidos de 300 s por lado = 16 partidos)
env/Scripts/python.exe scripts/benchmark.py soccer_team_DVF_v2 --vs soccer_team_DVF

# contra varios rivales, con más partidos (más precisión)
env/Scripts/python.exe scripts/benchmark.py soccer_team_DVF_v2 --vs soccer_team_DVF soccer_team_NormalTeam --seeds 16

# solo el saque: 200 saques aislados de 3 s por lado
env/Scripts/python.exe scripts/benchmark.py soccer_team_DVF_v2 --vs soccer_team_DVF --kickoff-trials 200

# partido espejo (mismo equipo en los dos lados) para medir el sesgo de lado
env/Scripts/python.exe scripts/benchmark.py soccer_team_DVF --vs soccer_team_DVF
```

En Linux/macOS: `env/bin/python scripts/benchmark.py ...`

Los equipos se pasan como nombre de módulo (`soccer_team_DVF`) o como ruta a un `.py`. Con
rutas se pueden probar variantes sin tocar el archivo real, por ejemplo
`scripts/benchmark.py experimentos/mi_variante.py --vs soccer_team_DVF`.

## Opciones

| Opción | Default | Qué hace |
|---|---|---|
| `team` | — | Equipo a evaluar. |
| `--vs RIVAL ...` | `soccer_team_DVF` | Uno o más rivales. Si ponés el mismo equipo, se juega un espejo. |
| `--seeds N` | 8 | Partidos **por lado** y por rival, con las semillas 0..N-1. |
| `--duration S` | 300 | Segundos simulados por partido. |
| `--jitter PX` | 3 | Ruido ±px en la posición de la pelota en cada saque. `0` = determinista, como en el torneo. |
| `--no-stuck-reset` | (emula) | Por defecto se emula el reinicio del juego con ventana cuando la pelota queda trabada (3 s quieta en un radio de 45 px + cuenta 3-2-1 de 2.4 s). Esta opción lo desactiva. |
| `--kickoff-trials N` | 0 | En lugar de partidos, N saques aislados de 3 s por lado. |
| `--workers N` | núcleos − 2 | Procesos en paralelo. |
| `--out archivo.jsonl` | — | Guarda los resultados crudos (marcador y cada gol con su tiempo desde el saque). |

## Cómo leer la salida

### Partidos

```
rival                        n |    como izq |    como der |   neto/2 part. |    G-E-P | saque fav-contra
soccer_team_DVF           8+8  |  1.9 -  2.2 |  1.8 -  2.1 |  -0.8 ±  1.6 |    4-6-6 |        1.0 - 1.0  (dentro del ruido)
soccer_team_NormalTeam    8+8  |  4.1 -  1.0 |  2.5 -  2.8 |  +2.9 ±  1.9 |    8-3-5 |        1.3 - 0.2
```
(Salida real de v2.1, 2026-10-17.)

- **como izq / como der:** goles a favor – en contra por partido, jugando a la izquierda (azul)
  y a la derecha (violeta).
- **neto/2 part.:** diferencia de gol como izq + como der, es decir, lo que se espera
  ganar en un par de partidos (uno de cada lado). **Es el número para comparar versiones.**
- **± :** intervalo de ~95 % (2 errores estándar). Si |neto| no supera el ±, aparece
  **"(dentro del ruido)"**: no se puede afirmar que uno sea mejor. Subí `--seeds`.
- **G-E-P:** partidos ganados, empatados y perdidos.
- **saque fav-contra:** goles por partido metidos o recibidos en los primeros 5 s después
  de un saque.

### Saques aislados

Para cada lado muestra cuántos de los N saques terminaron en gol a favor o en contra dentro
de los 3 s. Es la medición más precisa para cambios que afectan solo el saque.

```
rival                    |  como izq: a favor / en contra |  como der: a favor / en contra
soccer_team_DVF          |    0/200 ( 0.0%) /   21/200 (10.5%) |   20/200 (10.0%) /    0/200 ( 0.0%)
```
Referencia (v2.1 vs v1): el primer toque se reparte cerca de 50/50, pero los goles de saque
van casi siempre para el lado derecho. Comparar siempre contra esta línea de base.

## Por qué está hecho así

Lo aprendimos a los golpes (ver `CHANGELOG.md`, sesiones 2 y 3):

1. **El saque es caótico.** Los dos delanteros llegan a la pelota casi al mismo tiempo y
   unos pocos píxeles deciden para dónde sale. Cambiar algo lejos de la jugada, como la
   posición de nuestro arquero, cambia el orden en que pymunk resuelve los contactos y con
   eso el resultado. **Sin ruido**, cada saque da siempre lo mismo y aparecen conclusiones
   falsas: medimos un sesgo enorme a favor del lado derecho (0.9–5.5 en v1 vs v1) y una
   supuesta ventaja de +3.6 de v2.1 sobre v1. Con ruido, el espejo queda en −0.4 ± 1.3 y
   v2.1 vs v1 en −0.8 ± 1.6.
2. **Siempre en los dos lados.** Queda una asimetría real pequeña: los goles de saque van
   casi solo para el lado derecho (~10 % de los saques contra ~0–1 %). En partidos completos
   son ~0.4 goles por partido, dentro del ruido, pero alcanzan para sesgar una comparación
   de un solo lado.
3. **Un proceso nuevo por partido.** Los equipos guardan estado a nivel de módulo
   (instancias `striker`/`keeper`, atributos de clase como `_TeamTactics`). Si se reusa el
   proceso, ese estado se arrastra de un partido al siguiente.
4. **Semillas fijas.** La misma corrida da los mismos números, así se pueden comparar
   versiones.

## Limitaciones

- **Reinicio por pelota trabada.** En headless el motor no corre el "stuck watch", así que el
  benchmark lo emula por defecto (~12–15 reinicios por partido entre equipos DVF). Sin esa
  emulación salían empates 0-0 idénticos que no pasan en la ventana.
- **Dos preguntas distintas.** *Con ruido* mide el rendimiento esperado: ¿la estrategia es
  mejor? *Sin ruido* (`--jitter 0`) reproduce el torneo, donde la pelota sale exactamente
  del centro y cada saque es determinista: ¿qué pasa de cada lado? Para el rule-based final
  conviene mirar las dos.
- **Ruido estadístico.** Con 8 semillas, diferencias de ±1.5 goles netos suelen ser azar.
  Para decidir entre dos versiones parecidas, usá `--seeds 16` o más.
- **Tiempos de referencia** (14 procesos en paralelo, 16 núcleos): 32 partidos de 300 s
  (8 semillas contra 2 rivales) tardan ~26 s, y 200 saques por lado (400 pruebas), ~45 s.
