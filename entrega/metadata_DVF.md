# Metadata ML — DVF

Corridas: noche1, corrida2, corrida3

| campo | valor |
|---|---|
| Team | DVF |
| horas de entrenamiento | 29.0 |
| CPU/GPU | CPU (16 núcleos), sin GPU |
| épocas | 4 |
| capas | 3 |
| neuronas | 394 |
| modelos entrenados | 2 (striker + keeper), 170 fases alternadas |
| ideas creativas | Recompensa propia (dvf_rewards.py): eje de orientación corregido, recompensas de orientación escaladas por velocidad (sin premio por quedarse quieto), arquero parado en la trayectoria del tiro, malus por pelota trabada en esquinas; entrenamiento alternado striker/keeper contra NormalTeam y nuestros equipos rule-based v1/v2.3, con ruido en el saque, exploración por rol y detección automática de estancamiento. |
