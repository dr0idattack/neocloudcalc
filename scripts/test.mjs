/* Browser tests for index.html. No dependencies: it launches the Chromium or
   Chrome already on the machine and drives it over the DevTools protocol with
   Node's built-in WebSocket (Node 22+).

   It loads a temporary copy of the page with one line added at the end of
   the script, which puts the model's own functions on window.__t. index.html
   itself is never changed. The tests then call compute(), withOv() and the
   UI handlers directly, so they check the real model, not a second copy.

   Run:  node scripts/test.mjs
   Set CHROME_PATH if the browser is somewhere odd. */
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, mkdtempSync, existsSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

/* ── find a browser ─────────────────────────────────────────────────── */
function findChrome() {
  const pw = "/opt/pw-browsers";
  const cands = [process.env.CHROME_PATH,
    ...(existsSync(pw) ? readdirSync(pw).filter((d) => /^chromium-\d+$/.test(d))
                           .map((d) => join(pw, d, "chrome-linux", "chrome")) : []),
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"];
  const hit = cands.find((p) => p && existsSync(p));
  if (!hit) { console.error("No Chrome or Chromium found. Set CHROME_PATH."); process.exit(1); }
  return hit;
}

/* ── the page, with the model exposed ───────────────────────────────── */
const tmp = mkdtempSync(join(tmpdir(), "tco-test-"));
const html = readFileSync("index.html", "utf8");
const TAIL = "\nrender();\n})();";
if (!html.includes(TAIL)) { console.error("Cannot find the script tail to hook into."); process.exit(1); }
const hooked = html.replace(TAIL, "\nrender();\nwindow.__t = {compute:compute, withOv:withOv, render:render,"
  + " applyPreset:applyPreset, setMode:setMode, setTier:setTier, buildCsv:buildCsv,"
  + " GROUPS:GROUPS, PRESETS:PRESETS, COMPONENTS:COMPONENTS, MODELS:MODELS, GPUS:GPUS};\n})();");
const pagePath = join(tmp, "index.html");
writeFileSync(pagePath, hooked);

/* ── a tiny DevTools client ─────────────────────────────────────────── */
const chrome = spawn(findChrome(), ["--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run",
  "--disable-background-networking", "--disable-component-update",
  "--remote-debugging-port=0", "--user-data-dir=" + join(tmp, "profile"), "about:blank"],
  { stdio: ["ignore", "ignore", "pipe"] });
const wsUrl = await new Promise((ok, bad) => {
  let buf = "";
  const t = setTimeout(() => bad(new Error("Chrome did not start in 20 s")), 20000);
  chrome.stderr.on("data", (d) => {
    buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/);
    if (m) { clearTimeout(t); ok(m[1]); }
  });
  chrome.on("exit", (c) => bad(new Error("Chrome exited early, code " + c)));
});

const ws = new WebSocket(wsUrl);
await new Promise((ok) => ws.addEventListener("open", ok));
let seq = 0; const waiting = new Map(); const errors = [];
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && waiting.has(m.id)) {
    const { ok, bad } = waiting.get(m.id); waiting.delete(m.id);
    m.error ? bad(new Error(m.error.message)) : ok(m.result);
  } else if (m.method === "Runtime.exceptionThrown") {
    errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  } else if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") {
    errors.push(m.params.args.map((a) => a.value ?? a.description).join(" "));
  }
});
let sessionId;
const send = (method, params = {}) => new Promise((ok, bad) => {
  const id = ++seq; waiting.set(id, { ok, bad });
  ws.send(JSON.stringify({ id, method, params, sessionId }));
});

const { targetId } = await send("Target.createTarget", { url: "about:blank" });
({ sessionId } = await send("Target.attachToTarget", { targetId, flatten: true }));
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });

