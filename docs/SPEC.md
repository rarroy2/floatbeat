# Floatbeat — Especificación (v0.3, extensión)

> Sustituye a la spec v0.2 de la ventana flotante. El cambio está justificado en
> [`DECISIONS.md`](DECISIONS.md) (ADR-015) y el código anterior queda en el tag
> `v0.1.0`.

## 1. Resumen

DJ diminuto en la barra superior de GNOME, con un motor Python que aporta audio y
MPRIS, y un popover Qt translúcido con la versión grande, la portada y los
controles.

## 2. Por qué una extensión

Tres requisitos incompatibles con una ventana normal:

1. estar siempre visible,
2. no tapar información (barra de título, controles de ventana),
3. no ocultarse.

La única zona reservada del escritorio es el panel. Un cliente no puede dibujar
dentro de él, así que la única vía es una extensión. La ventana flotante de
v0.1.0 se conserva como histórico y como prueba del presupuesto de render.

## 3. Arquitectura

```
┌──────────────────────────────┐
│ GNOME Shell (GJS + Cairo)    │
│  actor 56×38 en el panel     │  ← dibuja, anima, detecta clic
└──────────────┬───────────────┘
               │ D-Bus (niveles + ShowPopover)
┌──────────────▼───────────────┐
│ Motor Python                 │
│  MPRIS2 (jeepney)            │  ← título, artista, portada, controles
│  audio (demo → parec)        │  ← RMS + 4 bandas
└──────────────┬───────────────┘
               │ mismo proceso
┌──────────────▼───────────────┐
│ Popover Qt translúcido       │
│  avatar grande + portada     │
│  título/artista + controles  │
└──────────────────────────────┘
```

- La extensión no depende de Python para existir: sin motor muestra el estado
  apagado.
- El motor publica `Frame(playing, {level, bands})` y expone `ShowPopover(x, y)`.
- El popover se abre centrado bajo el reloj y se cierra al hacer clic fuera o con
  Escape.

## 4. Estados del personaje

| Estado | Ojos | Barras | Animación |
| --- | --- | --- | --- |
| Apagado (sin música) | Grises | Ninguna | Ninguna; timer parado |
| Reproduciendo | Cian con brillo | 5 barras activas | 25 fps |
| Popover abierto | Igual que el estado de fondo | Igual | El popover no cambia el estado |

El estado se deriva de `PlaybackStatus` de MPRIS y/o del nivel de audio. Sin
reproductor y sin señal: apagado.

## 5. Fases

### Fase 1 — Extensión (hecha)
- Actor en el panel, posicionado por la allocation del reloj.
- Dibujo Cairo del avatar mini, con 6 px de overflow.
- Animación de prueba a 25 fps y clic registrado.
- **Aceptación:** carga sin errores en GNOME 50.6, se ve nítido, no rompe el shell.

### Fase 2 — Motor MPRIS + D-Bus (hecha)
- Descubrimiento y estado vía `GetAll` de MPRIS (jeepney; QtDBus no puede
  demarshalar `a{sv}` en PySide6).
- Servicio `io.github.rarroy2.Floatbeat.Engine` con `Frame` y `ShowPopover`
  implementado como `QDBusVirtualObject` para conservar el nombre de interfaz.
- **Verificado:** Spotify (título, artista, álbum, carátula, posición, controles)
  y la cadena extensión → motor en un shell headless (`playing=true/false`).

### Fase 3 — Popover (hecha)
- Ventana frameless translúcida de 430×250 bajo el reloj.
- Avatar grande, portada, título/artista/álbum, progreso y controles.
- **Verificado:** render offscreen con portada real y placeholder; el popover se
  abre con `ShowPopover` y se cierra con clic fuera o Escape.

### Fase 4 — Audio real
- `parec` contra el monitor del sink por defecto.
- RMS + 4 bandas; silencio → estado apagado y parada del stream.
- **Aceptación:** latencia < 80 ms, CPU del motor < 3 % de un núcleo, 0 % en
  silencio.

### Fase 5 — Empaquetado
- Extensión: zip y publicación en extensions.gnome.org.
- Motor: unidad systemd de usuario o arranque bajo demanda.
- **Aceptación:** instalación limpia en Fedora y Ubuntu con GNOME 45–50.

## 6. Rendimiento

| Pieza | Presupuesto |
| --- | --- |
| Extensión (25 fps, 56×38) | < 0.5 % de un núcleo; 0 % en apagado |
| Motor sin popover | 0.50 % y ~59 MB con el plugin offscreen (~85 MB con xcb) |
| Motor reproduciendo | 2.17 % de un núcleo |
| Popover abierto | Repinta solo la zona del avatar a 25 fps |
| Latencia audio → píxel | < 80 ms (pendiente de la captura real) |

La extensión debe parar el `GLib.timeout` cuando el estado es apagado y repintar
solo al cambiar de estado. El popover no debe mantener un timer propio: consume
los frames del motor.

## 7. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El panel recorta el overflow en otra versión de GNOME | Detectar altura y ajustar a 32 px si hace falta |
| APIs privadas (`statusArea.dateMenu`, `panelBox`) | Fallback al centro del monitor; probar 45–50 |
| Recarga en desarrollo exige logout | Shell headless para validar y render Cairo aparte |
| El motor siempre encendido consume RAM | Medirlo; valorar motor sin Qt si molesta |
| La extensión rompe el shell | try/catch en draw y callbacks; estado apagado si falla |

## 8. Repositorio

- `main`: extensión + motor + documentación actual.
- Tag `v0.1.0`: app flotante original, conservada como historia.
- El manifiesto Flatpak/AppImage del plan anterior queda descartado.
