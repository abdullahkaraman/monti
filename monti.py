"""Monti: cuts a talking-head vertical video, writes word-by-word subtitles and adds a few simple effects.

    python monti.py analyze VIDEO        # transcript + suggested cuts -> work/<name>/plan.json
    python monti.py render PLAN [OUTPUT] # plan -> finished 1080x1920 video

The plan is a JSON file a person (or a coding agent) reviews between the two steps; PLAN.md lists its fields.
Rules learned from feedback live in KURALLAR.md and are read before every edit.
"""
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H, FPS = 1080, 1920, 30
MAC = sys.platform == "darwin"
SFX = Path(os.environ.get("MONTI_SFX", Path.home() / "monti" / "sfx-kit"))
SOUNDS = {  # name -> (sfx-kit file, volume)
    "pop": ("sounds/pops/pop-medium-in.wav", 0.5),
    "ding": ("sounds/notifications/notification-alert-soft.wav", 0.45),
    "whoosh": ("sounds/whooshes/whoosh-fast-soft.wav", 0.5),
    "boom": ("sounds/booms-and-bass/boom-hit-soft.wav", 0.6),
}
EFFECT_DUR = {"zoom": 1.5, "spotlight": 3.0, "orbit": 3.0}
SAVE_Y = 1620  # save button centre: on the chest, below the subtitle band


def sh(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def duration(path):
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout)


def picture_delay(path):
    """Seconds ffmpeg shows the picture too early. A Samsung phone starts the picture ~0.2 s after the sound and says so
    in the file's edit list; ffmpeg drops that gap ("Missing key frame") and pulls the picture to zero."""
    import struct
    found = {}

    def walk(f, end, video):
        while f.tell() + 8 <= end:
            o = f.tell()
            n, kind = struct.unpack(">I4s", f.read(8))
            if n == 1: n = struct.unpack(">Q", f.read(8))[0]
            if n == 0: n = end - o
            if n < 8: return
            if kind == b"trak": video = {}
            if kind in (b"moov", b"trak", b"mdia", b"edts"):
                walk(f, o + n, video)
            elif video is not None and kind in (b"elst", b"mdhd", b"hdlr"):
                d = f.read(o + n - f.tell())
                if kind == b"hdlr": video["type"] = d[8:12]
                if kind == b"mdhd": video["scale"] = struct.unpack(">I", d[20:24] if d[0] else d[12:16])[0]
                if kind == b"elst" and d[0] == 0 and struct.unpack(">I", d[4:8])[0] == 1:
                    video["media"] = struct.unpack(">i", d[12:16])[0]
            if kind == b"trak" and video.get("type") == b"vide": found.update(video)
            f.seek(o + n)

    with open(path, "rb") as f:
        walk(f, os.path.getsize(path), None)
    if found.get("media", 0) <= 0:
        return 0.0

    def first(*opt):
        out = sh(["ffprobe", "-v", "error", *opt, "-read_intervals", "%+#30", "-select_streams", "v:0", "-show_entries",
                  "packet=pts_time", "-of", "csv=p=0", str(path)]).stdout
        return min(float(x) for x in out.replace(",", " ").split() if x != "N/A")

    return max(0.0, first("-ignore_editlist", "1") - found["media"] / found["scale"] - first())


def synced(path, work):
    """The same recording with the picture put back where the phone recorded it (stream copy), or the file itself."""
    d = picture_delay(path)
    if d < 0.02:
        return Path(path)
    out = Path(work) / (Path(path).stem + "_sync.mp4")
    sh(["ffmpeg", "-v", "error", "-y", "-itsoffset", f"{d:.4f}", "-i", str(path), "-i", str(path), "-map", "0:v:0", "-map", "1:a:0",
        "-c", "copy", str(out)])
    return out


def silences(wav, min_len):
    log = subprocess.run(["ffmpeg", "-i", wav, "-af", f"silencedetect=n=-35dB:d={min_len}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return list(zip(map(float, re.findall(r"silence_start: ([0-9.]+)", log)),
                    map(float, re.findall(r"silence_end: ([0-9.]+)", log))))


# ---------------------------------------------------------------- analyze

FILLER_PROMPT = """Listen to this video with its sound. Find the filler sounds in the speech (eee, ııı, hmm, uh:
hesitation sounds that are not words). Leave out repeated words and real words.
Return only a JSON array: [{"start": seconds, "end": seconds}]. Seconds from the start of the video, to 0.1.
Return [] if there are none."""


