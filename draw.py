"""Everything Monti draws: subtitles, the title, the save button, the closing card and the simple effects.

All drawing is Pillow on 1080x1920 transparent PNGs that monti.py lays over the video with ffmpeg.
"""
import math
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
YELLOW = "#FFD60A"
# The first font that exists: Mac, then Windows, then common Linux paths. (path, index for .ttc files)
BOLD = [("/System/Library/Fonts/HelveticaNeue.ttc", 1), ("C:/Windows/Fonts/segoeuib.ttf", 0),
        ("C:/Windows/Fonts/arialbd.ttf", 0), ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0)]
SUB = [("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0), ("C:/Windows/Fonts/arialbd.ttf", 0),
       ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0)]


def _first(fonts, size):
    for path, index in fonts:
        if os.path.exists(path):
            return ImageFont.truetype(path, size, index=index)
    raise SystemExit("No bold font found; add one to draw.py BOLD/SUB.")


def font(size):
    return _first(BOLD, size)


def draw_frame(words, shown, title, path, sub_y=1330):
    """One overlay frame: the title boxes (if any) and up to three caption words, the last one spoken in yellow."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if title:
        tf, y, rows = font(64), 250, []
        for ln in title:
            x0, y0, x1, y1 = d.textbbox((0, 0), ln, font=tf)
            bx = (W - (x1 - x0)) // 2
            rows.append((ln, bx, y, x0, y0, (bx - 30, y - 18, bx + x1 - x0 + 30, y + y1 - y0 + 22)))
            y += y1 - y0 + 46
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for *_, box in rows:  # soft shadow keeps white boxes visible against a white wall
            ImageDraw.Draw(shadow).rounded_rectangle((box[0], box[1] + 6, box[2], box[3] + 6), radius=22, fill=(0, 0, 0, 110))
        img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
        for ln, bx, y, x0, y0, box in rows:
            d.rounded_rectangle(box, radius=22, fill="white")
            d.text((bx - x0, y - y0), ln, font=tf, fill="black")
    if words:
        sf = _first(SUB, 84)
        sp, wl = d.textlength(" ", font=sf), [d.textlength(w, font=sf) for w in words]
        rows = [list(range(len(words)))]
        if sum(wl) + sp * (len(words) - 1) > W - 120 and len(words) > 1:
            k = (len(words) + 1) // 2
            rows = [list(range(k)), list(range(k, len(words)))]
        y = sub_y
        for r in rows:
            x = (W - (sum(wl[i] for i in r) + sp * (len(r) - 1))) / 2
            for i in r:
                if i < shown:
                    d.text((x, y), words[i], font=sf, fill=YELLOW if i == shown - 1 else "white",
                           stroke_width=7, stroke_fill="black")
                x += wl[i] + sp
            y += 100
    img.save(path)


def draw_save_frames(out_dir, fps, dur=1.5, tap=0.55, size=230):
    """A "save" button tapped on screen, as a PNG sequence: a white disc with a bookmark outline pops in,
    is pressed at `tap` seconds (dips, the bookmark fills yellow, a ring bursts out), then fades."""
    out_dir.mkdir(exist_ok=True)
    for f in out_dir.glob("*.png"): f.unlink()
    box = int(size * 1.9)
    for k in range(int(round(dur * fps))):
        t = k / fps
        if t < 0.3:  # overshoot pop-in
            u = t / 0.3; s = 1.15 * u if u < 0.7 else 1.15 - 0.15 * (u - 0.7) / 0.3
        elif tap <= t < tap + 0.24:  # press: dip then rebound
            u = (t - tap) / 0.24; s = 1 - 0.12 * (1 - abs(2 * u - 1))
        else:
            s = 1.0
        alpha = 1.0 if t < dur - 0.25 else max(0.0, (dur - t) / 0.25)
        img = Image.new("RGBA", (box, box), (0, 0, 0, 0))
        c, r = box // 2, int(size / 2 * s)
        if r > 2:
            sh = Image.new("RGBA", (box, box), (0, 0, 0, 0))
            ImageDraw.Draw(sh).ellipse((c - r, c - r + 10, c + r, c + r + 10), fill=(0, 0, 0, 110))
            img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
            d = ImageDraw.Draw(img)
            d.ellipse((c - r, c - r, c + r, c + r), fill="white")
            bw, bh = r * 0.78, r * 1.05  # bookmark: a tall rectangle with a V cut into its foot
            pts = [(c - bw / 2, c - bh / 2), (c + bw / 2, c - bh / 2), (c + bw / 2, c + bh / 2),
                   (c, c + bh / 2 - bw * 0.42), (c - bw / 2, c + bh / 2)]
            filled = t >= tap + 0.08
            d.polygon(pts, fill="#FFD60A" if filled else None, outline="#111111")
            d.line(pts + [pts[0]], fill="#111111", width=max(int(r * 0.11), 3), joint="curve")
            if tap <= t < tap + 0.45:  # burst ring
                u = (t - tap) / 0.45
                rr = int(r * (1 + 0.6 * u))
                d.ellipse((c - rr, c - rr, c + rr, c + rr), outline=(255, 214, 10, int(255 * (1 - u))), width=8)
        if alpha < 1:
            img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
        img.save(out_dir / f"f{k:03d}.png")


def draw_linkbio_frames(out_dir, fps, dur, text="Link bio'da", w=1080, h=1920):
    """Closing call to action on black, as a PNG sequence. Reels and Shorts put the profile picture and
    name at the bottom left (about x 40-120, y 1640-1720), so a white pill with the text slides in just
    above that spot and a yellow chevron under it bobs down toward the profile."""
    out_dir.mkdir(exist_ok=True)
    for f in out_dir.glob("*.png"): f.unlink()
    f = font(84)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    x0, y0, x1, y1 = probe.textbbox((0, 0), text, font=f)
    tw, th = x1 - x0, y1 - y0
    pw, ph = tw + 120, th + 80
    ax = 90  # chevron x: over the profile picture
    for k in range(int(round(dur * fps))):
        t = k / fps
        u = min(t / 0.45, 1.0); e = 1 - (1 - u) ** 3  # ease-out slide from the left
        a = int(255 * min(t / 0.35, 1.0))
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        px, py = 48 - int(80 * (1 - e)), 1400
        d.rounded_rectangle((px, py, px + pw, py + ph), radius=ph // 2, fill=(255, 255, 255, a))
        d.text((px + 60 - x0, py + 40 - y0), text, font=f, fill=(12, 12, 12, a))
        if t > 0.3:  # chevron under the pill, bobbing down toward the profile
            b = int(16 * math.sin((t - 0.3) * 2 * math.pi * 1.2))
            ca = int(255 * min((t - 0.3) / 0.3, 1.0))
            top = py + ph + 50 + b
            d.line([(ax - 46, top), (ax, top + 46), (ax + 46, top)], fill=(255, 214, 10, ca), width=14, joint="curve")
        img.save(out_dir / f"f{k:03d}.png")


def _chip(text, scale):
    """A white pill label for the orbit, drawn at `scale` (items shrink as they swing behind the head)."""
    f = font(max(int(46 * scale), 12))
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tw = probe.textlength(text, font=f)
    hgt = int(72 * scale)
    img = Image.new("RGBA", (int(tw + 44 * scale), hgt), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, img.width - 1, hgt - 1), radius=hgt // 2, fill=(255, 255, 255, 245))
    d.text((22 * scale, 11 * scale), text, font=f, fill=(15, 15, 15))
    return img


def draw_orbit_frame(mask, head, t, items, alpha, path, turns=0.35):
    """One frame of labels circling the head. `mask` is the person mask (L, white = person),
    `head` (cx, cy, size) the face box, `t` seconds into the effect. The half of the ring behind
    the head is cut out by the mask, so the labels pass behind it; the front half is drawn on top."""
    cx, cy, size = head
    rx, ry, oy = size * 0.95, size * 0.2, -size * 0.62  # flat ellipse around the top of the head
    back = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # the ring itself: a thin highlighter line, split into back and front halves
    steps = 120
    for k in range(steps):
        a0, a1 = 2 * math.pi * k / steps, 2 * math.pi * (k + 1) / steps
        layer = front if math.sin((a0 + a1) / 2) > 0 else back
        ImageDraw.Draw(layer).line([(cx + rx * math.cos(a0), cy + oy + ry * math.sin(a0)),
                                    (cx + rx * math.cos(a1), cy + oy + ry * math.sin(a1))],
                                   fill=(255, 214, 10, 235), width=6)
    for j, text in enumerate(items):
        a = 2 * math.pi * (j / len(items) + turns * t)
        depth = math.sin(a)  # +1 nearest the camera, -1 behind the head
        chip = _chip(text, 0.8 + 0.2 * depth)
        x, y = cx + rx * math.cos(a) - chip.width / 2, cy + oy + ry * math.sin(a) - chip.height / 2
        (front if depth > 0 else back).alpha_composite(chip, (int(x), int(y)))
    # behind the head: keep only where there is no person
    hole = Image.eval(mask, lambda v: 255 - v)
    back.putalpha(Image.composite(back.getchannel("A"), Image.new("L", (W, H), 0), hole))
    out = Image.alpha_composite(back, front)
    if alpha < 1:
        out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    out.save(path)


def draw_mask_spotlight(mask, alpha, path, title=""):
    """Darkens everything but the person (true spotlight), with an optional title at the top."""
    dark = Image.eval(mask.filter(ImageFilter.GaussianBlur(3)), lambda v: int((255 - v) * 0.72 * alpha))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.putalpha(dark)
    if title:
        f = font(120)
        tw = ImageDraw.Draw(img).textlength(title, font=f)
        ImageDraw.Draw(img).text(((W - tw) / 2, 150), title, font=f, fill=(255, 255, 255, int(255 * alpha)))
    img.save(path)