/* Run a function inside the page and return its (JSON) result. */
async function run(fn, ...args) {
  const r = await send("Runtime.evaluate", {
    expression: `(${fn})(...${JSON.stringify(args)})`, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
}
async function load() {
  await send("Page.navigate", { url: "file://" + pagePath });
  for (let i = 0; i < 200; i++) {
    if (await run(() => !!window.__t).catch(() => false)) return;
    await new Promise((r) => setTimeout(r, 50));
  }
  throw new Error("page did not finish loading");
}

/* ── in-page helpers, installed after each load ─────────────────────── */
function helpers() {
  window.ok = (cond, msg) => { if (!cond) throw new Error(msg); };
  window.set = (id, val) => { document.getElementById(id).value = val; };
  window.check = (id, on) => { document.getElementById(id).checked = on; };
  window.row = (d, id) => d.rows.find((r) => r.id === id);
  window.bad = (n) => typeof n !== "number" || !isFinite(n);
  /* Every number a route carries must be finite. */
  window.allFinite = (d, where) => d.rows.forEach((r) => {
    ["capex", "power", "people", "usage", "drag", "total", "upfront", "perDev", "perTask",
     "life", "yearOne", "lifeCash", "capTps", "demandTps", "headroom"].forEach((k) =>
      ok(!bad(r[k]), `${where}: ${r.id}.${k} is ${r[k]}`));
  });
  /* The visible page must never show NaN or Infinity. */
  window.cleanText = (where) => {
    const t = document.querySelector(".results")?.innerText || document.body.innerText;
    const hit = t.match(/NaN|Infinity|undefined/);
    ok(!hit, `${where}: page shows ${hit && hit[0]}`);
  };
  window.defaults = () => document.getElementById("resetbtn").click();
}

/* ── the tests ──────────────────────────────────────────────────────── */
const tests = [];
const test = (name, fn) => tests.push([name, fn]);

test("page loads with no script errors", async () => {
  if (errors.length) throw new Error(errors.join("\n"));
});

test("every preset gives finite, non-zero numbers", () => run(() => {
  Object.keys(__t.PRESETS).forEach((p) => {
    __t.applyPreset(p);
    const d = __t.compute();
    allFinite(d, p); cleanText(p);
    d.rows.forEach((r) => ok(r.total > 0, `${p}: ${r.id} total is ${r.total}`));
  });
}));

test("Developers = 0 gives no NaN, no Infinity", () => run(() => {
  __t.setMode("advanced"); set("devs", 0); __t.render();
  allFinite(__t.compute(), "devs=0"); cleanText("devs=0");
}));

test("empty and junk inputs do not break the page", () => run(() => {
  defaults(); set("devs", ""); set("workdays", "abc"); set("horizon", 0); set("amort", 0); __t.render();
  allFinite(__t.compute(), "junk"); cleanText("junk");
}));

test("each route total is the sum of its five components", () => run(() => {
  defaults();
  const keys = __t.COMPONENTS.map((c) => c.key);
  ok(keys.length === 5, "expected 5 cost components, found " + keys.length);
  __t.compute().rows.forEach((r) => {
    keys.forEach((k) => ok(typeof r[k] === "number", `${r.id} has no number for ${k}`));
    const sum = keys.reduce((s, k) => s + r[k], 0);
    ok(Math.abs(sum - r.total) < 1e-6, `${r.id}: parts ${sum} != total ${r.total}`);
    ["capTps", "scaling", "note", "name", "group"].forEach((k) =>
      ok(r[k] !== undefined, `${r.id} is missing ${k}`));
  });
}));

test("routes come out sorted cheapest first", () => run(() => {
  defaults();
  const t = __t.compute().rows.map((r) => r.total);
  t.forEach((x, i) => i && ok(t[i - 1] <= x, "rows are not sorted by total"));
}));

test("labour switch zeroes every labour line and moves the totals", () => run(() => {
  defaults();
  const on = __t.compute();
  check("labour", false);
  const off = __t.compute();
  check("labour", true);
  off.rows.forEach((r) => ok(r.people === 0, `${r.id}.people is ${r.people} with labour off`));
  ok(off.bom.setupLabour === 0 && off.bom.rentSetup === 0, "setup labour not zeroed");
  ok(row(on, "buy").total > row(off, "buy").total, "labour switch did not change the buy total");
}));

test("baseline platform team is charged to every centralised route", () => run(() => {
  defaults();
  const d = __t.compute();
  ok(d.platformMo > 0, "platformMo is 0 at defaults");
  ["buy", "rent", "bedrock", "azure", "anthropic", "openai", "hybrid", "seats"].forEach((id) =>
    ok(row(d, id).people >= d.platformMo - 1e-6, `${id} does not pay the platform team`));
  ok(row(d, "laptop").people < d.platformMo || d.platformMo === 0, "laptops should be exempt");
}));

test("'cost the tasks the agent cannot finish' reaches the totals", () => run(() => {
  defaults();
  const off = __t.compute(); check("countFallback", true);
  const on = __t.compute(); check("countFallback", false);
  const order = (d) => d.rows.map((r) => r.id).join();
  const moved = off.rows.some((r) => Math.abs(r.total - row(on, r.id).total) > 1);
  ok(moved, "fallback toggle did not change any total");
  ok(order(off) !== order(on) || moved, "fallback toggle changed nothing");
}));

test("a weaker open model costs twice: more attempts, more tokens, bigger fleet", () => run(() => {
  defaults();
  const same = __t.withOv({ acceptOpen: 60, acceptFrontier: 60, repairOpen: 40, repairFrontier: 40,
                            hardOpen: 5, hardFrontier: 5 }, __t.compute);
  const weak = __t.withOv({ acceptOpen: 20, acceptFrontier: 60, repairOpen: 40, repairFrontier: 40,
                            hardOpen: 5, hardFrontier: 5 }, __t.compute);
  ok(Math.abs(same.openTokenMult - 1) < 1e-9, "equal models should give token multiplier 1");
  ok(weak.openTokenMult > 1, "weaker open model should burn more tokens");
  ok(weak.peakTps > same.peakTps, "fleet is not sized on the extra tokens");
  ok(row(weak, "buy").drag > 0, "weaker open model has no developer-time cost");
  ok(row(same, "buy").drag < 1e-6, "equal models should have no drag");
}));

test("retry funnel is not attempts = 1/p", () => run(() => {
  defaults();
  /* With a hard share, some tasks never get solved however many retries. */
  const d = __t.withOv({ acceptOpen: 50, repairOpen: 50, hardOpen: 30, maxRetries: 10 }, __t.compute);
  ok(d.EFF.open.unres > 0, "hard share should leave unresolved tasks");
  ok(Math.abs(d.attemptsO - 1 / 0.5) > 1e-3, "attempts collapsed to 1/p");
}));

test("per-route demand differs between hosted and self-hosted routes", () => run(() => {
  defaults();
  const d = __t.compute();
  ok(d.openTokenMult > 1, "defaults should have a weaker open model");
  ok(row(d, "buy").demandTps > row(d, "anthropic").demandTps,
     "self-hosted demand should exceed hosted demand");
}));

test("replica sizing is topology-aware (power of two, then whole nodes)", () => run(() => {
  defaults();
  const pow2 = (n) => n > 0 && (n & (n - 1)) === 0;
  __t.MODELS.forEach((m) => __t.GPUS.forEach((g) => {
    document.getElementById("model").value = m.id;
    [4, 8].forEach((node) => {
      const s = __t.withOv({ nodeSize: node, gpuVram: g.vram, gpuBw: g.bw }, __t.compute).s;
      const n = s.gpusPerReplica;
      ok(n <= node ? pow2(n) : n % node === 0, `${m.id} on ${g.id}, node ${node}: ${n} cards per replica`);
      ok(n >= s.rawCards, `${m.id} on ${g.id}: ${n} cards < ${s.rawCards} needed`);
    });
  }));
  defaults();
}));

test("batch multiplier is capped at 32", () => run(() => {
  defaults();
  const a = __t.withOv({ batch: 32 }, __t.compute).s.perStream;
  const b = __t.withOv({ batch: 32 }, __t.compute).s.replicaTps;
  const c = __t.withOv({ batch: 128 }, __t.compute).s.replicaTps;
  ok(a > 0 && Math.abs(b - c) < 1e-6, `replica tps grew past batch 32: ${b} -> ${c}`);
}));

test("single-stream ceiling holds", () => run(() => {
  defaults();
  const s = __t.withOv({ streamCap: 50 }, __t.compute).s;
  ok(s.perStream <= 50 + 1e-9, "perStream " + s.perStream + " is over the cap");
}));

test("hybrid pays for its own fleet, not the standalone one", () => run(() => {
  defaults();
  /* 1,200 devs with renting made expensive, so buying wins for the hybrid. */
  const d = __t.withOv({ devs: 1200, gpuRent: 50 }, __t.compute);
  const h = row(d, "hybrid"), b = row(d, "buy");
  ok(d.hybridBuy, "buying should win for the hybrid in this setup");
  ok(d.hybridSize.gpus < d.s.gpus, `hybrid fleet ${d.hybridSize.gpus} not smaller than ${d.s.gpus}`);
  ok(h.upfront < b.upfront, `hybrid cheque ${h.upfront} >= standalone ${b.upfront}`);
  ok(h.capex < b.capex, "hybrid capex is not smaller than the standalone fleet's");
}));

test("cash view and accounting view stay distinct", () => run(() => {
  defaults();
  const b = row(__t.compute(), "buy");
  ok(b.upfront > b.capex, "buy upfront should be the full cheque, not one month");
  ok(Math.abs(b.cashAt(0) - b.upfront) < 1e-6, "cash at month 0 is not the upfront cheque");
}));

test("Reset returns to defaults", () => run(() => {
  defaults();
  const want = JSON.stringify(__t.compute().rows.map((r) => [r.id, r.total]));
  set("devs", 7); set("gpuBuy", 1); __t.applyPreset("enterprise");
  document.getElementById("model").value = __t.MODELS[0].id;
  defaults();
  ok(JSON.stringify(__t.compute().rows.map((r) => [r.id, r.total])) === want, "Reset did not restore totals");
}));

test("Simple and Advanced show the same numbers", () => run(() => {
  defaults(); __t.setMode("simple");
  const a = document.getElementById("kpis").innerText;
  __t.setMode("advanced");
  const b = document.getElementById("kpis").innerText;
  __t.setMode("simple");
  ok(a === b, "KPIs differ between modes");
}));

test("Simple-mode sliders write into the model", () => run(() => {
  defaults(); __t.setMode("simple");
  const s = document.getElementById("s-devs");
  s.value = 123; s.dispatchEvent(new Event("input", { bubbles: true }));
  ok(__t.compute().devs === 123, "developer slider did not reach the model");
}));

test("CSV lists every input and every value is a number", () => run(() => {
  defaults();
  const csv = __t.buildCsv(__t.compute());
  const lines = csv.split("\n");
  Object.values(__t.GROUPS).flat().forEach((f) => {
    const label = f[1].replace(/&amp;/g, "&").replace(/<[^>]*>/g, "");
    const line = lines.find((l) => l.startsWith('"' + label.replace(/"/g, '""') + '",'));
    ok(line, "CSV is missing input: " + label);
    const val = line.slice(label.length + 3).split(",")[0];
    ok(val !== "" && isFinite(Number(val)), `CSV value for ${label} is not a number: ${val}`);
  });
  ok(!/NaN|Infinity|undefined/.test(csv), "CSV contains NaN, Infinity or undefined");
}));

test("no sideways scroll at any width", async () => {
  for (const w of [1440, 1099, 1100, 900, 679, 680, 500, 399, 400, 320]) {
    await send("Emulation.setDeviceMetricsOverride", { width: w, height: 900, deviceScaleFactor: 1, mobile: w < 680 });
    for (const mode of ["simple", "advanced"]) {
      const over = await run((m) => { __t.setMode(m); return document.documentElement.scrollWidth - innerWidth; }, mode);
      if (over > 0) throw new Error(`${mode} mode at ${w}px scrolls sideways by ${over}px`);
    }
  }
  await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
});

test("print hides the rail, top bar and export, and shows the appendix", async () => {
  await send("Emulation.setEmulatedMedia", { media: "print" });
  try {
    await run(() => {
      const shown = (sel) => [...document.querySelectorAll(sel)].some((e) => getComputedStyle(e).display !== "none");
      ["aside.rail", ".topbar", ".export"].forEach((s) => ok(!shown(s), s + " is visible in print"));
      ok(shown("section.printonly"), "print appendix is hidden in print");
    });
  } finally { await send("Emulation.setEmulatedMedia", { media: "" }); }
});

test("both themes set a readable ground and ink", () => run(() => {
  const root = document.documentElement;
  ["light", "dark"].forEach((t) => {
    root.setAttribute("data-theme", t);
    const bg = getComputedStyle(document.body).backgroundColor;
    const fg = getComputedStyle(document.body).color;
    ok(bg !== fg, `${t} theme: text and background are the same colour`);
  });
  root.removeAttribute("data-theme");
}));

test("a slider drag stays smooth (render under 100 ms)", () => run(() => {
  defaults();
  const t0 = performance.now();
  for (let i = 0; i < 10; i++) { set("devs", 50 + i); __t.render(); }
  const ms = (performance.now() - t0) / 10;
  ok(ms < 100, `render takes ${ms.toFixed(1)} ms`);
  return ms;
}));

/* ── run ────────────────────────────────────────────────────────────── */
let failed = 0;
try {
  await load();
  await run(helpers);
  for (const [name, fn] of tests) {
    const t0 = performance.now();
    try {
      const out = await fn();
      const ms = (performance.now() - t0).toFixed(0);
      console.log(`  ok    ${name}  (${ms} ms${typeof out === "number" ? `, ${out.toFixed(1)} ms/render` : ""})`);
    } catch (e) {
      failed++; console.error(`  FAIL  ${name}\n        ${e.message.split("\n")[0]}`);
    }
  }
  if (errors.length) { failed++; console.error("  FAIL  script errors during tests:\n        " + errors.join("\n        ")); }
} finally {
  ws.close(); chrome.kill();
  await new Promise((r) => chrome.once("exit", r));
  rmSync(tmp, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
console.log(failed ? `\n${failed} test(s) failed` : `\nall ${tests.length} tests passed`);
process.exit(failed ? 1 : 0);
