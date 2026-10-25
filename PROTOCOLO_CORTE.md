# Protocolo de corte de internet (DVF)

Si se corta internet, la sesión con Claude se cae, pero **el entrenamiento y los benchmarks son
locales y siguen corriendo**. Para que no se pierda nada y se pueda retomar ordenado, queda
corriendo un vigilante: `scripts/protocolo_corte.py --vigilar`.

## Qué hace el vigilante

Cada 60 s prueba la conexión. Si se corta (dos pruebas seguidas, para no reaccionar a un
parpadeo) y cuando vuelve, ejecuta **"asegurar"**, que no frena ni toca ningún proceso:

1. **Foto del estado** → `models/runs/_estado/ESTADO.md`: procesos vivos (entrenamientos,
   supervisores, evaluadores, benchmarks, partidos en ventana) y, por corrida: fases, horas,
   última fase, último guardado, hora límite y última línea del log.
2. **Respaldo liviano** → `models/runs/_estado/respaldo_<fecha>/`: `run.json`, `until.txt` y
   `supervisor.log` de cada corrida, más `CHANGELOG.md` y `PLAN_ENTREGA.md`. Los modelos `.npz`
   ya se guardan solos cada 20 iteraciones (escritura atómica) y quedan en `checkpoints/`.
3. **Limpieza de lo corrupto**:
   - borra los temporales `*.tmp` de más de 5 minutos (restos de guardados interrumpidos);
   - prueba abrir los `.npz` principales, los checkpoints de las últimas 48 h y los resultados
     `.jsonl`. Lo que no abre se **mueve** a `models/_cuarentena/<fecha>/`: no se borra
     directamente, por si hay que revisarlo;
   - un `run.json` dañado solo se avisa (la corrida lo necesita); hay copias en los respaldos.
4. Todo queda anotado en `models/runs/_estado/protocolo.log`.

## Para retomar

1. Abrir la sesión de Claude y pedirle: **"leé `models/runs/_estado/ESTADO.md`"**.
2. Si un entrenamiento murió, se relanza y retoma solo desde su último guardado:
   `powershell -ExecutionPolicy Bypass -File scripts\lanzar_corrida.ps1 -Run <corrida> -Desacoplado`
3. Lo que haya ido a cuarentena se revisa y, si no sirve, se borra a mano.

## Comandos

```
python scripts/protocolo_corte.py --ahora      # asegurar una vez, a mano
python scripts/protocolo_corte.py --vigilar    # vigilante (ya queda corriendo)
```

El vigilante corre **desacoplado** de la app (creado por WMI, prioridad baja): sigue vivo aunque
se cierre Claude. Su PID está en `models/runs/_estado/vigilante_pid.txt`. **Si la PC se reinicia
o se apaga, el vigilante no vuelve solo**: hay que lanzarlo de nuevo (o pedirle a Claude que lo
lance).
