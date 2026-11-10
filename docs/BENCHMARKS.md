# Benchmarks — por qué el presupuesto cambió

> **Histórico.** Estos números describen la app de ventana flotante de v0.1.0,
> conservada en el tag `v0.1.0`. El proyecto actual es una extensión de GNOME
> Shell; sus métricas se añadirán aquí cuando el motor y el popover existan.
> La conclusión sigue siendo válida: Qt no baja de ~44 MB de RSS ni de 3 % de un
> núcleo a 30 fps, y por eso el presupuesto se corrigió.

Fecha: 2026-11-05. Todos los números son de esta máquina, no de una hoja de
cálculo.

## Metodología

Prototipo desechable en `/tmp` (no forma parte del repo): `QWidget` de 220×220,
frameless, `WA_TranslucentBackground`, `WindowStaysOnTopHint | Tool`, con
`QPainter` + antialiasing dibujando un cubo, dos ojos y 5 barras a 30 fps
(`QTimer` preciso de 33 ms). Sin audio real: amplitudes por oscilador.

- RSS: `VmRSS` de `/proc/self/status`.
- PSS: `Pss` de `/proc/self/smaps_rollup` (cuenta las páginas compartidas de Qt
  de forma proporcional, es el número justo para "cuánto cuesta esta app").
- CPU: `utime + stime` de `/proc/self/stat` dividido por el tiempo de pared;
  porcentaje de **un** núcleo.
- Se midió tras 6 s animando y de nuevo tras 4 s con el timer parado.
- Se ejecutó dos veces: `QT_QPA_PLATFORM=xcb` (XWayland) y
  `QT_QPA_PLATFORM=wayland`.

Hardware/entorno: 12 hilos, 15.8 GB RAM, 1920×1080 @ 1×, GNOME en Wayland,
PySide6 6.12.0 sobre CPython 3.14.8, sin GPU dedicada en el render de Qt
(composición por software para la superficie del widget).

## Resultados

| Métrica | XWayland | Wayland nativo |
| --- | --- | --- |
| RSS tras `import PySide6.QtWidgets` | 43.8 MB | 44.0 MB |
| PSS tras el import | 31.9 MB | 31.8 MB |
| RSS tras `QApplication` | 80.0 MB | 79.5 MB |
| RSS con ventana visible | 82.8 MB | 82.9 MB |
| PSS con ventana visible | 53.3 MB | 53.3 MB |
| FPS efectivos (timer 33 ms) | 30.3 | 30.7 |
| CPU animando | 7.30 % | 8.07 % |
| CPU en reposo (timer parado) | 0.240 % | 0.000 % |
| CPU steady-state 30 fps | 7.67 % | 5.67 % |

## Lectura

1. **40 MB de RAM es imposible con Qt.** Antes de crear una sola ventana, el
   import ya ocupa 43.8 MB RSS. No es una cuestión de optimizar el widget: es el
   coste de cargar QtCore + QtGui + QtWidgets + el plugin de plataforma.
2. **El coste real del widget es pequeño.** Pasar de `QApplication` a ventana
   visible solo añade ~3.3 MB RSS (80.0 → 82.8). El presupuesto razonable es
   ≤ 120 MB RSS, con 83 MB ya medidos.
3. **PSS ≈ 53 MB** es la cifra honesta para un gestor de memoria: gran parte de
   ese espacio son bibliotecas de Qt compartidas con otras apps.
4. **El reposo sí llega a cero.** Con el timer parado y sin stream de audio, el
   proceso no despierta. Esto valida el requisito central del proyecto.
5. **El prototipo costaba 5.7–7.7 % de CPU a 30 fps.** La implementación de la
   Fase 1 lo deja en 6.3–6.5 % con 30 fps reales (1.33 ms de pintado por frame).
   3 % no es alcanzable en este stack; el presupuesto se corrigió a 7 %.
6. **Wayland no permite saber dónde está la ventana.** `move(760, 380)` y luego
   `frameGeometry()` devuelven `(760, 380)` en ambos backends, pero en Wayland
   ese valor es la intención en caché del cliente: el compositor decide la
   posición real y no hay API para consultarla. En XWayland sí es autoritativo.

## Fase 1: implementación real

