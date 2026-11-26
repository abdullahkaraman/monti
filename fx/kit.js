// The workshop kit: everything drawn on top of the cut, as cut paper, chalk and highlighter on the cutting mat.
// render.mjs loads a timeline into load(data) and calls seek(t) for every frame; nothing here runs on its own clock.
const W = 1080, H = 1920, INK = "#0E1F18", CREAM = "#F7F2E2", YELLOW = "#FFD60A", RED = "#FF5A52", GREEN = "#35C46F";
const COLORS = { kulak: "#FF9F43", goz: "#5AC8FA", eller: "#FF6B6B", kutu: "#B39DFF", durbun: "#FF8AD8", defter: "#FFD60A", bicak: "#2EE6C5", pergel: "#C6FF4D",
                 sari: YELLOW, krem: CREAM, kirmizi: RED, yesil: GREEN };
const root = document.getElementById("root");
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const ease = x => 1 - (1 - clamp(x)) ** 3;
const smooth = x => { x = clamp(x); return x * x * (3 - 2 * x); };
const over = x => { x = clamp(x) - 1; return 1 + 2.7 * x ** 3 + 1.7 * x ** 2; };  // ease-out with a small overshoot
const rand = s => { const x = Math.sin(s * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const jit = (s, a) => (rand(s) - 0.5) * 2 * a;
const el = (tag, parent, css = "", html = "") => { const e = document.createElement(tag); e.style.cssText = css; e.innerHTML = html; parent.appendChild(e); return e; };
const color = c => COLORS[c] || c || YELLOW;

// A piece of hand-cut paper: uneven corners, an ink edge and a hard shadow. Redrawn per "boil" step.
function cutPaper(w, h, fill, seed, o = {}) {
  const k = o.edge ?? 7, s = o.skew ?? 0.16 * h, sh = o.shadow ?? 11, j = n => jit(seed + n, o.rough ?? 5);
  const p = [[s + j(1), j(2)], [w + j(3), j(4)], [w - s + j(5), h + j(6)], [j(7), h + j(8)]].map(q => q.map(v => v.toFixed(1)).join(",")).join(" ");
  return `<polygon points="${p}" transform="translate(${sh * .75},${sh})" fill="${INK}" stroke="${INK}" stroke-width="${k}" stroke-linejoin="round"/>` +
         `<polygon points="${p}" fill="${fill}" stroke="${INK}" stroke-width="${k}" stroke-linejoin="round"/>`;
}

function tag(parent, text, o = {}) {
  const size = o.size || 76, e = el("div", parent, `font-size:${size}px;padding:${size * .2}px ${size * .48}px ${size * .24}px;color:${o.ink || INK};${o.css || ""}`);
  e.className = "tag" + (o.script ? " script" : "");
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); e.appendChild(svg);
  el("span", e, "", text);
  e.paint = (seed, fill = color(o.color)) => { svg.innerHTML = cutPaper(e.offsetWidth, e.offsetHeight, fill, seed, o); };
  e.paint(o.seed || 1);
  return e;
}

const strokeAnim = (p, len) => `stroke-dasharray:${len};stroke-dashoffset:${len * (1 - p)}`;
// a red marker cross, or a green badge with a tick, drawn over a tag
function mark(e, kind) {
  const w = e.offsetWidth, h = e.offsetHeight;
  const s = el("div", e, "position:absolute;inset:0"); s.className = "abs";
  s.draw = p => {
    if (p <= 0) return s.innerHTML = "";
    if (kind === "x") {
      const L = Math.hypot(w, h) + 60;
      s.innerHTML = `<svg class="abs" width="${w}" height="${h}" fill="none" stroke-linecap="round">` +
        [[INK, 22], [RED, 13]].map(([c, sw]) => `<path d="M-14 ${h * .74} Q${w * .5} ${h * .42} ${w + 14} ${h * .22}" stroke="${c}" stroke-width="${sw}" style="${strokeAnim(ease(p * 1.6), L)}"/>` +
        `<path d="M${w * .06} ${h * .12} Q${w * .5} ${h * .62} ${w * .97} ${h * .92}" stroke="${c}" stroke-width="${sw}" style="${strokeAnim(ease(p * 1.6 - .6), L)}"/>`).join("") + `</svg>`;
    } else {
      const k = over(p * 1.4);
      s.innerHTML = `<svg class="abs" style="left:${w - 30}px;top:-30px;transform:scale(${k}) rotate(${(1 - k) * -60}deg);transform-origin:32px 32px" width="64" height="64">
        <circle cx="36" cy="37" r="30" fill="${INK}"/><circle cx="32" cy="32" r="29" fill="${GREEN}" stroke="${INK}" stroke-width="6"/>
        <path d="M18 33 L28 43 L46 22" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" style="${strokeAnim(ease(p * 2 - .6), 60)}"/></svg>`;
    }
  };
  return s;
}

let T, MAT, MATBG, FRAME, CAPS = [], ITEMS = [], SND = [];
const snd = (t, name, vol = 1) => SND.push([t, name, vol]);

// ---------- layout: full frame <-> the speaker in a paper frame on the mat ----------
const WIN = { x: 185, y: 862, w: 710, h: 790 };
function matAt(t) {  // 0 = full frame, 1 = on the mat
  let p = 0;
  for (const [a, b] of T.masa) p = Math.max(p, smooth((t - a) / 0.45) * (1 - smooth((t - b) / 0.45)));
  return p;
}
function drawMat(t, boil) {
  const p = matAt(t);
  MAT.style.display = FRAME.style.display = p > 0.002 ? "" : "none";
  if (p <= 0.002) return;
  const l = (a, b) => a + (b - a) * p, x = l(0, WIN.x), y = l(0, WIN.y), w = l(W, WIN.w), h = l(H, WIN.h), j = n => p * jit(40 + n, 7);
  const q = [[x + j(1), y + j(2)], [x + w + j(3), y + j(4)], [x + w + j(5), y + h + j(6)], [x + j(7), y + h + j(8)]].map(v => v.map(n => n.toFixed(1)));
  MAT.style.clipPath = `path(evenodd,"M0 0H${W}V${H}H0Z M${q.map(v => v.join(" ")).join("L")}Z")`;
  const pts = q.map(v => v.join(",")).join(" ");
  const tape = (cx, cy, r, s) => `<g transform="translate(${cx},${cy}) rotate(${r})" opacity="${clamp((p - .85) / .15)}"><path d="M-62 -21 l6 7 -6 7 6 7 -6 7 6 7 -4 7 H62 l-6 -7 6 -7 -6 -7 6 -7 -6 -7 4 -7Z" fill="rgba(255,236,150,.82)"/><path d="M-40 -8H40" stroke="rgba(255,255,255,.35)" stroke-width="8"/></g>`;
  FRAME.innerHTML = `<polygon points="${pts}" fill="none" stroke="${INK}" stroke-width="${34 * p}" stroke-linejoin="round" transform="translate(${9 * p},${12 * p})" style="clip-path:path(evenodd,'M-50 -50H1180V2020H-50Z M${q.map(v => v.join(" ")).join("L")}Z')"/>
    <polygon points="${pts}" fill="none" stroke="${INK}" stroke-width="${36 * p}" stroke-linejoin="round"/><polygon points="${pts}" fill="none" stroke="${CREAM}" stroke-width="${22 * p}" stroke-linejoin="round"/>` +
    tape(WIN.x + 20, WIN.y + 6, -38) + tape(WIN.x + WIN.w - 20, WIN.y + 6, 38) + tape(WIN.x + WIN.w - 14, WIN.y + WIN.h - 4, -36) + tape(WIN.x + 14, WIN.y + WIN.h - 4, 34);
}

// ---------- pieces ----------
// Each builder returns { el, at, end, draw(u, o, t, boil) }: u = seconds since it came, o = seconds until it goes.
const place = (x, y) => { const c = el("div", root, `transform:translate(${x}px,${y}px)`); c.className = "c"; const i = el("div", c); i.className = "in"; return [c, i]; };
const pose = (e, { x = 0, y = 0, r = 0, s = 1, a = 1 }) => { e.style.transform = `translate(${x}px,${y}px) rotate(${r}deg) scale(${s})`; e.style.opacity = a; };
const inOut = (u, o, boil, seed, from = {}) => {  // slap in, live a little, drop out
  const k = over(u / 0.28), g = clamp(1 - o / 0.22);
  return { s: (0.35 + 0.65 * k), r: (from.r || 0) + (1 - k) * (from.spin ?? -16) + jit(seed + boil, 0.55), a: clamp(u / 0.08) * (1 - g * g), y: g * g * 70, x: 0 };
};

const BUILD = {
  // title lockup: { lines: [{ text, kind: "big"|"small"|"script"|"tag", at, color, size, dx, dy, r }], x, y }
  lockup(d) {
    const parts = d.lines.map((l, i) => {
      const [c, inn] = place(d.x + (l.dx || 0), d.y + (l.dy || 0)); let e;
      if (l.kind === "tag") e = tag(inn, l.text, { size: l.size || 72, color: l.color, seed: 5 + i });
      else {
        const f = l.kind === "script" ? `font-family:'Caveat Brush';font-style:normal;font-weight:400;` : l.kind === "small" ? `font-style:normal;font-weight:800;letter-spacing:.16em;` : "";
        e = el("div", inn, `${f}font-size:${l.size}px;line-height:.95;color:${color(l.color || "krem")};-webkit-text-stroke:${l.size * .12}px ${INK};paint-order:stroke fill;filter:drop-shadow(0 ${l.size * .05}px 0 ${INK})`, l.text);
      }
      snd(l.at, l.kind === "big" ? "darbe" : l.kind === "tag" ? "kagit" : "kalem", l.kind === "big" ? .9 : .6);
      return { e, l };
    });
    return { draw(u, o, t, boil) { for (const [i, { e, l }] of parts.entries()) {
      const v = t - l.at; if (v < 0) { e.style.opacity = 0; continue; }
      const q = inOut(v, o, boil, 70 + i * 9, { r: l.r || 0, spin: l.kind === "tag" ? 22 : -10 });
      if (l.kind === "big") q.s = 1 + 1.1 * (1 - ease(v / .16));
      if (l.kind === "script") { e.style.clipPath = `inset(-40% ${100 - 110 * ease(v / .4)}% -40% -10%)`; q.s = 1; }
      pose(e, q); if (e.paint) e.paint(5 + i + boil * .01);
    } } };
  },
  // a wrap of tags, each with its own mark: { items: [{ text, at, mark: "x"|"ok", markAt, color, size }], x, y, width, dropAt }
  tags(d) {
    const [c, inn] = place(d.x, d.y); inn.style.cssText += `;flex-wrap:wrap;justify-content:center;gap:26px 30px;width:${d.width || 900}px;white-space:normal`;
    const list = d.items.map((it, i) => { const e = tag(inn, it.text, { size: it.size || d.size || 78, color: it.color || d.color || "krem", seed: 11 + i * 3 });
      const m = it.mark ? mark(e, it.mark) : null; snd(it.at, "kagit", .7); if (m) snd(it.markAt, it.mark === "x" ? "cizik" : "tik", .8); return { e, it, m, i }; });
    return { draw(u, o, t, boil) { for (const { e, it, m, i } of list) {
      const v = t - it.at; if (v < 0) { e.style.opacity = 0; continue; }
      const q = inOut(v, o, boil, 100 + i * 7, { r: jit(i + 3, 4), spin: i % 2 ? 18 : -18 });
      if (d.dropAt && t > d.dropAt + i * .05) { const f = t - d.dropAt - i * .05; q.y += 1900 * f * f - 260 * f; q.r += jit(i + 9, 70) * f; q.x += jit(i + 5, 160) * f; q.a *= clamp(1.3 - f * 1.5); }
      pose(e, q); if (m) m.draw((t - it.markAt) / .4);
    } } };
  },
  // one label, optionally struck out and replaced: { text, sub, at, strikeAt, then: { text, at, color }, color, size, x, y }
  label(d) {
    const [c, inn] = place(d.x, d.y), e = tag(inn, d.text, { size: d.size || 110, color: d.color, seed: 21 }), m = d.strikeAt ? mark(e, "x") : null;
    snd(d.at, "kagit", .8); if (d.strikeAt) snd(d.strikeAt, "cizik", .9);
    let sub; if (d.sub) { const [, i2] = place(d.x + (d.subDx || 0), d.y + (d.size || 110) * 1.05); sub = el("div", i2, `font-family:'Caveat Brush';font-style:normal;font-weight:400;font-size:${d.subSize || 66}px;color:${color(d.subColor || "sari")};-webkit-text-stroke:9px ${INK};paint-order:stroke fill`, d.sub); if (d.subAt) snd(d.subAt, "kalem", .7); }
    return { draw(u, o, t, boil) { pose(e, inOut(u, o, boil, 130, { r: d.r ?? -2 })); e.paint(21 + boil * .01); if (m) m.draw((t - d.strikeAt) / .4);
      if (sub) { const v = t - (d.subAt || d.at + .25); sub.style.clipPath = `inset(-30% ${100 - 112 * ease(v / .45)}% -30% -10%)`; pose(sub, { r: -3 + jit(140 + boil, .4), a: (v > 0 ? 1 : 0) * clamp(o / .15) }); } } };
  },
  // a chalk drawing that is drawn on, then breathes: { img, x, y, w }
  art(d) {
    const [c, inn] = place(d.x, d.y), e = el("img", inn, `width:${d.w}px;display:block`); e.src = `assets/${d.img}.png`; snd(d.at, "tebesir", .55);
    return { draw(u, o, t, boil) { const p = ease(u / .6); e.style.webkitMaskImage = `linear-gradient(105deg,#000 ${p * 125 - 25}%,transparent ${p * 125}%)`;
      pose(e, { s: .94 + .06 * over(u / .5) + .008 * Math.sin(t * 3), r: (d.r || 0) + jit(150 + boil, .35), a: clamp(o / .18), y: 5 * Math.sin(t * 2.4) }); } };
  },
  // steps that get done as they are said: { steps: [{ title, sub, at, done, color }], x, y }
  flow(d) {
    const n = d.steps.length, gap = d.gap || 300;
    const st = d.steps.map((s, i) => { const [c, inn] = place(d.x + (i - (n - 1) / 2) * gap, d.y); const e = tag(inn, s.title, { size: d.size || 72, color: "krem", seed: 31 + i * 5 }), m = mark(e, "ok");
      const [, i2] = place(d.x + (i - (n - 1) / 2) * gap, d.y + 92); const sub = el("div", i2, `font-family:'Caveat Brush';font-style:normal;font-weight:400;font-size:54px;color:${color(s.color)};-webkit-text-stroke:8px ${INK};paint-order:stroke fill`, s.sub);
      snd(d.at + i * .1, "kagit", .5); snd(s.at, "darbe2", .5); snd(s.done, "tik", .9); return { e, m, s, sub, i }; });
    const arrows = document.createElementNS("http://www.w3.org/2000/svg", "svg"); arrows.setAttribute("class", "abs"); arrows.style.cssText = "left:0;top:0"; root.appendChild(arrows);
    return { draw(u, o, t, boil) {
      arrows.innerHTML = u < 0 || o < 0 ? "" : st.slice(0, -1).map(({ s, e, i }) => { const a = d.x + (i - (n - 1) / 2) * gap + e.offsetWidth / 2 + 10, b = d.x + (i + 1 - (n - 1) / 2) * gap - st[i + 1].e.offsetWidth / 2 - 14, p = ease((t - st[i + 1].s.at + .25) / .3);
        return p > 0 ? `<path d="M${a} ${d.y} q${(b - a) / 2} -26 ${(b - a) * p} 0" fill="none" stroke="${CREAM}" stroke-width="7" stroke-linecap="round" stroke-dasharray="14 12" opacity="${clamp(o / .2)}"/>` : ""; }).join("");
      for (const { e, m, s, sub, i } of st) { const v = u - i * .1, w = t - s.at, q = inOut(v, o, boil, 160 + i * 5, { r: jit(i + 31, 3) });
        if (w >= 0) { q.s *= 1 + .22 * Math.exp(-6 * w) * Math.cos(w * 18); q.y -= 4; }
        pose(e, q); e.paint(31 + i * 5 + boil * .01, w >= 0 ? color(s.color) : "#8FA79B"); m.draw((t - s.done) / .4);
        sub.style.clipPath = `inset(-30% ${100 - 112 * ease(w / .35)}% -30% -10%)`; pose(sub, { a: (w > 0 ? 1 : 0) * clamp(o / .15), r: -2 + jit(170 + i + boil, .5) }); } } };
  },
  // a sound strip with junk cut out of it: { cuts: [{ text, at }], words: [...], x, y }
  strip(d) {
    const [c, inn] = place(d.x, d.y); const box = el("div", inn, "position:relative;width:920px;height:190px"); const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("width", 920); svg.setAttribute("height", 190); svg.style.overflow = "visible"; box.appendChild(svg);
    const segs = d.segs; let X = 0; for (const s of segs) { s.x0 = X; X += s.w; }
    snd(d.at, "bant", .7); for (const s of segs) if (s.cutAt) { snd(s.cutAt, "makas", 1); snd(s.cutAt + .28, "darbe2", .5); }
    return { draw(u, o, t, boil) {
      const q = inOut(u, o, boil, 190, { r: 0, spin: -6 }); pose(box, q);
      let x = 0, out = ""; const closed = segs.map(s => s.cutAt ? smooth((t - s.cutAt - .28) / .22) : 0), total = segs.reduce((a, s, i) => a + s.w * (1 - closed[i]), 0); x = (920 - total) / 2;
      segs.forEach((s, i) => {
        const v = s.cutAt ? t - s.cutAt : -1, f = Math.max(0, v - .18), junk = !!s.cutAt, w = s.w, y = junk && f > 0 ? 1500 * f * f - 200 * f : 0, r = junk ? f * 140 : 0;
        const bars = Array.from({ length: Math.floor((w - 24) / 15) }, (_, k) => { const h = (junk ? 22 + 18 * rand(i * 50 + k) : 26 + 78 * rand(i * 50 + k) * Math.abs(Math.sin(k * .5 + i))) ; return `<rect x="${14 + k * 15}" y="${78 - h / 2}" width="8" height="${h}" rx="4" fill="${INK}" opacity="${junk ? .55 : .8}"/>`; }).join("");
        const g = `<g transform="translate(${x + (junk ? f * 60 : 0)},${y}) rotate(${r} ${w / 2} 80)" opacity="${junk ? clamp(1.25 - f * 1.6) : 1}">${cutPaper(w - 8, 156, junk ? RED : s.color ? color(s.color) : CREAM, 200 + i, { skew: 0, rough: 3, shadow: 9 })}${bars}<text x="${(w - 8) / 2}" y="142" text-anchor="middle" font-family="Caveat Brush" font-style="normal" font-weight="400" font-size="44" fill="${INK}">${s.text}</text></g>`;
        out += g; if (junk && v > -.35 && v < .3) { const cl = Math.abs(Math.sin((v + .35) * 12)) * 24; const sx = x + w / 2; out += `<g transform="translate(${sx},${-70 + 60 * ease((v + .35) / .3)})"><g transform="rotate(${cl})"><path d="M0 0 L-12 108 L6 112Z" fill="#E8EFEA" stroke="${INK}" stroke-width="6" stroke-linejoin="round"/></g><g transform="rotate(${-cl})"><path d="M0 0 L12 108 L-6 112Z" fill="#E8EFEA" stroke="${INK}" stroke-width="6" stroke-linejoin="round"/></g><circle cx="-30" cy="-40" r="26" fill="none" stroke="${RED}" stroke-width="15"/><circle cx="30" cy="-40" r="26" fill="none" stroke="${RED}" stroke-width="15"/><path d="M-18 -18L0 4L18 -18" fill="none" stroke="${RED}" stroke-width="13"/></g>`; }
        x += w * (1 - closed[i]);
      });
      svg.innerHTML = out;
    } };
  },
  // a notebook page where remarks become rules: { lines: [{ text, at, stampAt, good }], x, y, w }
  note(d) {
    const w = d.w || 800, lh = 108, h = 70 + d.lines.length * lh, [c, inn] = place(d.x, d.y), box = el("div", inn, `position:relative;width:${w}px;height:${h}px`);
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); bg.setAttribute("class", "abs"); box.appendChild(bg); snd(d.at, "sayfa", .9);
    const L = d.lines.map((l, i) => { const e = el("div", box, `position:absolute;left:104px;top:${44 + i * lh}px;font-family:'Caveat Brush';font-style:normal;font-weight:400;font-size:72px;line-height:1.2;white-space:nowrap;color:#1B3A6B`, l.text);
      const holder = el("div", box, `position:absolute;right:26px;top:${40 + i * lh}px`); const s = el("div", holder, `font-size:56px;line-height:1;padding:6px 18px 10px;border:7px solid ${l.good ? "#1F9D55" : "#D7263D"};color:${l.good ? "#1F9D55" : "#D7263D"};border-radius:10px;background:rgba(255,255,255,.35)`, l.stamp || "KURAL");
      snd(l.at, "kalem", .8); snd(l.stampAt, "damga", 1); return { e, s, l }; });
    return { draw(u, o, t, boil) {
      const q = inOut(u, o, boil, 220, { r: d.r ?? -2, spin: 8 }); pose(box, q);
      let g = cutPaper(w, h, "#FFE66B", 220 + boil * .01, { skew: 0, rough: 6, shadow: 14 });
      for (let i = 0; i < d.lines.length; i++) g += `<path d="M70 ${122 + i * lh}H${w - 24}" stroke="rgba(60,90,140,.28)" stroke-width="4"/>`;
      g += `<path d="M84 14V${h - 14}" stroke="rgba(220,60,60,.45)" stroke-width="4"/>`;
      for (let y = 40; y < h - 20; y += 62) g += `<circle cx="34" cy="${y}" r="13" fill="#163B2E"/><path d="M34 ${y} C-26 ${y - 26} -26 ${y + 20} 30 ${y + 4}" fill="none" stroke="#DDE6E0" stroke-width="8" stroke-linecap="round"/>`;
      bg.innerHTML = g;
      L.forEach(({ e, s, l }, i) => { const v = t - l.at, k = t - l.stampAt; e.style.clipPath = `inset(-20% ${100 - 108 * smooth(v / .55)}% -20% 0)`; e.style.opacity = v > 0 ? 1 : 0;
        const z = 1 + 1.8 * (1 - ease(k / .12)); s.style.transform = `rotate(${-9 + jit(i + 60, 4)}deg) scale(${z})`; s.style.opacity = k > 0 ? clamp(k / .06) * .92 : 0; });
    } };
  },
  // the close, on live footage: Monti's own claw presses the buttons: { buttons: [{ text, then, at, press, color }], x, y, site, siteAt }
  cta(d) {
    const B = d.buttons.map((b, i) => { const [c, inn] = place(d.x, d.y + i * 165); const e = tag(inn, b.text, { size: 92, color: b.color || "krem", seed: 41 + i, skew: 22, shadow: 16 }); const sp = e.querySelector("span"); snd(b.at, "pop", .8); snd(b.press, "tikla", 1); snd(b.press + .06, "parilti", .5); return { c, e, sp, b, i, w: 0 }; });
    const [, ci] = place(0, 0); const claw = el("div", ci, "position:relative"); el("div", claw, `position:absolute;left:68px;top:-560px;width:20px;height:590px;background:${CREAM};border:6px solid ${INK};border-radius:10px;transform:rotate(14deg);transform-origin:50% 100%`); const ci2 = el("img", claw, "width:150px;display:block;position:relative;filter:drop-shadow(0 0 0 #0E1F18) drop-shadow(5px 0 0 #0E1F18) drop-shadow(-5px 0 0 #0E1F18) drop-shadow(0 5px 0 #0E1F18)"); ci2.src = "assets/kiskac.png";
    const burst = document.createElementNS("http://www.w3.org/2000/svg", "svg"); burst.setAttribute("class", "abs"); burst.style.cssText = "left:0;top:0"; root.appendChild(burst);
    const [, si] = place(d.x, d.y + 70); const site = el("div", si, "display:flex;flex-direction:column;align-items:center;gap:0"); const s1 = tag(site, d.site, { size: 104, color: "sari", seed: 51, skew: 20, shadow: 16 }); const s2 = el("div", site, `margin-top:30px;font-family:'Caveat Brush';font-style:normal;font-weight:400;font-size:82px;color:${CREAM};-webkit-text-stroke:11px ${INK};paint-order:stroke fill`, d.note || "link bio'da"); snd(d.siteAt, "darbe", .8);
    return { draw(u, o, t, boil) {
      let cx = 1250, cy = d.y - 300, shown = false, g = "";
      for (const { e, sp, b, i } of B) { const v = t - b.at, k = t - b.press, leave = t - d.siteAt, q = inOut(v, -leave < 0 ? .0001 + Math.max(0, .22 - leave) : 9, boil, 240 + i * 7, { r: i ? 2 : -2 });
        if (k >= 0) { sp.textContent = b.then; q.s *= 1 - .16 * Math.exp(-((k - .03) ** 2) / .002) + .12 * Math.exp(-7 * k) * Math.sin(k * 24); } else sp.textContent = b.text;
        pose(e, q); if (v < 0) e.style.opacity = 0; e.paint(41 + i + boil * .01, k >= 0 ? color(b.after || "yesil") : color(b.color || "krem"));
        const near = smooth(clamp((t - b.press + .5) / .42)), bx = d.x + e.offsetWidth / 2 + 8, by = d.y + i * 165 + 78;
        if (t > b.press - .5 && leave < .2) { shown = true; const px = i ? d.x + B[0].e.offsetWidth / 2 + 60 : 1250, py = i ? d.y + 40 : d.y - 300; const off = ease((k - .16) / .25); cx = px + (bx - px) * near + 70 * off; cy = py + (by - py) * near + 26 * Math.exp(-((k) ** 2) / .003); }
        if (k > 0 && k < .6) for (let n = 0; n < 14; n++) { const a = n / 14 * 6.283 + i, r0 = 90 + 330 * ease(k / .5), r1 = r0 + 46 * (1 - k / .6), c2 = [YELLOW, "#5AC8FA", "#FF8AD8", "#C6FF4D"][n % 4]; g += `<path d="M${d.x + Math.cos(a) * r0 * 1.5} ${d.y + i * 165 + Math.sin(a) * r0 * .62} L${d.x + Math.cos(a) * r1 * 1.5} ${d.y + i * 165 + Math.sin(a) * r1 * .62}" stroke="${c2}" stroke-width="${13 * (1 - k / .6)}" stroke-linecap="round"/>`; } }
      burst.innerHTML = g; const away = ease((t - d.siteAt) / .25); pose(claw, { x: cx + 500 * away, y: cy - 500 * away, r: -8, a: t > B[0].b.press - .5 ? 1 : 0 });
      const w = t - d.siteAt; pose(s1, { ...inOut(w, 9, boil, 260, { r: -3, spin: 20 }), a: w > 0 ? 1 : 0 }); s1.paint(51 + boil * .01); s2.style.clipPath = `inset(-30% ${100 - 112 * ease((w - .2) / .35)}% -30% -10%)`; s2.style.opacity = w > .2 ? 1 : 0; pose(s2, { r: -3, a: w > .2 ? 1 : 0 });
    } };
  },
  // a row of paper cards that rises up behind the speaker; the one being talked about is in colour, the rest wait in grey:
  // { x, y, w, h, gap, cards: [{ text, sub, color, mark: "x"|"ok", markAt }], focus: [{ at, card }] }   give it "behind": true
  raf(d) {
    const n = d.cards.length, w = d.w || 300, h = d.h || 400, gap = d.gap ?? 28; snd(d.at, "hisir", 1);
    const L = d.cards.map((k, i) => {
      const [, inn] = place(d.x + (i - (n - 1) / 2) * (w + gap), d.y), box = el("div", inn, `position:relative;width:${w}px;height:${h}px;display:flex;flex-direction:column;align-items:center;padding-top:${h * .12}px`);
      const bg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); bg.setAttribute("class", "abs"); bg.style.cssText = "left:0;top:0"; box.appendChild(bg);
      el("div", box, `position:relative;line-height:1;font-size:${k.size || 130}px`, k.text);
      if (k.sub) el("div", box, "position:relative;font-family:'Caveat Brush';font-style:normal;font-weight:400;font-size:58px;line-height:1.1", k.sub);
      const m = k.mark ? mark(box, k.mark) : null;
      snd(d.at + .08 + i * .06, "kagit", .6); if (k.markAt != null) snd(k.markAt, k.mark === "x" ? "cizik" : "tik", .9);
      return { box, bg, k, m };
    });
    const heat = (i, t) => d.focus.reduce((h, f) => { const p = smooth((t - f.at) / .12); return h + ((f.card === i ? 1 : 0) - h) * p; }, 0);
    return { draw(u, o, t, boil) {
      L.forEach(({ box, bg, k, m }, i) => {
        const v = over((u - i * .06) / .36), g = smooth(1 - o / .3), hot = heat(i, t);
        pose(box, { y: (1 - v) * 620 + g * 620 - 26 * hot, r: (i - (n - 1) / 2) * 3.5 + (1 - v) * (i % 2 ? 9 : -9) + jit(300 + i * 9 + boil, .4), s: 1 + .05 * hot, a: u < i * .06 ? 0 : 1 });
        bg.innerHTML = cutPaper(w, h, "#CFCDC2", 300 + i * 7 + boil * .01, { skew: 0, rough: 7, shadow: 14 }) + `<g opacity="${hot}">${cutPaper(w, h, color(k.color), 300 + i * 7 + boil * .01, { skew: 0, rough: 7, shadow: 0 })}</g>`;
        if (m) m.draw((t - k.markAt) / .4);
      });
    } };
  },
  // the edit itself as a paper strip running under a fixed needle; each stretch lights up while it plays and is ticked when done:
  // { y, segs: [{ text, color, at }] }   the last stretch ends at `until`, or with the piece
  zaman(d) {
    const box = el("div", root, "position:absolute;left:0;top:0"), bg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); bg.setAttribute("class", "abs"); bg.setAttribute("width", W); bg.setAttribute("height", H); box.appendChild(bg);
    const pps = d.pps || 130, h = d.h || 120, S = d.segs.map((s, i) => ({ ...s, to: d.segs[i + 1]?.at ?? (d.until ?? d.end) }));
    const L = S.map(s => el("div", box, `position:absolute;top:${d.y}px;height:${h}px;display:flex;align-items:center;justify-content:center;font-size:66px;white-space:nowrap`, s.text)); S.forEach((s, i) => i && snd(s.at, "tik", .8));
    return { draw(u, o, t, boil) {
      const x = v => W / 2 + (v - t) * pps, dy = (1 - over(u / .4)) * 300 + smooth(1 - o / .25) * 300; let g = "";
      S.forEach((s, i) => { const a = x(s.at), w = (s.to - s.at) * pps, on = smooth((t - s.at) / .12), done = t >= s.to - .02;
        g += `<g transform="translate(${a.toFixed(1)},${d.y + dy})">${cutPaper(w - 10, h, on > .5 ? color(s.color) : "#CFCDC2", 400 + i * 7 + boil * .01, { skew: 0, rough: 4, shadow: 10 })}` + (done ? `<path transform="translate(${w - 74},${h * .2})" d="M0 32 L18 54 L52 4" fill="none" stroke="${INK}" stroke-width="13" stroke-linecap="round" stroke-linejoin="round"/>` : "") + `</g>`;
        L[i].style.left = `${a}px`; L[i].style.width = `${w - 10 - (done ? 70 : 0)}px`; L[i].style.transform = `translateY(${dy}px)`; });
      g += `<g transform="translate(${W / 2},${d.y + dy})"><path d="M0 -14V${h + 22}" stroke="${INK}" stroke-width="20" stroke-linecap="round"/><path d="M0 -14V${h + 22}" stroke="${RED}" stroke-width="9" stroke-linecap="round"/><path d="M-30 -52H30L0 -8Z" fill="${RED}" stroke="${INK}" stroke-width="7" stroke-linejoin="round"/></g>`;
      bg.innerHTML = g;
    } };
  },
  // ---- "dergi": calm editorial pieces, no paper. Bone, near-black and one accent; type does the work. ----
  // a colour or backdrop image behind the speaker, wiped in like a look: { color, img, fly, blur, dim, cut, outAt }   behind: true
  fon(d) {
    const e = el("div", root, `position:absolute;inset:0;overflow:hidden;background:${d.color || "#14130F"};${d.fly ? "perspective:1100px;" : ""}`);
    let im = null;
    if (d.img) {
      im = el("img", e, d.fly
        ? `position:absolute;left:-20px;top:-60px;width:1120px;height:auto;border-radius:18px;box-shadow:0 30px 90px rgba(0,0,0,.35);transform-origin:50% 25%;`
        : `position:absolute;inset:0;width:100%;height:100%;object-fit:cover;${d.blur ? `filter:blur(${d.blur}px);` : ""}`);
      im.src = d.img;
      if (d.dim) el("div", e, `position:absolute;inset:0;background:rgba(10,10,12,${d.dim})`);
    }
    const edge = (v, w) => { const p = smooth(w / .55) * 1.5 - .25; return (p * W + (960 - v) * .28).toFixed(1); };
    return { draw(u, o, t) { const w = d.outAt == null ? -1 : t - d.outAt, l = v => w < 0 ? -400 : edge(v, w); e.style.clipPath = `polygon(${l(0)}px 0, ${edge(0, u)}px 0, ${edge(1920, u)}px 100%, ${l(1920)}px 100%)`; e.style.opacity = d.cut ? 1 : smooth(o / .3); if (im) im.style.transform = d.fly ? `rotateX(24deg) rotateZ(-4deg) translateY(${(-u * 260).toFixed(1)}px) scale(1.12)` : `scale(${(1.03 + 0.04 * smooth(u / 3.5)).toFixed(4)})`; } };
  },
  // type that rises letter by letter: { streaks, lines: [{ text, at, out, font: serif|italik|grotesk|mono, chrome, size, x, y, color, blend }] }
  yazi(d) {
    let st = null;
    if (d.streaks) { st = document.createElementNS("http://www.w3.org/2000/svg", "svg"); st.setAttribute("class", "abs"); st.style.cssText = "left:0;top:0"; st.setAttribute("width", W); st.setAttribute("height", H); root.appendChild(st); }
    const L = d.lines.map(l => { const e = el("div", root, `left:${l.x ?? 540}px;top:${l.y}px;font-size:${l.size}px;color:${l.color || "#F3EEE3"};${l.blend ? "mix-blend-mode:" + l.blend : ""}`); e.className = "d " + (l.font || "serif") + (l.chrome ? " chrome" : "");
      const B = [...l.text].map(c => el("b", e, "", c)); if (l.ses) snd(l.at, l.ses, l.vol || .8); return { l, B }; });
    return { draw(u, o, t) {
      if (st) { const p = ease(u / .65), a = p * (d.cut ? 1 : smooth(o / .25)), y0 = L[0]?.l.y ?? 425;
        st.innerHTML = `<defs><filter id="glw"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>` +
          `<g filter="url(#glw)" fill="none" stroke-linecap="round" opacity="${(a * .85).toFixed(3)}">` +
          `<path d="M-40 ${y0 + 135} Q360 ${y0 - 45} 1120 ${y0 + 75}" stroke="#FFFFFF" stroke-width="5" style="${strokeAnim(p, 1300)}"/>` +
          `<path d="M-40 ${y0 + 95} Q560 ${y0 + 175} 1120 ${y0 - 25}" stroke="#D9E2EC" stroke-width="3" opacity=".7" style="${strokeAnim(ease((u - .08) / .65), 1300)}"/>` +
          `<path d="M-40 ${y0 + 165} Q490 ${y0 + 15} 1120 ${y0 + 145}" stroke="#FFD60A" stroke-width="2.5" opacity=".55" style="${strokeAnim(ease((u - .14) / .65), 1300)}"/></g>`; }
      for (const { l, B } of L) B.forEach((b, i) => {
      const v = (t - l.at - i * (l.step ?? .028)) / .42, p = v <= 0 ? 0 : 1 - Math.pow(2, -9 * Math.min(1, v)), q = l.out == null && d.cut ? 0 : smooth((t - (l.out ?? d.end) + .26 - i * .006) / .24);
      b.style.opacity = p * (1 - q); b.style.transform = `translateY(${(1 - p) * 62 - q * 40}%) rotate(${(1 - p) * 5}deg)`; b.style.filter = p > .99 && !q ? "" : `blur(${((1 - p) * 14 + q * 10).toFixed(1)}px)`; }); } };
  },
  // VCR / VHS tape HUD overlay (pair with look "vcr"): { label }
  vcr(d) {
    const e = el("div", root); e.className = "vcr";
    return { draw(u, o, t) {
      const s = Math.floor(t), f = Math.floor((t - s) * 30), pad = n => String(n).padStart(2, "0");
      const dot = Math.floor(t * 2) % 2 === 0 ? `<span style="color:#FF5A52">●</span> ` : `<span style="opacity:.15;color:#FF5A52">●</span> `;
      e.style.opacity = clamp(u / .12) * clamp(o / .12);
      e.innerHTML = `${dot}${d.label || "VCR TAPE"}<br>00:${pad(Math.floor(s / 60))}:${pad(s % 60)}:${pad(f)}`;
    } };
  },
  // the sentence typed to Monti: { text, at, sendAt, end, y, label }
  komut(d) {
    const e = el("div", root, `top:${d.y || 250}px`); e.className = "komut"; el("div", e, "", d.label || "MONTİ'YE").className = "et"; const m = el("div", e); m.className = "me"; const g = el("div", e); g.className = "dg";
    const start = d.at + .3, type = d.sendAt - .22 - start; snd(d.at, "hisir", .5); for (let i = 0; i < d.text.length; i += 2) snd(start + type * i / d.text.length, "tus", .5); snd(d.sendAt, "gonder", .8);
    return { draw(u, o, t) {
      const p = 1 - Math.pow(2, -9 * Math.min(1, u / .5)), q = smooth(1 - o / .24), n = Math.round(clamp((t - start) / type) * d.text.length), sent = t >= d.sendAt, k = t - d.sendAt;
      e.style.transform = `translateY(${(1 - p) * -120 - q * 70}px) scale(${.94 + .06 * p})`; e.style.opacity = p * (1 - q); e.style.filter = q ? `blur(${q * 12}px)` : "";
      m.style.color = sent ? "#A39C8D" : "#14130F"; m.innerHTML = d.text.slice(0, n) + (!sent && Math.floor(t * 2.4) % 2 === 0 ? `<span style="display:inline-block;width:4px;height:52px;margin-left:5px;background:#14130F;vertical-align:-8px"></span>` : "");
      g.style.transform = `scale(${sent ? 1 - .16 * Math.exp(-((k - .05) ** 2) / .003) : 1})`;
      g.innerHTML = sent ? `<svg width="96" height="96"><circle cx="48" cy="48" r="20" fill="none" stroke="#6b665b" stroke-width="7"/><circle cx="48" cy="48" r="20" fill="none" stroke="#FFD60A" stroke-width="7" stroke-linecap="round" stroke-dasharray="46 80" transform="rotate(${k * 520} 48 48)"/></svg>`
        : `<svg width="96" height="96" fill="none" stroke="#F7F3EA" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"><path d="M48 66V31M33 45L48 30L63 45"/></svg>`;
    } };
  },
  // magazine furniture behind the speaker: hairline frame, kicker, barcode: { kicker, color }
  kapak(d) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("class", "abs"); svg.style.cssText = "left:0;top:0"; svg.setAttribute("width", W); svg.setAttribute("height", H); root.appendChild(svg);
    const k = el("div", root, "left:540px;top:228px"); k.className = "d mono"; k.textContent = d.kicker; const ink = d.color || "#F3EEE3"; k.style.color = ink; const bar = [...Array(34)].map((_, i) => 2 + Math.floor(rand(i + 5) * 7));
    return { draw(u, o) { const p = smooth(u / .7), q = smooth(1 - o / .25), P = 2 * (968 + 1300); let x = 92, g = "";
      bar.forEach((w, i) => { if (i % 2 === 0) g += `<rect x="${x}" y="1168" width="${w}" height="82" fill="#14130F"/>`; x += w; });
      svg.style.opacity = k.style.opacity = 1 - q; k.style.clipPath = `inset(-20% ${100 - 104 * smooth((u - .25) / .5)}% -20% 0)`;
      svg.innerHTML = `<rect x="56" y="190" width="968" height="1300" fill="none" stroke="${ink}" stroke-opacity=".75" stroke-width="2.5" style="${strokeAnim(p, P)}"/>` + (u > .45 ? `<g opacity="${smooth((u - .45) / .25)}"><rect x="78" y="1150" width="${x - 64}" height="118" fill="#F3EEE3"/>${g}</g>` : ""); } };
  },
  // black and white for build.py: where a look has already arrived (the wipe)
  silme(d) {
    const e = el("div", root, "position:absolute;inset:0;background:#fff"), b = el("div", root, "position:absolute;inset:0;background:#000;z-index:-1");
    return { draw(u, o) { const p = smooth(u / .55) * 1.5 - .25, x = v => (p * W + (960 - v) * .28).toFixed(1); const q = o < .02 ? 1 : 0; e.style.clipPath = `polygon(-400px 0, ${x(0)}px 0, ${x(1920)}px 100%, -400px 100%)`; e.style.opacity = 1 - q; } };
  },
  // the bright edge of that wipe, drawn on top: { at }
  silmecizgi(d) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("class", "abs"); svg.style.cssText = "left:0;top:0"; root.appendChild(svg); snd(d.at, "hisir", 1);
    return { draw(u) { const p = smooth(u / .55) * 1.5 - .25, x = v => p * W + (960 - v) * .28; svg.innerHTML = `<path d="M${x(0)} 0L${x(1920)} 1920" stroke="#F3EEE3" stroke-width="5" opacity="${u < .6 ? 1 : 0}"/>`; } };
  },
  // a sound on its own: { name, vol }
  ses(d) { snd(d.at, d.name, d.vol || 1); return { draw() {} }; },
  // the cartoon iris: a black ring closes on the speaker, waits a beat, and shuts: { x, y, rest, wait }
  iris(d) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("class", "abs"); svg.style.cssText = "left:0;top:0;z-index:20"; svg.setAttribute("width", W); svg.setAttribute("height", H); root.appendChild(svg);
    const rest = d.rest || 235, wait = d.wait || .55; snd(d.at, "iris", 1); snd(d.at + .75 + wait, "kapan", 1);
    return { draw(u) {
      let r = 1500 + (rest - 1500) * smooth(u / .7);
      if (u > .7) r = rest + 26 * Math.exp(-7 * (u - .7)) * Math.sin((u - .7) * 22);
      const k = (u - .75 - wait) / .22; if (k > 0) r = (rest + 34 * Math.sin(Math.min(1, k * 2.2) * Math.PI) * (k < .46 ? 1 : 0)) * (1 - smooth((k - .4) / .6));
      r = Math.max(0, r);
      svg.innerHTML = `<path fill-rule="evenodd" fill="#050807" d="M-10 -10H${W + 10}V${H + 10}H-10Z${r > .5 ? `M${d.x - r} ${d.y}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0Z` : ""}"/>` +
        (r > 4 ? `<circle cx="${d.x}" cy="${d.y}" r="${r + 7}" fill="none" stroke="${YELLOW}" stroke-width="${Math.min(14, r * .2)}"/>` : "");
    } };
  },
};

