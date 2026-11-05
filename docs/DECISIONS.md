# Decisiones de arquitectura (ADR)

Registro corto de las decisiones que cambian el diseño, con la evidencia que las
sostiene. Si algo aquí deja de ser cierto, se añade un ADR nuevo; no se reescribe
la historia.

---

## ADR-001 — PySide6 6.12 sobre CPython 3.12+

**Estado:** aceptada · 2026-11-05

**Contexto:** se necesita una UI transparente y siempre visible, portable a
Windows en el futuro, con bajo consumo y un solo lenguaje.

**Decisión:** Python 3.12+ y PySide6 6.12 (`QtWidgets`, no QML).

**Evidencia:** PySide6 6.12.0 instala y funciona en CPython 3.14.8. Un widget
completo cuesta 83 MB RSS / 53 MB PSS (ver `BENCHMARKS.md`). `uv` resuelve e
instala el stack en segundos.

**Consecuencias:** se renuncia a un binario de < 20 MB y a arranques de ~100 ms.
A cambio: desarrollo rápido, un toolkit para Linux y Windows, y `QtDBus`
gratis.

**Alternativas descartadas:** Rust + gtk4-layer-shell (mejor RAM, mucho más
trabajo y sin QtDBus); C++/Qt (mismo coste de RAM, peor velocidad de iteración);
Electron/Tauri (peor RAM y transparencia).

---

## ADR-002 — El presupuesto de RAM es ≤ 120 MB, no < 40 MB

**Estado:** aceptada · 2026-11-05

**Contexto:** la especificación original exigía `< 40 MB RAM`.

**Decisión:** presupuesto de ≤ 120 MB RSS / ≤ 65 MB PSS con ventana visible.

**Evidencia:** `import PySide6.QtWidgets` = 43.8 MB RSS / 31.9 MB PSS sin
ventana. Con ventana: 82.8 MB / 53.3 MB. Ninguna optimización de widget puede
bajar de lo que cuesta cargar Qt.

**Consecuencias:** el README comunica una cifra real y medible. Si algún día 40
MB es requisito duro, hay que cambiar de stack (ADR nuevo), no de widget.

---

## ADR-003 — XWayland por defecto; layer-shell solo como extra

**Estado:** aceptada · 2026-11-05

**Contexto:** el concepto exige posición libre y "siempre encima". En Wayland
un cliente normal no puede fijar su posición ni su orden de apilamiento.

**Decisión:** en sesiones Wayland, arrancar con `QT_QPA_PLATFORM=xcb` por
defecto. Ofrecer Wayland nativo como opción avanzada. Reservar `wlr-layer-shell`
para un plugin futuro en wlroots/KDE, nunca como requisito.

**Evidencia:** medido en GNOME/Wayland: `move(760, 380)` + `frameGeometry()`
devuelve `(760, 380)` en XWayland y en Wayland nativo, pero en Wayland es un
valor en caché del cliente; el compositor no garantiza esa posición. GNOME no
implementa `wlr-layer-shell`.

**Consecuencias:** HiDPI bajo XWayland puede requerir `QT_SCALE_FACTOR`; se
documenta. El drag usa `startSystemMove()`, que funciona en ambos.

**Alternativas descartadas:** exigir KDE/wlroots; usar un panel del sistema en
vez de una ventana flotante (rompe el concepto).

---

## ADR-004 — QtDBus en lugar de `dasbus` / `dbus-python`

**Estado:** aceptada · 2026-11-05

**Contexto:** MPRIS2 necesita señales `PropertiesChanged` y llamadas asíncronas.

**Decisión:** `PySide6.QtDBus`.

**Evidencia:** ya viene con PySide6; comparte el event loop de Qt (sin hilos ni
traducciones de tipos); `dasbus` no publica releases desde 2021 y `dbus-python`
requiere cabeceras y complica el Flatpak.

**Consecuencias:** el código de MPRIS queda ligero y testeable con dobles de
`QDBusConnection`. Menos una dependencia en el manifiesto.

---

## ADR-005 — Captura de audio con `parec`, no con `pulsectl`

**Estado:** aceptada · 2026-11-05

**Contexto:** se necesita la señal del monitor del sink por defecto.

**Decisión:** lanzar `parec --device=@DEFAULT_MONITOR@ --format=s16le
--rate=44100 --channels=1` y leer bloques de 1024 muestras (≈ 23 ms).

