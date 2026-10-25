# Empezar acá (Diego, Fernando) — seguir entrenando el DL en tu PC

Paquete armado el 25/10/2026 por Valentino. Contiene todo el proyecto, sin el venv (`env\`) y sin
los checkpoints intermedios (pesan ~1,3 GB).

## 1. Instalar (una sola vez)

1. Descomprimí el zip en una carpeta. Puede tener espacios en el nombre, pero entonces las rutas
   van siempre entre comillas.
2. Tené instalado **Python 3.10** (https://www.python.org/downloads/release/python-31011/; en el
   instalador, marcá "Add python.exe to PATH").
3. En PowerShell, parado en la carpeta del proyecto:
   ```
   powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
   ```
   Crea `env\`, instala `requirements.txt` y corre `scripts\verificar_entorno.py`. Tiene que
   terminar con **"Listo para entrenar"** y 0 fallas.

## 2. Si usás una IA (Claude, ChatGPT/Codex, Cursor, Copilot…)

Abrí la carpeta del proyecto con la IA y pedile que **lea `AGENTS.md` y `docs/CONTEXTO_DL.md`
antes de hacer nada**. Ahí están las reglas, el estado, los comandos y los errores que ya
cometimos. Claude Code lee `CLAUDE.md` solo.

## 3. Entrenar

- Usá un **nombre de corrida tuyo**, por ejemplo `corrida6_diego`. No pises `corrida5`.
- Para seguir desde lo último de corrida5 (con su optimizador), copiá
  `models\runs\corrida5\striker.npz` y `keeper.npz` a una carpeta, por ejemplo
  `models\inicio_diego\`, y lanzá:
  ```
  powershell -ExecutionPolicy Bypass -File scripts\lanzar_corrida.ps1 -Run corrida6_diego -InitFrom models\inicio_diego -Workers 6 -StrikerEntropy 0.015 -KeeperEntropy 0.01 -Lr 1e-4 -Hasta 2026-10-30T08:00 -Desacoplado
  ```
  - `-Workers`: la mitad de tus núcleos menos 2 si usás la PC (lo sugiere
    `verificar_entorno.py`), siempre en prioridad baja.
  - `-Hasta`: fecha y hora en que termina. Se puede mover sin cortar, escribiendo otra fecha en
    `models\runs\<corrida>\until.txt`.
- Otros puntos de partida posibles:
  - el mejor par medido: `models\runs\corrida5\chequeos\20261024_1401_*.npz`, que trae solo pesos;
  - la imitación de la v2.3: `models\imitacion\equipo_v23`.
- Cortar después de un guardado:
  `powershell -ExecutionPolicy Bypass -File scripts\cortar_corrida.ps1 -Run corrida6_diego`

## 4. Medir (cada hora, más o menos)

```
env\Scripts\python.exe scripts\chequeo_completo.py --run corrida6_diego --workers 8
```
Deja un informe en `models\runs\corrida6_diego\chequeos\`: partidos de 1 y 3 minutos con gol de
oro contra NormalTeam, v1 y v2.3, % de carrera de espaldas y saques. Compará con las referencias
del informe. Y mirá partidos en ventana:
```
$env:DVF_DL_STRIKER="models\runs\corrida6_diego\striker.npz"; $env:DVF_DL_KEEPER="models\runs\corrida6_diego\keeper.npz"
env\Scripts\python.exe run.py soccer_team_DVF_DL soccer_team_DVF_v2 --duracion 60 --gol-de-oro
```

## 5. Devolver lo que hiciste

Comprimí `models\runs\<tu corrida>\` **sin** la carpeta `checkpoints\` y mandala. Anotá qué
hiciste en `CHANGELOG.md` (una sesión nueva arriba de todo, con tu nombre).

Más detalle: `AGENTS.md` (resumen para la IA), `docs/CONTEXTO_DL.md` (cómo funciona todo) y
`PROTOCOLO_CORTE.md` (cortes de internet).