def gemini_key():
    """GEMINI_API_KEY, or the system password store under service "monti", account "gemini-api-key"
    (Keychain on Mac, Credential Manager on Windows; see the setup guide). Never read from a file."""
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    try:
        import keyring
        return keyring.get_password("monti", "gemini-api-key")
    except ImportError:
        pass
    if MAC:
        try:
            return sh(["security", "find-generic-password", "-s", "monti", "-a", "gemini-api-key", "-w"]).stdout.strip()
        except subprocess.CalledProcessError:
            return None
    return None


def transcribe(wav, work, lang):
    """Word-timed transcript. mlx-whisper (fast on Apple Silicon) if installed, else openai-whisper; same JSON."""
    if shutil.which("mlx_whisper"):
        cmd = ["mlx_whisper", str(wav), "--model", "mlx-community/whisper-large-v3-turbo", "--word-timestamps", "True",
               "--output-format", "json", "--output-dir", str(work)]
    elif shutil.which("whisper"):
        cmd = ["whisper", str(wav), "--model", "turbo", "--word_timestamps", "True",
               "--output_format", "json", "--output_dir", str(work)]
    else:
        sys.exit("No Whisper found: install mlx-whisper (Mac) or openai-whisper (Windows); see the setup guide.")
    sh(cmd + (["--language", lang]))
    return json.load(open(Path(work) / (Path(wav).stem + ".json")))


def gemini_fillers(video, work, key):
    """Gemini watches a small copy of the video and lists filler sounds; Whisper does not write them."""
    small = work / "small.mp4"
    sh(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", "scale=540:-2", "-c:v", "libx264", "-crf", "28",
        "-preset", "fast", "-c:a", "aac", "-b:a", "96k", str(small)])
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "video/mp4", "data": base64.b64encode(small.read_bytes()).decode()}},
        {"text": FILLER_PROMPT}]}], "generationConfig": {"responseMimeType": "application/json"}}
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
        data=json.dumps(body).encode(), headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=600))
    text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
    return [{"start": float(f["start"]), "end": float(f["end"])} for f in json.loads(text)]


