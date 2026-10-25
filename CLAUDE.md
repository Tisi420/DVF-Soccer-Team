# CLAUDE.md

Todo el contexto del proyecto está en **AGENTS.md** (vale para cualquier asistente de IA):

@AGENTS.md

Para entrenar o evaluar la red, leé también `docs/CONTEXTO_DL.md`. Las sesiones más recientes
están arriba en `CHANGELOG.md`.

Notas para Claude Code:
- Hablá en español y comentá cada cambio de código (ver AGENTS.md §2).
- Antes de lanzar procesos largos, verificá el entorno con `scripts/verificar_entorno.py` y usá
  `-Desacoplado`, para que no mueran si se cierra la app.
- Al retomar después de un corte de internet, leé primero `models/runs/_estado/ESTADO.md`.
