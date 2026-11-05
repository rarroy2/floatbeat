# Floatbeat — Especificación (v0.2, corregida)

> Reemplaza a la v0.1. Los cambios no son cosméticos: eliminan supuestos que no
> se sostienen en Linux real. Cada corrección está justificada en
> [`DECISIONS.md`](DECISIONS.md) y medida en [`BENCHMARKS.md`](BENCHMARKS.md).

## 1. Resumen

Widget de escritorio para Linux: ventana flotante, sin bordes, transparente y
siempre visible que muestra a un DJ ("cubito") reaccionando al audio del sistema
y a los metadatos MPRIS2. Objetivo: coste casi nulo cuando no hay música y una
estética propia, no un clon.

**Estado:** pre-alpha, fase de especificación. Sin código todavía.

## 2. Objetivos y no-objetivos

### Objetivos v0.1
- Ventana flotante arrastrable que funcione en X11 y en sesiones Wayland vía
  XWayland, sin crashes ni ventanas huérfanas.
- Animación ligada al **nivel de audio real**, no al estado de un reproductor.
- Metadatos y controles MPRIS2 sin polling.
- Consumo en reposo indistinguible de cero (sin repintados, sin stream abierto).
- Empaquetado Flatpak y AppImage reproducible en CI.

### No-objetivos v0.1
- Soporte nativo de layer-shell en GNOME (no existe; ver ADR-003).
- Vídeo, letras sincronizadas, ecualizador de 64 bandas, temas descargables.
- Port a Windows/macOS/iOS (solo se deja la arquitectura preparada).
- Presupuesto de 40 MB de RAM (imposible con Qt; ver ADR-002).

## 3. Stack definitivo

| Capa | Elección | Por qué |
| --- | --- | --- |
| Lenguaje | Python 3.12+ | Wheels de PySide6 6.12 disponibles hasta 3.14 |
| GUI | PySide6 6.12 (`QtWidgets`) | Un solo toolkit, portable a Windows |
| D-Bus | **QtDBus** (incluido en PySide6) | Señales nativas, mismo event loop, cero deps |
| Audio | **`parec` en subproceso** | `pulsectl` no lee muestras; `parec` es estable en PipeWire y PulseAudio |
| Análisis | `array` + `math` (RMS y 3–5 bandas) | `audioop` fue eliminado en Python 3.13 |
| Render | `QPainter` procedural | Sin Lottie, sin GIF, sin assets que envejezcan |
| Ajustes | `QSettings` (INI) | Cero dependencias, portable |
| Empaquetado | Flatpak (`io.qt.PySide.BaseApp`) + AppImage | Ver ADR-010 |

Dependencias de runtime: **PySide6** y el binario `parec` del sistema. Nada más.

## 4. Arquitectura

```
floatbeat/
├── __main__.py          # arranque, QApplication, single-instance
├── app.py               # PlayerState, máquina de estados, wiring
├── ui/
│   ├── widget.py        # ventana frameless/translúcida, drag, expandir
│   ├── avatar.py        # cubito + visor + barras (QPainter)
│   ├── panel.py         # metadata, controles, ajustes
│   └── theme.py         # paleta, radios, tipografía
├── audio/
│   ├── mpris.py         # cliente MPRIS2 sobre QtDBus
│   ├── capture.py       # parec → frames PCM normalizados
│   └── analysis.py      # RMS + energía por banda con suavizado
└── platform/
    ├── display.py       # detección X11/Wayland/XWayland, posición
    └── idle.py          # parada/arranque del render y del stream
```

### Flujo de datos

1. `MprisWatcher` se suscribe a `NameOwnerChanged` de `org.mpris.MediaPlayer2.*`
   y a `PropertiesChanged` del reproductor activo.
2. `AudioCapture` arranca `parec` contra el monitor del sink por defecto y emite
   bloques de ~1024 muestras mono a 44.1 kHz.
3. `analysis.py` calcula RMS y 4 bandas con filtros de primer orden (graves,
   medios-bajos, medios-altos, agudos) y aplica ataque/release asimétrico.
4. `app.py` decide el estado: `idle`, `vibing`, `mixing`, `paused`.
5. `ui` solo repinta si el estado visual cambió o hay nuevas amplitudes.

### Máquina de estados

```
        ┌──────────── pause/silencio > 1.5 s ────────────┐
        ▼                                                │
     ┌──────┐   audio > umbral   ┌────────┐  pico > 0.8  │
     │ idle │ ─────────────────▶ │ vibing │ ───────────▶ │ mixing │
     └──────┘                    └────────┘ ◀─────────── └────────┘
        ▲                            │        RMS < 0.6
        └──────── stream cerrado ────┘
```

`PlaybackStatus` **no** controla la animación (ver ADR-007). Solo decide si se
muestra el icono de pausa y si los controles están activos.

## 5. Fases y criterios de aceptación

### Fase 0 — Fundaciones
- Repo, licencia MIT, `.gitignore`, README, CI de lint (`ruff`) y tests.
- `pyproject.toml` con `requires-python = ">=3.12"`.
- **Aceptación:** `uv pip install -e .` en limpio y `ruff check` verde.

### Fase 1 — Ventana flotante y avatar procedural
- `QWidget` frameless, `WA_TranslucentBackground`, `WindowStaysOnTopHint`.
- Arrastre con `windowHandle().startSystemMove()` (funciona en X11 y Wayland).
- Avatar dibujado con `QPainter`: cubo biselado, visor único, 4 barras.
- Amplitudes alimentadas por un oscilador de prueba (`--demo`).
- **Aceptación:** 30 fps estables, ≤ 3 % de un núcleo, RSS ≤ 120 MB, drag
  correcto en GNOME Wayland y en X11.

