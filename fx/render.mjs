// node fx/render.mjs timeline.json out.mov [t ...]   draws kit.html frame by frame in headless Chrome/Edge (no npm packages; Node 22+).
// With times, writes out.mov.<t>.png previews instead of a movie. Also writes out.mov.sounds.json.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

function findChrome() {
  if (process.env.CHROME) return process.env.CHROME;
  const candidates = process.platform === "darwin"
    ? ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    : process.platform === "win32"
      ? [
          "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
          "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
          "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
          "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
        ]
      : ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"];
  const hit = candidates.find(existsSync);
  if (!hit) throw new Error("Chrome/Chromium not found. Install Google Chrome or set CHROME=/path/to/chrome.");
  return hit;
}

if (typeof WebSocket !== "function") {
  throw new Error("Node 22+ is required (built-in WebSocket).");
}

const [file, out, ...times] = process.argv.slice(2);
const data = JSON.parse(readFileSync(file)), here = dirname(fileURLToPath(import.meta.url)), FPS = data.fps || 15;
const dir = mkdtempSync(join(tmpdir(), "kit-"));
const chrome = spawn(findChrome(), ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${dir}`,
  "--hide-scrollbars", "--allow-file-access-from-files", "--force-device-scale-factor=1", "--window-size=1080,1920", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
const ws = await new Promise(ok => { let s = ""; chrome.stderr.on("data", b => { s += b; const m = s.match(/ws:\/\/\S+/); if (m) ok(m[0]); }); });
const sock = new WebSocket(ws); await new Promise(ok => sock.onopen = ok);
let id = 0; const wait = new Map();
sock.onmessage = e => { const m = JSON.parse(e.data); if (wait.has(m.id)) { const [ok, no] = wait.get(m.id); wait.delete(m.id); m.error ? no(new Error(JSON.stringify(m.error))) : ok(m.result); } };
const send = (method, params = {}, sessionId) => new Promise((ok, no) => { wait.set(++id, [ok, no]); sock.send(JSON.stringify({ id, method, params, sessionId })); });
try {
  const { targetId } = await send("Target.createTarget", { url: pathToFileURL(join(here, "kit.html")).href });
  const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
  const cmd = (m, p) => send(m, p, sessionId);
  const js = async expression => { const r = await cmd("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
  await cmd("Page.enable");
  await cmd("Emulation.setDeviceMetricsOverride", { width: 1080, height: 1920, deviceScaleFactor: 1, mobile: false });
  await cmd("Emulation.setDefaultBackgroundColorOverride", { color: { r: 0, g: 0, b: 0, a: 0 } });
  for (let i = 0; i < 100 && !(await js("typeof window.load === 'function' && document.readyState === 'complete'")); i++) await new Promise(r => setTimeout(r, 100));
  const sounds = await js(`load(${JSON.stringify(data)})`);
  writeFileSync(out + ".sounds.json", JSON.stringify(sounds));
  const shot = async t => { await js(`seek(${t})`); return Buffer.from((await cmd("Page.captureScreenshot", { format: "png", optimizeForSpeed: true })).data, "base64"); };
  if (times.length) for (const t of times) writeFileSync(`${out}.${t}.png`, await shot(+t));
  else {
    const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "png", "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", out], { stdio: ["pipe", "inherit", "inherit"] });
    const done = new Promise(ok => ff.on("close", ok));
    for (let i = 0; i < Math.ceil(data.total * FPS); i++) if (!ff.stdin.write(await shot(i / FPS))) await new Promise(r => ff.stdin.once("drain", r));
    ff.stdin.end(); if (await done) throw new Error("ffmpeg failed");
  }
} finally { sock.close(); chrome.kill(); await new Promise(r => chrome.on("close", r)); rmSync(dir, { recursive: true, force: true, maxRetries: 5 }); }
