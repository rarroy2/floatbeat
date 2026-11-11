// Floatbeat — GNOME Shell extension.
//
// A small DJ actor anchored to the top panel, left of the clock. It lives in the
// shell's UI group (not inside the panel's box layout) so it can overflow a few
// pixels below the bar.
//
// The extension is only a renderer: the Python engine publishes
// `Frame(playing, {level, bands})` over D-Bus and the actor goes idle (grey
// eyes, no equaliser, timer stopped) when nothing is playing. Clicking the
// character asks the engine to open the translucent popover.

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {DESIGN_WIDTH, OVERFLOW, drawAvatar} from './avatar.js';

const FRAME_MS = 40;
const GAP = 6;
const BUS_NAME = 'io.github.rarroy2.Floatbeat.Engine';
const OBJECT_PATH = '/io/github/rarroy2/Floatbeat/Engine';

const ENGINE_XML = `
<node>
  <interface name="io.github.rarroy2.Floatbeat.Engine">
    <method name="ShowPopover">
      <arg type="i" direction="in"/>
      <arg type="i" direction="in"/>
    </method>
    <method name="HidePopover"/>
    <signal name="Frame">
      <arg type="b"/>
      <arg type="a{sv}"/>
    </signal>
  </interface>
</node>`;

let EngineProxy = null;
try {
    EngineProxy = Gio.DBusProxy.makeProxyWrapper(ENGINE_XML);
} catch (error) {
    console.error(`[floatbeat] proxy setup failed: ${error}`);
}

export default class FloatbeatExtension extends Extension {
    enable() {
        this._phase = 0;
        this._playing = false;
        this._level = 0;
        this._bands = [];
        this._timeout = 0;
        this._proxy = null;
        this._proxyReady = false;
        this._signals = [];

        this._actor = new St.DrawingArea({
            style_class: 'floatbeat-avatar',
            reactive: true,
            track_hover: true,
        });
        this._actor.set_size(DESIGN_WIDTH, this._panelHeight() + OVERFLOW);
        this._actor.connect('destroy', () => {
            this._actor = null;
        });
        this._actor.connect('repaint', area => this._draw(area));
        this._actor.connect('button-press-event', () => {
            this._openPopover();
            return Clutter.EVENT_STOP;
        });

        Main.layoutManager.uiGroup.add_child(this._actor);
        this._reposition();

        this._connect(Main.panel, 'notify::height', () => {
            this._actor?.set_height(this._panelHeight() + OVERFLOW);
            this._reposition();
        });
        this._connect(Main.panel, 'notify::visible', () => {
            if (this._actor)
                this._actor.visible = Main.panel.visible;
        });
        this._connect(Main.panel.statusArea.dateMenu, 'notify::allocation',
            () => this._reposition());
        this._connect(Main.layoutManager.panelBox, 'notify::translation-y', () => {
            if (this._actor)
                this._actor.visible = Main.layoutManager.panelBox.translation_y >= 0;
        });
        if (Main.layoutManager.startupComplete)
            this._reposition();
        else
            this._connect(Main.layoutManager, 'startup-complete', () => this._reposition());

        this._nameWatcher = Gio.bus_watch_name(
            Gio.BusType.SESSION,
            BUS_NAME,
            Gio.BusNameWatcherFlags.NONE,
            () => this._connectEngine(),
            () => this._disconnectEngine());

        this._log(`enabled panel=${this._panelHeight()}`);
    }

    disable() {
        if (this._timeout) {
            GLib.source_remove(this._timeout);
            this._timeout = 0;
        }
        if (this._nameWatcher) {
            Gio.bus_unwatch_name(this._nameWatcher);
            this._nameWatcher = 0;
        }
        this._proxy = null;
        this._proxyReady = false;
        for (const [object, id] of this._signals) {
            if (object)
                object.disconnect(id);
        }
        this._signals = [];
        const actor = this._actor;
        this._actor = null;
        try {
            actor?.destroy();
        } catch {
            // Already disposed by the shell.
        }
    }

    // -- drawing ------------------------------------------------------------

