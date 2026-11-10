// Floatbeat — GNOME Shell extension (spike).
//
// Adds a small DJ actor anchored to the top panel, left of the clock. It lives
// in the shell's UI group (not inside the panel's box layout) so it can overflow
// a few pixels below the bar: the panel does not clip its children.
//
// Clicking it is wired to the future engine call; for now it logs and blinks so
// the hit area can be verified.

import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {DESIGN_WIDTH, OVERFLOW, drawAvatar} from './avatar.js';

const FRAME_MS = 40;
const GAP = 6;

export default class FloatbeatExtension extends Extension {
    enable() {
        this._phase = 0;
        this._timeout = 0;
        this._signals = [];

        this._actor = new St.DrawingArea({
            style_class: 'floatbeat-avatar',
            reactive: true,
            track_hover: true,
        });
        this._actor.set_size(DESIGN_WIDTH, this._panelHeight() + OVERFLOW);
        this._actor.connect('repaint', area => {
            const cr = area.get_context();
            try {
                const [width, height] = area.get_surface_size();
                drawAvatar(cr, width, height, this._phase, this._level());
            } catch (error) {
                this._log(`draw failed: ${error}`);
            } finally {
                cr.$dispose();
            }
        });
        this._actor.connect('destroy', () => {
            this._actor = null;
        });
        this._actor.connect('button-press-event', () => {
            this._log('clicked');
            this._phase += 0.18;
            this._actor.queue_repaint();
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

        this._timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, FRAME_MS, () => {
            this._phase += FRAME_MS / 1000;
            try {
                this._actor?.queue_repaint();
            } catch {
                // The actor can be disposed by the shell during shutdown.
            }
            return GLib.SOURCE_CONTINUE;
        });

        const clock = Main.panel.statusArea.dateMenu;
        this._log(`enabled panel=${this._panelHeight()} clock=${
            clock ? clock.get_transformed_position().join(',') : 'none'}`);
    }

    disable() {
        if (this._timeout) {
            GLib.source_remove(this._timeout);
            this._timeout = 0;
        }
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

    _connect(object, signal, callback) {
        if (!object)
            return;
        this._signals.push([object, object.connect(signal, callback)]);
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
            if (!this._loggedPosition) {
                this._loggedPosition = true;
                this._log(`positioned x=${Math.round(x)} y=${Math.round(y)} clock=${clockX}`);
            }
        } catch (error) {
            if (!this._loggedError) {
                this._loggedError = true;
                this._log(`reposition failed: ${error}`);
            }
        }
    }

    // Placeholder until the engine publishes real levels over D-Bus.
    _level() {
        const v = 0.45 + 0.4 * Math.sin(this._phase * 1.7) * Math.sin(this._phase * 0.6);
        return Math.max(0, Math.min(1, v));
    }

    _log(message) {
        console.log(`[floatbeat] ${message}`);
    }
}