### Fase 2 — MPRIS2
- Descubrimiento reactivo de reproductores; selección del activo.
- Lectura de `Metadata` (`xesam:title`, `xesam:artist`, `mpris:artUrl`) y
  `PlaybackStatus`.
- Controles `PlayPause`, `Next`, `Previous`, `Seek`.
- **Aceptación:** cambiar de canción en Spotify/VLC/Firefox actualiza la UI en
  < 100 ms sin polling; matar el reproductor no deja estado colgado.

### Fase 3 — Audio real
- `parec` contra `@DEFAULT_MONITOR@`, formato fijo s16le/44.1 kHz/mono.
- RMS + 4 bandas con suavizado; sin picos de GC (buffers preasignados).
- Maper de "silencio" a idle tras 1.5 s.
- **Aceptación:** latencia visual < 80 ms; CPU ≤ 3 %; al pausar, proceso `parec`
  termina y el timer se detiene.

### Fase 4 — Panel y ajustes
- Expansión animada al clic (150–220 ms, `QEasingCurve.OutCubic`).
- Título, artista, carátula (cacheada en disco), controles.
- Ajustes: posición, opacidad, "mirar al cursor", arranque automático.
- **Aceptación:** la ventana crece sin saltos y recuerda geometría entre
  sesiones; el modo "sin mirada" no instala el timer del cursor.

### Fase 5 — Empaquetado
- `org.freedesktop` metainfo, `.desktop`, icono SVG escalable.
- Flatpak con `io.qt.PySide.BaseApp`; permisos mínimos:
  `--socket=pulseaudio`, `--talk-name=org.mpris.MediaPlayer2.*`.
- AppImage con `python-appimage`; workflow de release en GitHub Actions.
- **Aceptación:** instalación limpia en Fedora y Ubuntu sin Python del sistema;
  el AppImage arranca con y sin FUSE (`--appimage-extract-and-run`).

## 6. Requisitos de plataforma

### X11 / XWayland
Soporte completo: posición absoluta, stacking, transparencia y drag.

### Wayland nativo
- `WindowStaysOnTopHint` **puede ser ignorado** por el compositor.
- La posición absoluta **no se puede fijar**; `move()` no es autoritativo.
- Se usa `startSystemMove()` para arrastrar y se guarda la posición como
  preferencia, aceptando que el compositor puede recolocar.
- En GNOME no hay layer-shell. Alternativa futura: plugin `wlr-layer-shell`
  solo para wlroots/KDE, nunca como requisito.
- Decisión por defecto: **forzar XWayland** (`QT_QPA_PLATFORM=xcb`) si el
  usuario no pide lo contrario, y documentarlo en la UI de ajustes.

### PipeWire / PulseAudio
`parec` funciona en ambos gracias a `pipewire-pulse`. Si no hay servidor de
audio, el widget arranca en modo "solo MPRIS" (barras planas) sin fallar.

## 7. Presupuesto de rendimiento

| Métrica | Presupuesto |
| --- | --- |
| RSS con ventana | ≤ 120 MB |
| PSS con ventana | ≤ 65 MB |
| CPU a 30 fps | ≤ 3 % de un núcleo |
| CPU en pausa | 0 repintados, timer parado |
| Latencia audio → píxel | < 80 ms |
| Arranque en frío | < 700 ms |

Técnicas obligatorias para cumplirlo:
- Cachear el cuerpo del avatar en un `QPixmap` y repintar solo las zonas sucias.
- Limitar `update()` a `QRect` de barras/ojos, no a toda la ventana.
- Bajar a 24 fps cuando el RMS es bajo; 30 fps solo en `mixing`.
- No usar `QGraphicsView`, ni QML, ni composición por capas extra.

## 8. Interacción

| Gesto | Acción |
| --- | --- |
| Arrastrar | Mover el widget (`startSystemMove`) |
| Clic | Expandir/colapsar el panel |
| Clic derecho | Menú: ajustes, siempre visible, salir |
| Rueda sobre el cubito | Volumen del reproductor activo |
| Clic en ojos (mantener) | "Scratch" visual, sin efecto en el audio |

## 9. Riesgos

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| GNOME Wayland ignora always-on-top | Alto | XWayland por defecto (ADR-003) |
| `parec` ausente o sin monitor | Medio | Fallback a modo MPRIS; mensaje en ajustes |
| Reproductores sin MPRIS | Medio | La animación depende del RMS, no de MPRIS |
| CPU alta por repintado completo | Medio | Dirty rects + caché de cuerpo |
| Parecido con Coucou | Medio | Silueta, paleta y animación propias; sin assets ajenos |
| PySide6 rompe en Python nuevo | Bajo | Pin de versión y CI con 3.12/3.13/3.14 |

## 10. Identidad

- **Nombre:** Floatbeat (sin "rarroy", sin referencia a Wayland/X11).
- **App ID:** `io.github.rarroy2.Floatbeat` (reverse-DNS real, requisito de
  Flathub; nunca `org.rarroy.*`).
- **Personaje:** cubo con bisel y visor horizontal continuo; paleta neón
  cian/magenta sobre grafito. Sin squircle, sin ojos redondos separados.
- **Licencia:** MIT para código; assets con licencia propia.

## 11. Futuro

- **Windows:** misma UI; MPRIS → GSMTC (`winsdk`) y `parec` → WASAPI loopback.
  La capa `platform/` ya aísla ambos.
- **Móvil:** fuera de alcance; no condiciona la arquitectura.