// ---------- captions: the spoken word gets the highlighter ----------
function captions(t) {
  const c = T.captions.find(c => t >= c.start && t < c.end);
  if (!c) { CAP.style.opacity = 0; return; }
  const k = c.words.filter(w => t >= w.start).length - 1;
  CAP.style.opacity = 1; CAP.style.top = `${(T.capFull ?? 1520) + ((T.capMat ?? 735) - (T.capFull ?? 1520)) * (matAt(t) > .5 ? 1 : 0)}px`;
  CAP.innerHTML = c.words.map((w, i) => `<i class="${i === k ? "on" : ""}" style="opacity:${i <= k ? 1 : T.capStyle ? .38 : 0};transform:scale(${i === k && !T.capStyle ? 1 + .16 * (1 - over((t - w.start) / .16)) : 1})">${w.word}</i>`).join(" ");
}
let CAP;

window.load = async data => {
  T = data; MAT = el("div", root); MAT.id = "mat";
  FRAME = document.createElementNS("http://www.w3.org/2000/svg", "svg"); FRAME.setAttribute("class", "abs"); FRAME.setAttribute("width", W); FRAME.setAttribute("height", H); root.appendChild(FRAME);
  await document.fonts.ready; await Promise.all(["900 italic 80px 'Barlow Condensed'", "800 80px 'Barlow Condensed'", "400 80px 'Caveat Brush'", "500 80px 'Bodoni Moda'", "italic 500 80px 'Bodoni Moda'", "850 80px Archivo", "600 60px Archivo", "500 30px 'JetBrains Mono'"].map(f => document.fonts.load(f, "ığşİöç ABC")));
  for (const d of T.ui) { const before = root.children.length, heard = SND.length, p = BUILD[d.type](d); if (d.mute) SND.length = heard; ITEMS.push({ ...p, at: d.at, end: d.end, nodes: [...root.children].slice(before) }); }
  for (const [a] of T.masa) snd(a, "hisir", .8);
  CAP = el("div", root); CAP.className = "cap" + (T.capStyle ? " " + T.capStyle : "");
  await Promise.all([...document.images].map(i => i.decode().catch(() => {})));
  return SND;
};
window.seek = t => {
  const boil = Math.floor(t * 6);
  drawMat(t, boil);
  for (const i of ITEMS) { const on = t >= i.at && t < i.end; for (const n of i.nodes) n.style.display = on ? "" : "none"; if (on) i.draw(t - i.at, i.end - t, t, boil); }
  captions(t);
};