def analyze(args):
    original = Path(args.input).resolve()
    work = HERE / "work" / original.stem
    work.mkdir(parents=True, exist_ok=True)
    src = synced(original, work)
    wav = work / "audio.wav"
    sh(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    tr = transcribe(wav, work, args.lang)
    words = [{"word": w["word"].strip(), "start": round(w["start"], 2), "end": round(w["end"], 2)}
             for s in tr["segments"] for w in s.get("words", [])]
    while words and words[-1]["end"] - words[-1]["start"] < 0.05:  # Whisper's zero-length tail tokens
        words.pop()

    fillers, key = [], gemini_key()
    if key:
        try:
            fillers = gemini_fillers(str(src), work, key)
        except Exception as e:  # fillers are a suggestion; a failed call must not stop the edit
            print("Gemini filler pass skipped:", e, file=sys.stderr)
    else:
        print("No Gemini key: filler sounds were not looked for (see the setup guide, step 6).", file=sys.stderr)

    plan = {
        "source": str(src),
        "output": str(original.with_name(original.stem + "_monti.mp4")),
        "range": [round(max(words[0]["start"] - 0.1, 0), 2) if words else 0.0, round(duration(str(src)), 2)],
        "cuts": [],          # [[start, end, "why"], ...] parts to remove (a fumble, a repeated sentence)
        "fillers": fillers,  # Gemini's filler sounds; fix start/end or set "skip": true to keep one
        "protect": [],       # [[start, end], ...] silent parts that must stay (a deliberate pause or move)
        "max_gap": 0.35, "pad": 0.12,
        "replace": {},       # {"Klod": "Claude"}: fix words Whisper gets wrong
        "title": {"lines": [], "until": 4.0},
        "effects": [],       # see PLAN.md
        "outro": None,       # {"save_at": seconds, "hold": 2.2, "text": "Link bio'da"}
        "words": words,
    }
    out = work / "plan.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(out)


# ---------------------------------------------------------------- render

def subtract(ranges, cuts):
    out = []
    for a, b in ranges:
        segs = [(a, b)]
        for x, y in cuts:
            nxt = []
            for s, e in segs:
                if y <= s or x >= e:
                    nxt.append((s, e))
                    continue
                if x > s: nxt.append((s, x))
                if y < e: nxt.append((y, e))
            segs = nxt
        out += [(s, e) for s, e in segs if e - s > 0.05]
    return out


def apply_replace(words, replace):
    """Merge Whisper tokens that spell a known name into one corrected word, keeping the spoken suffix."""
    letters = lambda t: re.sub(r"[^\w]", "", t).lower()
    rules = [(k.split(), v) for k, v in replace.items()]
    out, i = [], 0
    while i < len(words):
        for toks, rep in rules:
            n = len(toks)
            if [letters(w["word"]) for w in words[i:i + n]] == [letters(t) for t in toks]:
                tail = re.sub(r"^\w+", "", words[i + n - 1]["word"])
                if letters(rep).endswith(letters(tail)):
                    tail = re.search(r"[.,!?…]*$", tail).group()
                out.append({"word": rep + tail, "start": words[i]["start"], "end": words[i + n - 1]["end"]})
                i += n
                break
        else:
            out.append(words[i])
            i += 1
    return out


def render(args):
    sys.path.insert(0, str(HERE))
    import draw
    import vision
    from PIL import Image
    plan = json.load(open(args.plan))
    work = Path(args.plan).resolve().parent
    src = plan["source"]
    out = args.output or plan.get("output") or str(Path(src).with_name(Path(src).stem + "_monti.mp4"))
    wav = str(work / "audio.wav")

    # 1) what stays: the range, minus long silences, cuts and fillers
    prot = plan.get("protect", [])
    sil = [(a, b) for a, b in silences(wav, plan["max_gap"]) if not any(a < pb and b > pa for pa, pb in prot)]
    pad = plan["pad"]
    cuts = [(a + pad, b - pad) for a, b in sil] + [tuple(c[:2]) for c in plan["cuts"]]
    cuts += [(f["start"], f["end"]) for f in plan["fillers"] if not f.get("skip")]
    keep = subtract([tuple(plan["range"])], cuts)
    # a kept piece with no word in it is a sliver between two cuts and plays as a stutter; a silent piece of
    # 0.2 s or more stays, it is a breath left between two sentences
    mids = [(w["start"] + w["end"]) / 2 for w in plan["words"]]
    pauses = silences(wav, 0.2)
    keep = [(a, b) for a, b in keep
            if any(a <= m <= b for m in mids) or any(a < pb and b > pa for pa, pb in prot)
            or (b - a >= 0.2 and any(sa <= a + 0.02 and b - 0.02 <= sb for sa, sb in pauses))]
    (work / "timeline.json").write_text(json.dumps({"keep": keep}))

    def remap(t):  # source seconds -> output seconds
        off = 0.0
        for a, b in keep:
            if a <= t <= b: return off + t - a
            if t < a: return off
            off += b - a
        return off

    total = sum(b - a for a, b in keep)
    outro = plan.get("outro")
    speech_end = total
    if outro: total += outro.get("hold", 2.2)

    # 2) subtitles: up to three words at a time, the word being spoken in yellow
    events = []
    if plan.get("captions", True):
        words = apply_replace(plan["words"], plan.get("replace", {}))
        caps, cur = [], []
        for w in words:
            if not any(a <= (w["start"] + w["end"]) / 2 <= b for a, b in keep):
                continue
            if cur and (len(cur) == 3 or w["start"] - cur[-1]["end"] > 0.4 or cur[-1]["word"][-1] in ".?!,"):
                caps.append(cur); cur = []
            cur.append(w)
        if cur: caps.append(cur)
        for j, c in enumerate(caps):
            ws = [w["word"] for w in c]
            ws[-1] = ws[-1].rstrip(".,")
            st = [remap(w["start"]) for w in c]
            for k in range(1, len(st)): st[k] = max(st[k], st[k - 1])
            e = max(remap(c[-1]["end"]), st[-1] + 0.3)
            if j + 1 < len(caps): e = min(e + 0.25, remap(caps[j + 1][0]["start"]))
            for k in range(len(c)):
                a, b = st[k], (st[k + 1] if k + 1 < len(c) else e)
                if b > a: events.append((a, b, ws, k + 1))
    title, until = plan["title"]["lines"], plan["title"]["until"]
    subs = work / "subs"
    subs.mkdir(exist_ok=True)
    for f in subs.glob("*.png"): f.unlink()
    pts = sorted({0.0, total} | ({until} if title else set()) | {x for a, b, *_ in events for x in (a, b)})
    lines, n = ["ffconcat version 1.0"], 0
    for a, b in zip(pts, pts[1:]):
        if b - a < 0.001: continue
        ev = next(((ws, k) for s, e, ws, k in events if s <= a < e), (None, 0))
        draw.draw_frame(ev[0], ev[1], title if title and a < until else None, subs / f"f{n:04d}.png")
        lines += [f"file f{n:04d}.png", f"duration {b - a:.3f}"]; n += 1
    lines.append(lines[-2])
    (subs / "list.ffconcat").write_text("\n".join(lines) + "\n")

    # 3) the filter graph: cut pieces joined, then effects, subtitles, outro
    extra, sounds = [], []
    def add(a):
        extra.extend(a)
        return 1 + extra.count("-i")
    labels = iter(range(10 ** 6))
    nl = lambda: f"x{next(labels)}"
    fc, cat = "", ""
    first = float(sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=start_time",
                      "-of", "default=nw=1:nk=1", src]).stdout.split()[0])
    for k, (a, b) in enumerate(keep):
        # a piece that starts before the picture does keeps that gap (first frame held), or the lips move early again
        zero = f"setpts=PTS-{a}/TB,fps={FPS}:start_time=0" if a < first else f"setpts=PTS-STARTPTS,fps={FPS}"
        fc += (f"[0:v]trim={a}:{b},{zero},scale={W}:{H}[v{k}];"
               f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={max(b - a - 0.02, 0)}:d=0.02[a{k}];")
        cat += f"[v{k}][a{k}]"
    fc += f"{cat}concat=n={len(keep)}:v=1:a=1[vc0][ac0];"
    hold = total - speech_end
    fc += (f"[vc0]tpad=stop_mode=clone:stop_duration={hold:.3f}[vc];[ac0]apad=pad_dur={hold:.3f}[ac];" if outro
           else "[vc0]null[vc];[ac0]anull[ac];")
    vlast = "vc"

    def person_overlay(i, e, d, paint):
        """Per-frame overlay for effects that need the person mask (vision.py). Frames come from the source at
        the effect's time, so the window is clipped to the kept piece it starts in."""
        d = min(d, next((b for a, b in keep if a <= e["at"] <= b), e["at"] + d) - e["at"])
        base = work / f"fx{i}"
        for sub in ("src", "mask", "ov"):
            (base / sub).mkdir(parents=True, exist_ok=True)
            for f in (base / sub).glob("*.png"): f.unlink()
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{e['at']:.3f}", "-t", f"{d:.3f}", "-i", src,
            "-vf", f"fps={FPS},scale={W}:{H}", str(base / "src" / "%04d.png")])
        frames = sorted((base / "src").glob("*.png"))
        vision.masks(frames, base / "mask")
        heads = []
        if e["type"] == "orbit":  # face box per frame, averaged over 9 frames so the ring does not shake
            last = (W // 2, 760, 520)
            for box in vision.faces(frames):
                last = box or last
                heads.append(last)
            heads = [tuple(sum(h[c] for h in heads[max(0, k - 4):k + 5]) / len(heads[max(0, k - 4):k + 5])
                           for c in range(3)) for k in range(len(heads))]
        for k, fpath in enumerate(frames):
            tt = k / FPS
            alpha = max(0.0, min(1.0, tt / 0.3, (d - tt) / 0.3))
            paint(Image.open(base / "mask" / fpath.name).convert("L"), heads[k] if heads else None, tt, alpha,
                  base / "ov" / fpath.name)
        return add(["-framerate", str(FPS), "-i", str(base / "ov" / "%04d.png")])

    for i, e in enumerate(plan.get("effects", [])):
        t, d = remap(e["at"]), e.get("dur", EFFECT_DUR[e["type"]])
        a, o = nl(), nl()
        if e["type"] == "zoom":  # punch-in on the face for the window
            s, cx, cy = e.get("scale", 1.3), e.get("cx", W // 2), e.get("cy", 760)
            sw, shh = int(W * s) // 2 * 2, int(H * s) // 2 * 2
            x, y = min(max(int(cx * s - W / 2), 0), sw - W), min(max(int(cy * s - H / 2), 0), shh - H)
            fc += (f"[{vlast}]split[{a}][{a}b];[{a}b]trim=start={t:.3f}:end={t + d:.3f},scale={sw}:{shh},"
                   f"crop={W}:{H}:{x}:{y}[{a}z];[{a}][{a}z]overlay=0:0:eof_action=pass:"
                   f"enable='between(t,{t:.3f},{t + d:.3f})'[{o}];")
            sounds.append((t, e.get("sound", "whoosh")))
        else:
            if e["type"] == "orbit":
                items, turns = e.get("items", ["Monti"]), e.get("turns", 0.35)
                n = person_overlay(i, e, d, lambda m, hd, tt, al, p: draw.draw_orbit_frame(m, hd, tt, items, al, p, turns))
                sounds.append((t, e.get("sound", "whoosh")))
            else:  # spotlight: only the background darkens
                n = person_overlay(i, e, d, lambda m, hd, tt, al, p: draw.draw_mask_spotlight(m, al, p, e.get("title", "")))
                sounds.append((t, e.get("sound", "boom")))
            fc += f"[{n}:v]format=rgba,setpts=PTS+{t:.3f}/TB[{a}];[{vlast}][{a}]overlay=0:0:eof_action=pass[{o}];"
        vlast = o

    fc += f"[1:v]format=rgba,fps={FPS}[sub];[{vlast}][sub]overlay=0:0:shortest=1[vs];"
    vlast = "vs"

    if outro:  # a save button tapped on the chest, then black with "Link bio'da" pointing at the profile
        if "save_at" in outro:
            d_, t = work / "save", remap(outro["save_at"])
            draw.draw_save_frames(d_, FPS)
            n, o = add(["-framerate", str(FPS), "-i", str(d_ / "f%03d.png")]), nl()
            fc += (f"[{n}:v]format=rgba,setpts=PTS-STARTPTS+{t:.3f}/TB[{o}s];[{vlast}][{o}s]overlay="
                   f"x={W // 2}-w/2:y={SAVE_Y}-h/2:eof_action=pass[{o}];")
            vlast = o
            sounds += [(t, "pop"), (t + 0.55, "ding")]
        n, o = add(["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}:d={total:.3f}"]), nl()
        fc += (f"[{n}:v]format=rgba,fade=t=in:st={speech_end:.3f}:d=0.35:alpha=1[{o}k];"
               f"[{vlast}][{o}k]overlay=0:0:enable='gte(t,{speech_end:.3f})'[{o}];")
        vlast = o
        d_, t = work / "linkbio", speech_end + 0.3
        draw.draw_linkbio_frames(d_, FPS, total - t, outro.get("text", "Link bio'da"))
        n, o = add(["-framerate", str(FPS), "-i", str(d_ / "f%03d.png")]), nl()
        fc += f"[{n}:v]format=rgba,setpts=PTS-STARTPTS+{t:.3f}/TB[{o}l];[{vlast}][{o}l]overlay=0:0:eof_action=pass[{o}];"
        vlast = o
        sounds.append((t, "whoosh"))

    fc += f"[{vlast}]format=yuv420p[v];"
    alast = "ac"
    if sounds and not SFX.exists():
        print(f"No sound kit at {SFX}: effects are silent (see the setup guide, step 4).", file=sys.stderr)
        sounds = []
    if sounds:
        mixed = []
        for name in sorted({s for _, s in sounds}):
            file, vol = SOUNDS[name]
            n = add(["-i", str(SFX / file)])
            times = [t for t, s in sounds if s == name]
            fc += f"[{n}:a]aresample=48000,asplit={len(times)}" + "".join(f"[{name}{j}]" for j in range(len(times))) + ";"
            for j, t in enumerate(times):
                ms = int(t * 1000)
                fc += f"[{name}{j}]adelay={ms}|{ms},volume={vol}[{name}{j}d];"
                mixed.append(f"[{name}{j}d]")
        fc += f"[{alast}]" + "".join(mixed) + f"amix=inputs={1 + len(mixed)}:normalize=0:duration=first[am];"
        alast = "am"
    fc += f"[{alast}]loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    (work / "filter.txt").write_text(fc.replace(";", ";\n"))
    sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-f", "concat", "-safe", "0", "-i", str(subs / "list.ffconcat"), *extra,
        "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
    print(out, f"{total:.2f}s", f"{len(keep)} pieces", f"{len(plan.get('effects', []))} effects", f"{len(sounds)} sounds")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("analyze", help="transcribe a video and write its plan")
    a.add_argument("input"); a.add_argument("--lang", default="tr", help="spoken language (Whisper code), default tr")
    r = sp.add_parser("render", help="render a reviewed plan")
    r.add_argument("plan"); r.add_argument("output", nargs="?")
    args = ap.parse_args()
    analyze(args) if args.cmd == "analyze" else render(args)