**Evidencia:** `pulsectl` es una API de control (volumen, mute, routing); no
expone buffers PCM. `QAudioSource` no lista monitores de forma fiable. `parec`
funciona igual sobre PipeWire (vía `pipewire-pulse`) y sobre PulseAudio puro, y
se puede matar limpiamente al pausar.

**Consecuencias:** el formato se fija a s16le/44.1 kHz/mono: menos CPU y cero
negociación. Si `parec` no existe o no hay monitor, la app arranca en modo
"solo MPRIS" sin fallar.

**Alternativas descartadas:** PipeWire nativo vía `ctypes` (mucho código y
bindings frágiles); `soundcard` (depende de PortAudio, más peso).

---

## ADR-006 — Avatar procedural con `QPainter`; ni Lottie ni GIF

**Estado:** aceptada · 2026-11-05

**Contexto:** el personaje debe verse nítido sobre el escritorio y escalar.

**Decisión:** dibujar el cubo, el visor y las barras en `paintEvent` con
`QPainterPath`. Sin assets de animación.

**Evidencia/razón:** los GIF tienen transparencia binaria y bordes dentados al
componerse sobre el escritorio; Lottie exige QML + QtLottie y añade una capa de
render. Lo procedural pesa 0 MB de assets, escala con `devicePixelRatio` y
permite modular la animación con el RMS directamente.

**Consecuencias:** el diseño vive en código; los cambios de estilo son cambios
de constantes. El estado estático se cachea en `QPixmap` para cumplir CPU.

---

## ADR-007 — El RMS manda; MPRIS solo informa y controla

**Estado:** aceptada · 2026-11-05

**Contexto:** la especificación original animaba solo si
`PlaybackStatus == "Playing"`.

**Decisión:** la animación se activa con energía de audio por encima de un
umbral. MPRIS aporta título, artista, carátula y controles.

**Evidencia/razón:** hay audio sin MPRIS (juegos, llamadas, apps antiguas) y
MPRIS sin audio real (un vídeo pausado que sigue sonando por otra pestaña). El
RMS describe lo que el usuario oye; el estado del reproductor no.

**Consecuencias:** el modo `paused` visual se deriva de 1.5 s de silencio, no de
la propiedad `PlaybackStatus`. Ambos se muestran por separado en la UI.

---

## ADR-008 — Identidad: `io.github.rarroy2.Floatbeat`, MIT

**Estado:** aceptada · 2026-11-05

**Contexto:** la v0.1 usaba `org.rarroy.DJWidget`, con un nombre que se había
decidido eliminar.

**Decisión:** app ID `io.github.rarroy2.Floatbeat`; licencia MIT; sin "rarroy"
ni referencias a Wayland/X11 en el nombre visible.

**Evidencia/razón:** Flathub exige reverse-DNS verificable; el namespace de
GitHub es la vía sin dominio propio. MIT es compatible con el ecosistema del que
se toma inspiración y maximiza adopción.

**Consecuencias:** el `.desktop`, el metainfo y el manifest usan ese ID. Los
assets tendrán su propio archivo de licencia.

---

## ADR-009 — Nada de `audioop`; `array` + `math`

**Estado:** aceptada · 2026-11-05

**Contexto:** `audioop` se eliminó en Python 3.13 (PEP 594).

**Decisión:** calcular RMS con `array("h")` y sumas en Python; bandas con
filtros IIR de primer orden.

**Consecuencias:** compatible con 3.12–3.14 sin dependencias. Si el perfil de
CPU lo exige, `numpy` será una extra opcional, nunca un requisito (cuesta ~20 MB
RSS).

---

## ADR-010 — Flatpak con `io.qt.PySide.BaseApp`; AppImage con `python-appimage`

**Estado:** aceptada · 2026-11-05

**Contexto:** hay que distribuir sin depender del Python del sistema.

**Decisión:** Flatpak sobre `io.qt.PySide.BaseApp` (no sobre
`org.kde.Platform` + `pip install PySide6`), y AppImage generado con
`python-appimage` en CI.

**Evidencia/razón:** el BaseApp ya trae PySide6 compilado; instalar el wheel
dentro del manifest multiplica el tamaño y el tiempo de build. `python-appimage`
empaqueta wheels manylinux sin pelear con `linuxdeploy-plugin-qt`.

**Consecuencias:** el manifest declara `--socket=pulseaudio` y
`--talk-name=org.mpris.MediaPlayer2.*`. El AppImage se prueba en Fedora y Ubuntu,
con y sin FUSE.

---

## ADR-011 — Originalidad frente a Coucou

**Estado:** aceptada · 2026-11-05