    _draw(area) {
        const cr = area.get_context();
        try {
            const [width, height] = area.get_surface_size();
            drawAvatar(cr, width, height, this._phase, this._level, this._playing);
        } catch (error) {
            this._log(`draw failed: ${error}`);
        } finally {
            cr.$dispose();
        }
    }

    _panelHeight() {
        return Math.max(Main.panel.height, 24);
    }

    _reposition() {
        try {
            if (!this._actor)
                return;
            const monitor = Main.layoutManager.primaryMonitor;
            const monitorWidth = monitor ? monitor.width : 1280;
            const monitorX = monitor ? monitor.x : 0;
            const monitorY = monitor ? monitor.y : 0;
            const clock = Main.panel.statusArea.dateMenu;
            const [panelX, panelY] = Main.panel.get_transformed_position();
            let clockX = NaN;
            if (clock) {
                const [x] = clock.get_transformed_position();
                if (Number.isFinite(x))
                    clockX = x;
            }
            // At enable time the panel may not be allocated yet; fall back to
            // the centre of the primary monitor and reposition on startup.
            const x = Number.isFinite(clockX) && clockX > 0
                ? clockX - this._actor.width - GAP
                : monitorX + Math.round(monitorWidth / 2) - this._actor.width - GAP;
            const y = Number.isFinite(panelY) ? panelY : monitorY;
            this._actor.set_position(Math.max(0, Math.round(x)), Math.round(y));
        } catch {
            // Actor disposed during teardown.
        }
    }

    // -- engine -------------------------------------------------------------

    _connectEngine() {
        this._log('engine appeared');
        if (!EngineProxy || this._proxy)
            return;
        this._proxy = new EngineProxy(Gio.DBus.session, BUS_NAME, OBJECT_PATH,
            (proxy, error) => {
                if (error) {
                    this._log(`proxy failed: ${error}`);
                    this._proxy = null;
                    this._proxyReady = false;
                    return;
                }
                this._proxyReady = true;
                this._log('proxy ready');
                proxy.connectSignal('Frame', (p, sender, params) => {
                    const [playing, data] = params;
                    let info = {};
                    try {
                        info = data ? data.deepUnpack() : {};
                    } catch {
                        info = {};
                    }
                    this._onFrame(Boolean(playing), info);
                });
            });
    }

    _disconnectEngine() {
        this._log('engine vanished');
        this._proxy = null;
        this._proxyReady = false;
        this._onFrame(false, {});
    }

    _onFrame(playing, info) {
        const level = Number(info.level ?? 0);
        this._level = Number.isFinite(level) ? Math.max(0, Math.min(1, level)) : 0;
        this._bands = Array.isArray(info.bands) ? info.bands.map(Number) : [];
        this._setPlaying(playing);
    }

    _setPlaying(playing) {
        if (this._playing === playing) {
            this._actor?.queue_repaint();
            return;
        }
        this._playing = playing;
        this._log(`playing=${playing}`);
        if (playing) {
            this._startTimer();
        } else {
            this._stopTimer();
            this._level = 0;
            this._bands = [];
        }
        this._actor?.queue_repaint();
    }

    _startTimer() {
        if (this._timeout)
            return;
        this._timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, FRAME_MS, () => {
            this._phase += FRAME_MS / 1000;
            try {
                this._actor?.queue_repaint();
            } catch {
                // Actor disposed during shutdown.
            }
            return GLib.SOURCE_CONTINUE;
        });
    }

    _stopTimer() {
        if (!this._timeout)
            return;
        GLib.source_remove(this._timeout);
        this._timeout = 0;
    }

    _openPopover() {
        if (!this._proxy || !this._proxyReady)
            return;
        const clock = Main.panel.statusArea.dateMenu;
        const [clockX] = clock ? clock.get_transformed_position() : [0];
        const clockWidth = clock ? clock.width : 0;
        const [, panelY] = Main.panel.get_transformed_position();
        const x = Math.round((clock ? clockX : 0) + clockWidth / 2);
        const y = Math.round(panelY + Main.panel.height);
        this._proxy.ShowPopoverRemote(x, y, () => {}, () => {});
    }

    _connect(object, signal, callback) {
        if (!object)
            return;
        this._signals.push([object, object.connect(signal, callback)]);
    }

    _log(message) {
        console.log(`[floatbeat] ${message}`);
    }
}
