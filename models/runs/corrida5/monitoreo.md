# Monitoreo de corrida5

Neto por par de partidos (uno de cada lado), 16 semillas por lado, partidos de 60 s con gol de oro, ruido 3, corrección violeta. Criterio = promedio contra v1 y v2.3.

## 2026-10-24 13:25 · 0.96 h, 6 fases

| ciclo | rol | exploración | entropía | a favor/act. | en contra/act. | % a favor |
|---|---|---|---|---|---|---|
| 2 | striker | 0.015 | 1.0194 | 2.147 | 1.136 | 65 % |
| 2 | keeper | 0.015 | 1.2444 | 2.022 | 1.087 | 65 % |
| 3 | striker | 0.015 | 1.2096 | 2.114 | 1.201 | 64 % |
| 3 | keeper | 0.015 | 1.2862 | 2.168 | 0.821 | 73 % |

| rival | neto | ± | G-E-P |
|---|---|---|---|
| NormalTeam | +5.3 | 1.3 | 31-0-1 |
| DVF | +2.5 | 0.6 | 30-1-1 |
| DVF_v2 | -0.8 | 0.7 | 10-2-20 |

**Criterio: +0.8** · par guardado en `monitoreo/1325_striker.npz` + `_keeper.npz`

Striker en movimiento: **15 % de espaldas**, 66 % de frente (1 partido de 120 s contra v2.3).

## 2026-10-25 13:02 · 2.25 h, 13 fases

| ciclo | rol | exploración | entropía | a favor/act. | en contra/act. | % a favor |
|---|---|---|---|---|---|---|
| 5 | keeper | 0.015 | 1.8851 | 1.473 | 0.873 | 63 % |
| 6 | striker | 0.015 | 1.2967 | 1.633 | 0.947 | 63 % |
| 6 | keeper | 0.015 | 2.0839 | 2.045 | 1.012 | 67 % |
| 7 | striker | 0.015 | 1.316 | 1.873 | 1.159 | 62 % |

| rival | neto | ± | G-E-P |
|---|---|---|---|
| NormalTeam | +3.9 | 1.1 | 29-0-3 |
| DVF | +1.1 | 0.8 | 21-2-9 |
| DVF_v2 | -2.4 | 1.0 | 6-0-26 |

**Criterio: -0.6** · par guardado en `monitoreo/1302_striker.npz` + `_keeper.npz`

Striker en movimiento: **8 % de espaldas**, 68 % de frente (1 partido de 120 s contra v2.3).
