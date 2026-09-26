#!/usr/bin/env python3
"""generate-wallpapers.py — Zorin-AI OS wallpaper set, omarchy-style.

Procedurally renders dark, minimal, moody desktop wallpapers (layered
mountain/forest silhouettes, atmospheric gradients, stars, film grain).
Deterministic: every scene is seeded, so builds are reproducible.

Usage:
  python3 generate-wallpapers.py [--outdir DIR] [--width W] [--height H]
                                 [--seed N] [--only NAME]

Scenes default to 3840x2160 JPEG (quality 92). Requires: pillow, numpy.
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 3840, 2160


# ---------------------------------------------------------------- noise utils
def value_noise_1d(n, rng, octaves=6, persistence=0.5, base_freq=4):
    """Fractal 1D value noise in [0, 1], length n, smooth (cubic) interp."""
    total = np.zeros(n)
    amp, freq = 1.0, base_freq
    norm = 0.0
    for _ in range(octaves):
        pts = rng.random(freq + 2) * 2 - 1
        x = np.linspace(0, freq, n)
        idx = np.clip(x.astype(int), 0, freq)
        frac = x - idx
        smooth = frac * frac * (3 - 2 * frac)
        vals = pts[idx] * (1 - smooth) + pts[idx + 1] * smooth
        total += vals * amp
        norm += amp
        amp *= persistence
        freq *= 2
    total /= norm
    return (total - total.min()) / (total.max() - total.min() + 1e-9)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp_rgb(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def vertical_gradient(w, h, stops):
    """stops: list of (pos 0..1, (r,g,b)) top->bottom."""
    cols = np.zeros((h, w, 3), dtype=np.float64)
    ys = np.linspace(0, 1, h)
    for ch in range(3):
        vals = np.interp(ys, [p for p, _ in stops], [c[ch] for _, c in stops])
        cols[:, :, ch] = vals[:, None]
    return cols


# ---------------------------------------------------------------- scene parts
def draw_sky(img_arr, rng, sky_stops, cloudiness=0.35, seed_shift=0):
    """Vertical gradient + very-low-contrast drifting cloud bands."""
    h, w, _ = img_arr.shape
    base = vertical_gradient(w, h, sky_stops)
    n = value_noise_1d(h, rng, octaves=5, base_freq=3 + seed_shift)
    band = (n[:, None] - 0.5) * cloudiness * 14.0
    img_arr[:] = np.clip(base + band[:, :, None], 0, 255)


def draw_stars(img_arr, rng, density=90, max_y=0.62):
    h, w, _ = img_arr.shape
    count = int(w * h / 1e6 * density)
    xs = (rng.random(count) * w).astype(int)
    ys = (rng.random(count) * h * max_y).astype(int)
    bright = rng.random(count)
    for x, y, b in zip(xs, ys, bright):
        if b < 0.55:
            v = 90 + int(b * 90)
        elif b < 0.92:
            v = 140 + int(b * 80)
        else:
            v = 220 + int(b * 35)
        img_arr[y, x] = np.maximum(img_arr[y, x], v)
        if b > 0.97:  # rare bright star with a soft halo
            img_arr[y, x] = 255
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w:
                    img_arr[yy, xx] = np.maximum(img_arr[yy, xx], 160)


def draw_moon(img_arr, cx, cy, r, tint=(225, 230, 235)):
    h, w, _ = img_arr.shape
    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    disc = dist <= r
    glow = np.exp(-(dist / (r * 6)) ** 2) * 0.55
    img_arr[:] = img_arr * (1 - glow[:, :, None]) + np.array(tint) * glow[:, :, None]
    img_arr[disc] = tint


def ridge_mask(w, h, rng, base_y, amp, roughness=6):
    """Silhouette polygon mask for one mountain layer."""
    line = value_noise_1d(w, rng, octaves=6, persistence=0.55,
                          base_freq=roughness)
    ys = (base_y * h - line * amp * h).astype(int)
    poly = [(x, int(y)) for x, y in enumerate(ys)] + [(w - 1, h), (0, h)]
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    return mask, ys


def atmospheric_color(sky_pixel, ridge_color, depth):
    """Blend ridge color toward the sky haze for far layers (aerial perspective)."""
    return lerp_rgb(sky_pixel, ridge_color, depth)


def draw_ridges(img, img_arr, rng, layers, palette, haze_y=0.55, blur=True,
                haze_lift=None):
    """layers: list of dicts(base_y, amp, rough, depth 0..1 near).

    haze_lift: optional explicit haze color for dark skies; far layers fade
    toward it (must be LIGHTER than the sky for silhouettes to read)."""
    w, h = img.size
    haze = haze_lift or tuple(int(v) for v in img_arr[int(h * haze_y), int(w * 0.5)])
    for spec in layers:
        mask, _ = ridge_mask(w, h, rng, spec["base_y"], spec["amp"],
                             spec.get("rough", 6))
        color = lerp_rgb(haze, palette["ridge"], spec["depth"])
        layer = Image.new("RGB", img.size, color)
        if blur and spec["depth"] < 0.65:
            layer = layer.filter(ImageFilter.GaussianBlur(3 + (1 - spec["depth"]) * 9))
        img.paste(layer, (0, 0), mask)
        img_arr[:] = np.asarray(img)


def draw_mist(img, img_arr, rng, bands):
    """Soft horizontal mist bands: bands = list of (center_y 0..1, strength)."""
    w, h = img.size
    for cy, strength in bands:
        band = Image.new("L", (w, h), 0)
        bd = ImageDraw.Draw(band)
        yy = int(cy * h)
        thickness = int(h * 0.045 * (0.6 + rng.random() * 0.8))
        for i in range(thickness):
            a = int(strength * 255 * (1 - abs(i - thickness / 2) / (thickness / 2)) ** 2)
            bd.line([(0, yy + i), (w, yy + i)], fill=a)
        band = band.filter(ImageFilter.GaussianBlur(28))
        mist = Image.new("RGB", img.size, atmospheric_color(
            tuple(int(v) for v in img_arr[yy, w // 2]), (200, 205, 215), 0.25))
        img.paste(mist, (0, 0), band)
        img_arr[:] = np.asarray(img)


def finish(img, grain=0.02, vignette=0.16):
    """Film grain + vignette, then return the final image."""
    arr = np.asarray(img).astype(np.float64)
    h, w, _ = arr.shape
    rng = np.random.default_rng(77)
    arr += rng.normal(0, grain * 255, (h, w, 1))
    yy, xx = np.ogrid[:h, :w]
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    arr *= (1 - vignette * np.clip(d - 0.55, 0, 1) ** 1.5)[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# ------------------------------------------------------------------- scenes
def scene_midnight_ridges(w, h, seed):
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (w, h))
    arr = np.zeros((h, w, 3))
    draw_sky(arr, rng, [(0.0, hex_rgb("070b14")), (0.45, hex_rgb("0d1526")),
                        (0.78, hex_rgb("1a2740")), (1.0, hex_rgb("24344f"))],
             cloudiness=0.3)
    draw_stars(arr, rng, density=110)
    draw_moon(arr, w * 0.78, h * 0.16, int(h * 0.035))
    img = Image.fromarray(arr.astype(np.uint8))
    img_arr = np.asarray(img).astype(np.float64)
    draw_ridges(img, img_arr, rng, [
        dict(base_y=0.60, amp=0.12, rough=5, depth=0.30),
        dict(base_y=0.71, amp=0.14, rough=6, depth=0.55),
        dict(base_y=0.84, amp=0.15, rough=7, depth=0.85),
        dict(base_y=0.98, amp=0.12, rough=8, depth=1.00),
    ], palette=dict(ridge=hex_rgb("05080f")), haze_lift=hex_rgb("33456b"))
    draw_mist(img, img_arr, rng, [(0.68, 0.14), (0.81, 0.10)])
    return finish(img)


def scene_dusk_valley(w, h, seed):
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (w, h))
    arr = np.zeros((h, w, 3))
    draw_sky(arr, rng, [(0.0, hex_rgb("0b1020")), (0.40, hex_rgb("232a44")),
                        (0.68, hex_rgb("6e4a3a")), (0.84, hex_rgb("b97a4a")),
                        (1.0, hex_rgb("d99a5b"))], cloudiness=0.45)
    draw_stars(arr, rng, density=40, max_y=0.35)
    img = Image.fromarray(arr.astype(np.uint8))
    img_arr = np.asarray(img).astype(np.float64)
    draw_ridges(img, img_arr, rng, [
        dict(base_y=0.70, amp=0.09, rough=5, depth=0.25),
        dict(base_y=0.80, amp=0.11, rough=6, depth=0.60),
        dict(base_y=0.95, amp=0.12, rough=8, depth=1.00),
    ], palette=dict(ridge=hex_rgb("120e12")), haze_y=0.80)
    draw_mist(img, img_arr, rng, [(0.74, 0.30), (0.88, 0.22)])
    return finish(img)


def scene_teal_forest(w, h, seed):
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (w, h))
    arr = np.zeros((h, w, 3))
    draw_sky(arr, rng, [(0.0, hex_rgb("04100f")), (0.5, hex_rgb("0a201d")),
                        (1.0, hex_rgb("123430"))], cloudiness=0.4)
    draw_stars(arr, rng, density=55)
    img = Image.fromarray(arr.astype(np.uint8))
    img_arr = np.asarray(img).astype(np.float64)
    draw_ridges(img, img_arr, rng, [
        dict(base_y=0.60, amp=0.14, rough=9, depth=0.28),
        dict(base_y=0.72, amp=0.15, rough=10, depth=0.55),
        dict(base_y=0.86, amp=0.16, rough=11, depth=0.85),
        dict(base_y=1.02, amp=0.14, rough=12, depth=1.00),
    ], palette=dict(ridge=hex_rgb("020c0a")), haze_lift=hex_rgb("24544a"))
    draw_mist(img, img_arr, rng, [(0.68, 0.15), (0.82, 0.11), (0.93, 0.08)])
    return finish(img)


def scene_storm_coast(w, h, seed):
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (w, h))
    arr = np.zeros((h, w, 3))
    draw_sky(arr, rng, [(0.0, hex_rgb("0c1216")), (0.45, hex_rgb("1a2830")),
                        (0.72, hex_rgb("2c4250")), (1.0, hex_rgb("375663"))],
             cloudiness=0.6)
    img = Image.fromarray(arr.astype(np.uint8))
    img_arr = np.asarray(img).astype(np.float64)
    # sea: darken lower half with horizontal streaks
    hz = int(h * 0.62)
    sea = img_arr.copy()
    sea[hz:, :] *= np.linspace(1.0, 0.35, h - hz)[:, None, None]
    streak = value_noise_1d(h - hz, rng, octaves=4, base_freq=40)
    sea[hz:, :] *= (0.9 + 0.2 * streak)[:, None, None]
    img = Image.fromarray(sea.astype(np.uint8))
    img_arr = np.asarray(img).astype(np.float64)
    draw_mist(img, img_arr, rng, [(0.63, 0.30), (0.70, 0.16)])
    # headland cliff, near-black
    mask, _ = ridge_mask(w, h, rng, base_y=0.94, amp=0.16, roughness=3)
    layer = Image.new("RGB", img.size, hex_rgb("05080a")).filter(
        ImageFilter.GaussianBlur(1.5))
    img.paste(layer, (0, 0), mask)
    img_arr[:] = np.asarray(img)
    return finish(img, grain=0.025)


def scene_ember_minimal(w, h, seed):
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (w, h))
    arr = np.zeros((h, w, 3))
    draw_sky(arr, rng, [(0.0, hex_rgb("08080a")), (0.55, hex_rgb("101014")),
                        (0.80, hex_rgb("241a16")), (1.0, hex_rgb("38241a"))],
             cloudiness=0.25)
    draw_stars(arr, rng, density=70, max_y=0.5)
    img = Image.fromarray(arr.astype(np.uint8))
    img_arr = np.asarray(img).astype(np.float64)
    draw_ridges(img, img_arr, rng, [
        dict(base_y=0.86, amp=0.07, rough=4, depth=0.55),
        dict(base_y=1.00, amp=0.06, rough=6, depth=1.00),
    ], palette=dict(ridge=hex_rgb("070607")), haze_lift=hex_rgb("4a3324"),
        haze_y=0.9)
    draw_mist(img, img_arr, rng, [(0.90, 0.10)])
    return finish(img, grain=0.015, vignette=0.2)


SCENES = {
    "midnight-ridges": scene_midnight_ridges,
    "dusk-valley": scene_dusk_valley,
    "teal-forest": scene_teal_forest,
    "storm-coast": scene_storm_coast,
    "ember-minimal": scene_ember_minimal,
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)))
    p.add_argument("--width", type=int, default=W)
    p.add_argument("--height", type=int, default=H)
    p.add_argument("--seed", type=int, default=20260925)
    p.add_argument("--only", choices=sorted(SCENES))
    args = p.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    names = [args.only] if args.only else sorted(SCENES)
    for name in names:
        out = os.path.join(args.outdir, f"zorin-ai-{name}-{args.height}p.jpg")
        img = SCENES[name](args.width, args.height, args.seed)
        img.save(out, "JPEG", quality=92, optimize=True, progressive=True)
        print(f"{out}  ({os.path.getsize(out) // 1024} KiB)")


if __name__ == "__main__":
    main()
