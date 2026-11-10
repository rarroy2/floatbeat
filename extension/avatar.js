// Mini avatar for the GNOME top bar.
//
// Drawn with Cairo in a fixed 56x38 coordinate space; the actor scales it to
// the panel height. The desk intentionally overflows a few pixels below the
// panel: the panel does not clip its children, so the DJ looks like it is
// sitting on the edge of the bar with the mixer dangling.

export const DESIGN_WIDTH = 56;
export const DESIGN_HEIGHT = 38;
export const OVERFLOW = 6;

const BODY = { x: 14, y: 4, w: 28, h: 21, r: 8 };
const DESK = { x: 6, y: 26, w: 44, h: 8, r: 3 };
const EYES = [24.5, 31.5];

function roundedRect(cr, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    cr.newSubPath();
    cr.arc(x + r, y + r, r, Math.PI, 1.5 * Math.PI);
    cr.arc(x + w - r, y + r, r, 1.5 * Math.PI, 2 * Math.PI);
    cr.arc(x + w - r, y + h - r, r, 0, 0.5 * Math.PI);
    cr.arc(x + r, y + h - r, r, 0.5 * Math.PI, Math.PI);
    cr.closePath();
}

export function drawAvatar(cr, width, height, phase, level) {
    cr.save();
    cr.scale(width / DESIGN_WIDTH, height / DESIGN_HEIGHT);

    // Ropes: fixed at the panel edge, following the small sway.
    const sway = Math.sin(phase * 0.9) * 0.8 * level;
    cr.setLineWidth(0.9);
    cr.setSourceRGBA(0.55, 0.55, 0.55, 0.85);
    cr.moveTo(19, 0);
    cr.lineTo(11 + sway, 26);
    cr.stroke();
    cr.moveTo(37, 0);
    cr.lineTo(45 + sway, 26);
    cr.stroke();

    cr.translate(sway, 0);

    // Desk (mixer) with five tiny level bars.
    roundedRect(cr, DESK.x, DESK.y, DESK.w, DESK.h, DESK.r);
    cr.setSourceRGB(0.043, 0.043, 0.047);
    cr.fillPreserve();
    cr.setLineWidth(0.7);
    cr.setSourceRGB(0.29, 0.29, 0.29);
    cr.stroke();

    const bars = 5;
    for (let i = 0; i < bars; i++) {
        const band = 0.5 + 0.5 * Math.sin(phase * 2.3 + i * 0.9);
        const h = 1.2 + 3.4 * band * (0.4 + 0.6 * level);
        roundedRect(cr, 19 + i * 4.4, DESK.y + DESK.h - 1.2 - h, 2.4, h, 0.8);
        cr.setSourceRGBA(0.145, 0.957, 0.824, 0.9);
        cr.fill();
    }

    // Arms, leaning outward with the beat.
    const angle = (0.18 + 0.12 * level);
    drawArm(cr, 15, 18, -angle);
    drawArm(cr, 41, 18, angle);

    // Body.
    roundedRect(cr, BODY.x, BODY.y, BODY.w, BODY.h, BODY.r);
    cr.setSourceRGB(0.851, 0.851, 0.851);
    cr.fillPreserve();
    cr.setLineWidth(0.7);
    cr.setSourceRGBA(0, 0, 0, 0.16);
    cr.stroke();

    // Eyes: the only colour, stretching with the level.
    const eyeH = 5.5 + 4.5 * level;
    for (const x of EYES) {
        roundedRect(cr, x - 1.3, 14.5 - eyeH / 2, 2.6, eyeH, 1.3);
        cr.setSourceRGB(0.145, 0.957, 0.824);
        cr.fill();
    }

    cr.restore();
}

function drawArm(cr, x, y, angle) {
    cr.save();
    cr.translate(x, y);
    cr.rotate(angle);
    roundedRect(cr, -2, -1, 4, 10, 2);
    cr.setSourceRGB(0.851, 0.851, 0.851);
    cr.fillPreserve();
    cr.setLineWidth(0.6);
    cr.setSourceRGBA(0, 0, 0, 0.14);
    cr.stroke();
    cr.restore();
}
