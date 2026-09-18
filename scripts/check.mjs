/* Structural checks for the single-file app. No dependencies, no browser —
   this runs on a bare Node and is meant to catch the two ways this file has
   actually broken in practice: a syntax error in the inline script, and a
   field id referenced by the model that no longer exists.

   It is not a substitute for opening the page. It cannot catch a wrong
   formula, a layout regression, or a runtime error on a path it does not
   execute. See AGENTS.md for what a human still has to check by hand. */
import { readFileSync, existsSync } from "node:fs";

let failures = 0;
const fail = (msg) => { failures++; console.error("  FAIL  " + msg); };
const pass = (msg) => console.log("  ok    " + msg);

/* ── required files ─────────────────────────────────────────────────── */
for (const f of ["index.html", "README.md", "ARCHITECTURE.md", "SOURCES.md", "AGENTS.md"]) {
  existsSync(f) ? pass(f + " present") : fail(f + " is missing");
}

const html = readFileSync("index.html", "utf8");

/* ── the page keeps its shape ───────────────────────────────────────── */
const required = [
  ["<!doctype html>", "doctype"],
  ["<title>", "title"],
  ['name="viewport"', "viewport meta"],
  ["@media print", "print stylesheet"],
  ['@media (prefers-color-scheme: dark)', "dark theme block"],
  ['[data-theme="dark"]', "explicit dark theme stamp"],
];
for (const [needle, label] of required) {
  html.includes(needle) ? pass(label + " present") : fail(label + " is missing");
}

/* Every token a dark block redefines must ALSO be declared on the bare :root,
   or the un-stamped "system" state renders one theme's text on the other
   theme's ground. That is the classic unreadable-artifact bug, and it is the
   precise rule worth enforcing — a layout variable scoped to one component is
   fine and is not what this checks. */
const rootBlock = html.slice(html.indexOf(":root{"),
                             html.indexOf("@media (prefers-color-scheme: dark)"));
const onRoot = new Set([...rootBlock.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]));

/* Only the two dark scopes, not every rule that follows them — a component
   may legitimately define its own local variable. */
const inDark = new Set();
for (const re of [/:root:not\(\[data-theme="light"\]\)\s*\{([^}]*)\}/g,
                  /:root\[data-theme="dark"\]\s*\{([^}]*)\}/g]) {
  for (const m of html.matchAll(re))
    for (const t of m[1].matchAll(/(--[a-z0-9-]+)\s*:/g)) inDark.add(t[1]);
}
const themeOnly = [...inDark].filter((t) => !onRoot.has(t));
themeOnly.length === 0
  ? pass(`all ${inDark.size} theme tokens also declared on bare :root`)
  : fail("redefined in a theme block but absent from bare :root: " + themeOnly.join(", "));

/* ── the inline script compiles ─────────────────────────────────────── */
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
scripts.length ? pass(scripts.length + " inline script block(s) found") : fail("no inline script found");
const body = scripts.join("\n;\n");
try {
  new Function(body);
  pass("inline script parses");
} catch (e) {
  fail("inline script has a syntax error: " + e.message);
}

/* ── every referenced control id exists ─────────────────────────────── */
/* Ids come from three places: GROUPS tuples, selectHTML() calls, and literal
   id="..." attributes in the markup. Anything the model reads must be one. */
const ids = new Set([...html.matchAll(/\bid="([A-Za-z0-9_-]+)"/g)].map((m) => m[1]));
for (const m of body.matchAll(/\[\s*"([A-Za-z0-9_]+)"\s*,\s*"[^"]*"\s*,\s*"[^"]*"\s*,/g)) ids.add(m[1]);
for (const m of body.matchAll(/selectHTML\(\s*"([A-Za-z0-9_]+)"/g)) ids.add(m[1]);

const referenced = new Set();
for (const m of body.matchAll(/\bv\(\s*"([A-Za-z0-9_]+)"\s*\)/g)) referenced.add(m[1]);
for (const m of body.matchAll(/getElementById\(\s*"([A-Za-z0-9_-]+)"\s*\)/g)) referenced.add(m[1]);

const missing = [...referenced].filter((k) => !ids.has(k));
missing.length === 0
  ? pass(`all ${referenced.size} referenced control ids are defined`)
  : fail("referenced but never defined: " + missing.join(", "));

/* ── size guard ─────────────────────────────────────────────────────── */
const kb = Buffer.byteLength(html) / 1024;
kb < 16384 ? pass(`page is ${kb.toFixed(0)} KB`) : fail(`page is ${kb.toFixed(0)} KB, over the 16 MB artifact limit`);

console.log(failures === 0 ? "\nall checks passed" : `\n${failures} check(s) failed`);
process.exit(failures === 0 ? 0 : 1);
