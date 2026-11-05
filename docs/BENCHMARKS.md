# Benchmarks — por qué el presupuesto cambió

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
5. **La CPU a 30 fps está por encima del objetivo** (5.7–7.7 % frente a ≤ 3 %).
   Este es el trabajo de optimización real de la Fase 1, no un problema del
   lenguaje: el prototipo repinta la ventana completa con antialiasing en cada
   frame. Ver abajo.
6. **Wayland no permite saber dónde está la ventana.** `move(760, 380)` y luego
   `frameGeometry()` devuelven `(760, 380)` en ambos backends, pero en Wayland
   ese valor es la intención en caché del cliente: el compositor decide la
   posición real y no hay API para consultarla. En XWayland sí es autoritativo.

## Backlog de optimización (Fase 1)

- [ ] Cachear el cuerpo estático del cubo en un `QPixmap` y dibujarlo con
      `drawPixmap`, dejando para el frame solo ojos y barras.
- [ ] Repintar por regiones sucias (`update(QRect)`) en vez de la ventana entera.
- [ ] Bajar a 24 fps cuando el RMS es bajo; 30 fps solo en picos.
- [ ] Evitar `Antialiasing` en las barras (rectángulos redondeados ya se ven
      bien) y limitarlo al cubo/visor.
- [ ] Medir de nuevo con `Qsg`/RHI si el repintado parcial no basta; no se
      adopta OpenGL por defecto porque añade superficie y memoria.
- [ ] Repetir la medición con 600×260 (panel expandido) para conocer el techo.

## Reproducir

El prototipo vive fuera del repo a propósito (es un experimento, no código de
producción). Cuando exista `src/floatbeat`, el benchmark se convertirá en un
script versionado dentro de `tools/bench.py` para que estos números se puedan
repetir en CI y en otras máquinas.