**Contexto:** la inspiración declarada es Coucou (MIT en código; nombre,
personaje y sonidos reservados). Su personaje es un squircle con ojos grandes
que sigue el cursor y baila al ritmo de Spotify.

**Decisión:** no reutilizar código, arte, sonidos ni nombres. Silueta distinta
(cubo biselado con visor continuo), paleta propia (cian/magenta sobre grafito),
animación ligada al RMS y no a un reproductor concreto.

**Consecuencias:** el README acredita la inspiración de forma explícita. Ante
duda de diseño, se elige lo que se aleje del referente, no lo que sea más fácil
de copiar.

---

## ADR-012 — Render en dos capas y presupuesto de CPU del 7 %

**Estado:** aceptada · 2026-11-06

**Contexto:** la Fase 1 exigía ≤ 3 % de un núcleo a 30 fps. La primera
implementación gastaba 12.8 % y el prototipo de la fase 0, 7.3 %.

**Decisión:** cachear cuerpo y placa del visor (glow incluido) como `QImage`; un
solo `update()` por frame; sin rotación del visor; presupuesto de ≤ 7 %.

**Evidencia:** el pintado bajó de 3.65 a 1.33 ms por frame y la CPU a 6.3–6.5 %
con 30 fps reales, 0.00 % en pausa. El suelo del stack (solo cuerpo y bucle de
eventos) es ~1.1 ms/frame, o 2.7 % a 25 fps: 3 % no es alcanzable optimizando el
dibujo.

**Consecuencias:** el README y la spec comunican 7 %. Bajar de ahí exigiría
cambiar el modelo de ventana (surface propia en Wayland) o el toolkit, no
micro-optimizar el widget.

**Alternativas descartadas:** rotar la placa del visor (0.65 ms/frame por 2.6°);
tres regiones de daño separadas (más caras que una sola); `QOpenGLWidget`
(añade superficie y memoria para un ahorro que no se midió).

---

## ADR-013 — Posición anclada al área de trabajo, no dentro del panel

**Estado:** aceptada · 2026-11-06

**Contexto:** el requisito es que el widget aparezca arriba, junto al reloj, en la
posición donde el usuario tenga su barra.

**Decisión:** anclar a `QScreen.availableGeometry()` (el área de trabajo, que el
escritorio ya recorta para excluir paneles y docks), con anclas configurables
(arriba/abajo × izquierda/derecha) y margen de 24 px. Por defecto, arriba derecha.

**Evidencia:** en esta máquina, GNOME expone `geometry=1920x1080` y
`availableGeometry=1920x1048` en `y=32`: el panel superior son exactamente 32 px
de strut. Anclar al área de trabajo coloca el widget en `(1676, 56)`, justo bajo
la barra, sin código específico de GNOME. Con el panel abajo o a la izquierda el
mismo cálculo lo sigue.

**Consecuencias:** no se necesita extensión de GNOME, plasmoides de KDE ni plugin
de XFCE. El widget no puede *vivir dentro* de la barra: eso exigiría tres
codebases distintas. Se documenta como limitación consciente en `docs/USAGE.md`.

**Alternativas descartadas:** detectar el panel por nombre de DE (frágil y
duplica lógica); integración por plugin (fuera de alcance de un widget Qt);
`layer-shell` con zona exclusiva (GNOME no lo implementa, ADR-003).

---

## ADR-014 — Documentación en el repo, no en la wiki de GitHub

**Estado:** aceptada · 2026-11-06

**Contexto:** se barajó una wiki (de GitHub o una web aparte) para uso, dudas y
FAQ.

**Decisión:** `docs/` dentro del repositorio, con `README.md` como portada,
`docs/USAGE.md` para usuarios y `docs/SPEC.md` / `DECISIONS.md` / `BENCHMARKS.md`
para ingeniería. Si más adelante hace falta una web, se publica `docs/` con
MkDocs Material en GitHub Pages.

**Evidencia/razón:** la wiki de GitHub es un repositorio git separado: no se
revisa en los PR, no viaja con los tags, no se puede validar en CI y se
desincroniza del código que documenta. Con docs-as-code, un cambio de
comportamiento y su documentación van en el mismo commit, y el enlace
`docs/USAGE.md` funciona igual en el repo, en un clon offline y en la web
generada.

**Consecuencias:** una sola fuente de verdad y cero mantenimiento duplicado. La
wiki queda reservada, si acaso, para notas comunitarias que no dependan del
código.

**Alternativas descartadas:** wiki de GitHub (duplica y envejece); web propia
desde el día uno (coste de mantenimiento sin usuarios todavía).