Una vez escrito el widget, mismas condiciones (220×220, demo de 124 BPM, 30 fps):

| Métrica | Valor |
| --- | --- |
| RSS animando | 85.6 MB |
| PSS animando | 55.9 MB |
| CPU a 30 fps | 6.3–6.5 % de un núcleo |
| `paintEvent` | 1.33 ms por frame |
| RSS en pausa | 85.9 MB |
| CPU en pausa | 0.00 % |

Desglose del primer `paintEvent` medido, antes de optimizar:

| Pieza | Coste |
| --- | --- |
| Visor (glow 7 px + AA + rotación) | 2.5 ms |
| Barras (10 rectángulos redondeados) | 0.3 ms |
| LED | 0.05 ms |
| Blit del cuerpo cacheado | 0.28 ms |

### Iteraciones

| Versión | paint | CPU |
| --- | --- | --- |
| Primera (glow + rotación + 3 updates) | 3.65 ms | 12.8 % a 25 fps |
| Placa del visor cacheada en `QImage` | 2.13 ms | 7.6 % a 25 fps |
| Sin rotación del visor (mirada lateral) | 1.48 ms | 5.7 % a 25 fps |
| Ojos sólidos + histéresis del timer | 1.33 ms | 6.4 % a 30 fps |

La última fila sube de CPU porque por fin corre a 30 fps reales: el coste **por
frame** bajó de 3.65 a 1.33 ms, un 64 % menos.

### Hallazgos de la fase 1

- El trazo de glow de 7 px con antialiasing era el 68 % del coste de pintado.
  Cachearlo como imagen lo reduce a un blit.
- Rotar el visor 2.6° cuesta 0.65 ms/frame. Se sustituyó por un desplazamiento
  horizontal de los ojos según el balance espectral.
- `setInterval()` en cada frame reinicia el `QTimer` y la tasa cae a ~25 fps. Con
  histéresis (1 s de silencio antes de bajar a 24 fps) se recuperan 30.2 fps.
- El suelo del stack es ~1.1 ms/frame solo con el cuerpo y el bucle de eventos
  (2.7 % a 25 fps). **3 % a 30 fps no es alcanzable**; el presupuesto se fijó en
  7 % con esta evidencia.

## Backlog de optimización (Fase 1)

- [x] Cachear el cuerpo estático en una imagen y dibujarlo con un blit.
- [x] Cachear la placa del visor (glow incluido) en lugar de trazar 7 px con AA
      cada frame: 3.65 → 2.13 ms.
- [x] Eliminar la rotación del visor (2.6° costaba 0.65 ms) y sustituirla por
      mirada lateral de los ojos.
- [x] Un solo `update()` por frame en vez de tres.
- [x] Histéresis en el intervalo del timer (el `setInterval` por frame hundía la
      tasa a 25 fps).
- [ ] Repetir la medición con 600×260 (panel expandido) para conocer el techo.
- [ ] Medir con `devicePixelRatio = 2` (HiDPI): el coste de pintado se multiplica
      por 4 en píxeles.
- [ ] Convertir estas cifras en `tools/bench.py` versionado, ejecutable en CI.

## Lo que no funcionó

- **Tres `update()` por frame** (visor, barras, LED) en lugar de uno: 12.8 % de
  CPU frente a 13.3 %. Cada actualización cuesta su propio evento de pintado y
  la ganancia de área no compensa.
- **`QImage` en vez de `QPixmap`** para el cuerpo: sin cambio medible. El
  `QPainter` de widgets ya rasteriza; el cuello de botella era el trazo, no el
  blit.
- **Bajar a 24 fps** no compensa: ahorra ~1.3 puntos de CPU y se nota en la
  animación. Se mantiene como modo silencioso, no como ajuste general.

## Reproducir

Estos comandos corresponden a la app de v0.1.0:

```bash
git checkout v0.1.0
python -m floatbeat                 # demo en marcha
FLOATBEAT_STATS=1 python -m floatbeat   # fps / paints/s / CPU / paint ms / RSS
python tools/preview.py             # PNG sin ventana (offscreen)
```

El prototipo original de la fase 0 vivió fuera del repo a propósito. Las cifras
de arriba salen del binario real con `FLOATBEAT_STATS=1`, no de un benchmark
sintético.
