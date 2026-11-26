"""MontiFX: cut a talking video with monti.py, then dress it with HTML/CSS effects (kit.html).

    python fx/build.py work/<stem>/plan.json OUT.mp4 [--preview T ...]     (T: output seconds before speed-up)

plan["kit"]: { "ui": [pieces, see kit.js], "masa": [[from, to], ...], "face": [x, y] centre of the face in 1080x1920,
               "hold": seconds kept after the last word, "speed": 1.1 }. All times are source seconds.
"looks": [{"at", "end", "style": see LOOKS}] changes the colours from `at` on, with a diagonal wipe.
A piece with "behind": true is drawn behind the speaker (person mask via vision.py; previews show it in front).
"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import vision  # noqa: E402
from monti import SFX, apply_replace, duration  # noqa: E402

SFX_SOUNDS = SFX / "sounds"
SOUNDS = {  # kit name -> (sfx-kit file, volume, seconds)
    "darbe": ("impacts/impact-medium-firm", .55, 1.5), "darbe2": ("impacts/impact-light-soft", .5, 1), "damga": ("impacts/impact-medium-hard", .55, 1),
    "kagit": ("foley/foley-paper-slide", .7, 1), "sayfa": ("everyday-props/props-page-turn", .7, 1.5), "bant": ("everyday-props/props-tape", .5, 1),
    "makas": ("everyday-props/props-scissors", .7, 1), "kalem": ("writing-and-drawing/writing-marker-write", .5, .8), "cizik": ("writing-and-drawing/writing-marker-draw", .7, .7),
    "tik": ("writing-and-drawing/writing-marker-tick", .8, .6), "tebesir": ("writing-and-drawing/writing-chalk-draw", .5, .9), "pop": ("pops/pop-medium-in", .6, .6),
    "tus": ("keyboard/keyboard-letter-soft", .55, .25), "gonder": ("pops/pop-small-out", .6, .5), "tikla": ("interface/click-mouse-firm", .9, .5), "parilti": ("shimmers/shimmer-short-sparkle", .4, 1.5), "iris": ("risers-and-fallers/faller-1s-strong", .55, 1.0), "kapan": ("pops/pop-large-out", .8, .6), "hisir": ("whooshes/whoosh-fast-soft", .5, 1),
}
TIMES = {"at", "end", "markAt", "dropAt", "strikeAt", "subAt", "done", "cutAt", "stampAt", "press", "siteAt", "until", "out", "outAt", "sendAt"}
LOOKS = {  # ffmpeg filters on the picture, under everything the kit draws
    "karanlik": "eq=brightness=-0.13:contrast=1.18:saturation=0.42,colorbalance=rs=-.04:bs=.06:bm=.02,vignette=PI/4.2",
    "sicak": "eq=brightness=0.02:contrast=1.08:saturation=1.12,colorbalance=rs=.06:gs=.01:bs=-.07:rm=.07:bm=-.07:rh=.04:bh=-.05,vignette=PI/6",
    "vcr": "hue=s=0,eq=contrast=1.26:brightness=-0.02,noise=alls=13:allf=t+u,drawgrid=w=0:h=4:t=1:c=black@0.22,vignette=PI/3.8",
}
WIN = (540, 1257)  # centre of the paper frame in kit.js (WIN)


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-3000:])
    return r.stdout


def link_or_copy(src, dst):
    try:
        dst.symlink_to(src)
    except OSError:
        shutil.copy2(src, dst)


def person_mask(base, work, windows, total):
    """Numbered frames for the whole video: the person in white inside the windows, black elsewhere."""
    out, shots = work / "kit_mask", work / "kit_mask_f"
    for d in (out, shots):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir()
    for a, b in windows:
        a = max(0.0, a)
        first, count = int(a * 30), int((min(b, total) - a) * 30) + 2
        run(["ffmpeg", "-v", "error", "-y", "-i", base, "-vf", f"fps=30,trim=start_frame={first}:end_frame={first + count},setpts=PTS-STARTPTS", "-start_number", first, shots / "%05d.png"])
    vision.masks(sorted(shots.glob("*.png")), out)
    shutil.rmtree(shots)
    size = run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", next(out.glob("*.png"))]).strip()
    black = work / "kit_mask_black.png"
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=black:s={size}", "-frames:v", "1", "-pix_fmt", "gray", black])
    last = max(out.glob("*.png"))
    for i in range(int(total * 30) + 2):
        target = out / f"{i:05d}.png"
        if not target.exists():  # past the last frame the picture is held, so the person is too
            link_or_copy(last if i > int(last.stem) and any(a <= i / 30 <= b for a, b in windows) else black, target)
    return out / "%05d.png"


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: python fx/build.py work/<stem>/plan.json OUT.mp4 [--preview T ...]")
    plan_path, out = Path(sys.argv[1]).resolve(), sys.argv[2]
    previews = sys.argv[sys.argv.index("--preview") + 1:] if "--preview" in sys.argv else []
    plan, work = json.loads(plan_path.read_text()), plan_path.parent
    kit = plan["kit"]
    cut = copy.deepcopy(plan)
    cut.update(captions=False, title={"lines": [], "until": 0}, effects=[])
    for k in ("outro", "kit"):
        cut.pop(k, None)
    cut_plan, base = work / "kit_cut.json", work / "kit_base.mp4"
    text = json.dumps(cut, ensure_ascii=False)
    if not base.exists() or not cut_plan.exists() or cut_plan.read_text() != text:  # the cut is slow; redo it only when it changed
        cut_plan.write_text(text)
        run([sys.executable, ROOT / "monti.py", "render", cut_plan, base])
    keep = json.loads((work / "timeline.json").read_text())["keep"]

    def remap(t):
        o = 0.0
        for a, b in keep:
            if t <= a:
                return o
            if t < b:
                return o + t - a
            o += b - a
        return o + t - keep[-1][1]

    def shift(x):
        if isinstance(x, dict):
            return {k: round(remap(v), 3) if k in TIMES and isinstance(v, (int, float)) and v >= 0 else shift(v) for k, v in x.items()}
        return [shift(v) for v in x] if isinstance(x, list) else x

    # Only a cut made on purpose takes a word out. Trimmed silence does not.
    gone = [c[:2] for c in plan.get("cuts", [])] + [(f["start"], f["end"]) for f in plan.get("fillers", []) if not f.get("skip")]
    words = [w for w in apply_replace(plan["words"], plan.get("replace", {})) if not any(a <= (w["start"] + w["end"]) / 2 <= b for a, b in gone)]
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) == 3 or w["start"] - cur[-1]["end"] > .4 or cur[-1]["word"][-1] in ".?!," or sum(len(x["word"]) + 1 for x in cur) + len(w["word"]) > 21):
            groups.append(cur); cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    caps = []
    for g in groups:
        ws = [{"word": w["word"], "start": round(remap(w["start"]), 3)} for w in g]
        ws[-1]["word"] = ws[-1]["word"].rstrip(".,")
        caps.append({"start": ws[0]["start"], "end": round(remap(g[-1]["end"]) + .25, 3), "words": ws})
    for a, b in zip(caps, caps[1:]):
        a["end"] = min(a["end"], b["start"])

    spoken = duration(str(base))
    total = spoken + kit.get("hold", 1.6)
    masa = [[remap(a), remap(b) if b else total + 9] for a, b in kit.get("masa", [])]
    ui = shift(kit.get("ui", []))
    for d in ui:
        if d.get("end") is None:
            d["end"] = total + 9
    back = [] if previews else [d for d in ui if d.get("behind")]
    ui = [d for d in ui if d not in back]
    data = {"fps": kit.get("fps", 15), "capStyle": kit.get("capStyle"), "total": total, "ui": ui, "masa": masa, "captions": caps, "capFull": kit.get("capFull", 1520)}
    (work / "kit.json").write_text(json.dumps(data, ensure_ascii=False))
    mov = work / "kit.mov"
    stamp = work / "kit.stamp"
    drawn = (work / "kit.json").read_text() + "".join((HERE / f).read_text() for f in ("kit.js", "kit.html", "render.mjs"))

    # the speaker: full frame, or scaled into the paper frame; on the mat the framing alternates at cuts
    p = "+".join(f"(clip((t-{a:.3f})/0.45,0,1)-clip((t-{b:.3f})/0.45,0,1))" for a, b in masa) or "0"
    p = f"st(0,{p})*0+ld(0)*ld(0)*(3-2*ld(0))"
    alt, last, o, flips = False, -9, 0.0, []
    for a, b in keep:
        if o - last > 2.0:
            alt, last = not alt, o
        if alt:
            flips.append((o, o + b - a))
        o += b - a
    z = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in flips) or "0"
    s = f"(1+({p})*(0.70-1+0.06*({z})))"
    fx, fy = kit.get("face", [512, 1150])
    fc = (f"[0:v]tpad=stop_mode=clone:stop_duration={total - spoken:.3f},split[v0][v1];"
          f"[v0]scale=w='2*trunc(540*{s})':h='2*trunc(960*{s})':eval=frame[vs];"
          f"[v1]drawbox=t=fill:color=black[bk];"
          f"[bk][vs]overlay=x='({p})*({WIN[0]}-{fx}*{s})':y='({p})*({WIN[1]}-{fy}*{s})':eval=frame[vb];")

    if previews:
        run(["node", HERE / "render.mjs", work / "kit.json", mov, *previews])
        for t in previews:
            run(["ffmpeg", "-v", "error", "-y", "-copyts", "-ss", min(float(t), spoken - .1), "-i", base, "-i", f"{mov}.{t}.png", "-filter_complex",
                 fc + "[vb][1:v]overlay=0:0:eof_action=repeat[v]", "-map", "[v]", "-frames:v", "1", work / f"kit_prev_{float(t):06.2f}.png"])
        return
    if not mov.exists() or not stamp.exists() or stamp.read_text() != drawn:
        run(["node", HERE / "render.mjs", work / "kit.json", mov])
        stamp.write_text(drawn)
    sounds = json.loads(Path(f"{mov}.sounds.json").read_text())
    layers = ["-i", base, "-i", mov]
    looks, looked = shift(kit.get("looks", [])), []
    for k, look in enumerate(looks):
        (work / f"kit_look{k}.json").write_text(json.dumps({**data, "ui": [{"type": "silme", "at": look["at"], "end": look["end"]}], "masa": [], "captions": []}))
        run(["node", HERE / "render.mjs", work / f"kit_look{k}.json", work / f"kit_look{k}.mov"])
        n_in = layers.count("-i")
        layers += ["-i", work / f"kit_look{k}.mov"]
        looked.append((n_in, LOOKS[look["style"]]))
    if looked:
        # every look is made from the untouched picture and wiped over what came before
        pre = f"[0:v]format=gbrp,split={len(looked) + 1}[lo0]" + "".join(f"[lb{k}]" for k in range(len(looked))) + ";"
        for k, (n_in, style) in enumerate(looked):
            pre += (f"[lb{k}]format=yuv444p,{style},format=gbrp[lc{k}];[{n_in}:v]format=argb,fps=30,trim=duration={spoken:.3f}[lm{k}];"
                    f"color=black:s=1080x1920:r=30:d={spoken:.3f},format=argb[lk{k}];[lk{k}][lm{k}]overlay=eof_action=repeat,format=gbrp[ln{k}];"
                    f"[lo{k}][lc{k}][ln{k}]maskedmerge[lo{k + 1}];")
        fc = pre + fc.replace("[0:v]", f"[lo{len(looked)}]", 1)
    if back:
        (work / "kit_back.json").write_text(json.dumps({**data, "ui": back, "masa": [], "captions": []}, ensure_ascii=False))
        bmov = work / "kit_back.mov"
        run(["node", HERE / "render.mjs", work / "kit_back.json", bmov])
        sounds += json.loads(Path(f"{bmov}.sounds.json").read_text())
        nb = layers.count("-i")
        layers += ["-i", bmov, "-framerate", 30, "-i", person_mask(base, work, [(d["at"], d["end"]) for d in back], total)]
        place = f"x='({p})*({WIN[0]}-{fx}*{s})':y='({p})*({WIN[1]}-{fy}*{s})':eval=frame"
        fc = fc.replace("split[v0][v1];", "split=3[v0][v1][v2];").replace("eval=frame[vb];", "eval=frame[vf];")
        fc += (f"[{nb + 1}:v]format=gray,gblur=sigma=2[pm];[v2]format=rgba[vr];[vr][pm]alphamerge,scale=w='2*trunc(540*{s})':h='2*trunc(960*{s})':eval=frame[who];"
               f"[{nb}:v]fps=30[bk2];[vf][bk2]overlay=0:0:eof_action=repeat[vg];[vg][who]overlay={place}:eof_action=pass[vb];")
    sounds = [x for x in sounds if x[0] < total and x[1] in SOUNDS]
    if sounds and not SFX_SOUNDS.exists():
        print(f"No sound kit at {SFX_SOUNDS}: effects are silent (see the setup guide).", file=sys.stderr)
        sounds = []
    speed = kit.get("speed", 1.0)
    cmd, n = ["ffmpeg", "-v", "error", "-y", *layers], layers.count("-i")
    mix = [f"[0:a]apad=pad_dur={total - spoken:.3f}[a0]"]
    for k, (t, name, vol) in enumerate(sounds):
        f, v, d = SOUNDS[name]
        cmd += ["-t", d, "-i", SFX_SOUNDS / f"{f}.wav"]
        ms = max(0, int(t * 1000))
        mix.append(f"[{n + k}:a]aresample=48000,aformat=channel_layouts=stereo,afade=t=out:st={d - .15:.2f}:d=0.15,volume={v * vol * .55:.3f},adelay={ms}|{ms}[s{k}]")
    fc += f"[1:v]fps=30[k];[vb][k]overlay=0:0:eof_action=repeat,trim=duration={total:.3f},setpts=PTS/{speed},fps=30[v];"
    if sounds:
        fc += ";".join(mix) + ";[a0]" + "".join(f"[s{k}]" for k in range(len(sounds)))
        fc += f"amix=inputs={len(sounds) + 1}:duration=first:normalize=0,atempo={speed},loudnorm=I=-14:TP=-2:LRA=11,aresample=48000[a]"
    else:
        fc += f"{mix[0]};[a0]atempo={speed},loudnorm=I=-14:TP=-2:LRA=11,aresample=48000[a]"
    run(cmd + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    print(out, f"{total / speed:.1f}s", len(sounds), "sounds")


if __name__ == "__main__":
    main()
