# Directions for agents

Read this before changing anything. `ARCHITECTURE.md` has the formulas; this file
has the rules.

## The shape of this repo

One application file: `index.html`. Markup, CSS and the entire cost model live in
it. No build step, no bundler, no framework, no `package.json`, no dependencies.

**Keep it that way.** If you are about to add a build step, a framework, a state
library, or an npm dependency, stop. The value here is the model, not the
plumbing, and a file anyone can open in a browser is the point.

The only external resources are the Google Fonts stylesheet and the font files it
pulls. Do not add more.

## Ground rules

1. **KISS and YAGNI.** Prefer the simplest correct change. Do not add
   abstraction for a second case that does not exist yet.
2. **No new dependencies.** Not even a small one. Not even a CDN chart library.
3. **No purple.** Neutrals are cool slate. The accent is blue. This is a
   deliberate call, not an accident — see `ARCHITECTURE.md` §6.
4. **Every number stays editable.** Any figure that could be argued with must be
   a field in the rail, not a constant buried in the script. That is the whole
   contract with the user: they get to disagree with you.
5. **Never present a default as a fact.** Prices, quotas and model specs move.
   The footer says so; keep it saying so.
6. **Changing a default means updating `SOURCES.md`.** Every number in the
   catalogues and rate panels has a recorded provenance. A default with no
   source is a guess wearing a suit.
7. **Simple mode stays at three levers.** A fourth is always tempting and always
   wrong — that is what Advanced is for.

## How to add things

### A new open-weight model

Add one entry to `MODELS`. That is the whole change — it appears in the dropdown
and flows through sizing, capacity and cost automatically.

```js
{id:"slug", label:"Human Name 70B", total:70, active:70, kvMB:0.31}
```

`total` and `active` are billions of parameters (equal for dense models, `active`
much smaller for mixture-of-experts). Derive `kvMB` from the model's config as
`layers × kv_heads × head_dim × 2 × 2 / 1e6`. Latent-attention models compress
this hard — small numbers there are correct.

### A new accelerator

Add one entry to `GPUS`: `vram` in GB, `bw` in GB/s, `buy` as a street price per
card, `rent` as an hourly on-demand rate, `w` as board power. Selecting a card
copies these into the editable fields; no other change is needed.

### A new input

Add a tuple to the right group in `GROUPS`: `[id, label, unit, default, step]`.
It renders itself. Read it in the model with `v("id")`. Do not add a field
without using it.

### A new route

Push an object into the `rows` array in `compute()`. It must carry all five cost
components (`capex`, `power`, `people`, `usage`, `drag` — use `0`, never
`undefined`), plus `capTps`, `scaling`, `note`, `name` and `group`. Everything
downstream — sorting, ranking, chart, cards, capacity table — picks it up.

If the route scales one unit per developer rather than sharing a pool, set
`perDevScale: true` and `unitTps`. See `ARCHITECTURE.md` §5.

### A new cost component

Add it to `COMPONENTS` **and** give every route a value for it. A route missing a
key silently contributes zero and the totals stop adding up. There are five
components and five validated chart colours; a sixth needs the palette
re-validated for colour-vision-deficiency separation, not a hue picked by eye.

## Things that will bite you

- `render()` rewrites containers with `innerHTML`. Anything interactive inside
  them must be driven by delegated listeners on `document`, not by handlers
  bound to elements that get replaced.
- The five cost components are summed by key. Adding a component without
  updating every route produces totals that look plausible and are wrong.
- Chart colours are assigned in a fixed order for a reason. Do not reorder them.
- Grid containers use `gap: 1px` over a coloured background to draw hairlines.
  If a grid can leave an uneven tail, use the outline idiom instead, or you get
  a grey block where cells should be. See `ARCHITECTURE.md` §6.
- Theme tokens must exist on bare `:root` before any media or `[data-theme]`
  block redefines them. A colour defined only inside one of those blocks renders
  one theme's text on the other theme's background.

## Honesty rules

This tool makes an argument about money. Three rules protect it:

1. **The developer-time penalty stays one visible field.** It is the assumption
   that decides the whole ranking. Do not bury it, do not hard-code it, do not
   quietly vary it per model. Make it obvious and let the user turn it off.
2. **Cost and capacity stay separate.** A route that is cheap and cannot carry
   the team is not cheap. Do not collapse the capacity table into the cost chart.
3. **Throughput stays calibrated.** The batch cap of 32 and the single-stream
   ceiling exist because the uncapped model overstated throughput by 2.3x
   against measured vLLM numbers, which quietly flattered self-hosting. If you
   change either, re-check them against published benchmarks and record it in
   `SOURCES.md`.
4. **Keep the omissions list current.** `ARCHITECTURE.md` §7 lists what is not
   modelled. If you add a simplification, add it there.

## Before you push

There are no tests. Open `index.html` in a browser and check:

- The four presets (Solo / Startup / Midsize / Enterprise) all produce sensible
  numbers, and **Reset** returns to defaults.
- Switching model, precision and accelerator all move the sizing strip.
- Both themes are legible — toggle, and also check with the OS set to dark and no
  explicit choice made.
- The page does not scroll sideways at any width. Breakpoints are at 1099px,
  679px and 399px, deliberately off the common device widths — Chrome evaluates
  media queries against the viewport including the scrollbar, so a breakpoint on
  1024 flips on and off at iPad-landscape width. Do not "tidy" them to round
  numbers.
- Simple and Advanced both render, and switching between them keeps the numbers
  in step.
- No `NaN`, no `Infinity`, no `$0` where a figure belongs. Setting Developers to
  0 is the fastest way to find a divide-by-zero.

Commit to the branch you were given. Do not open a pull request unless you were
asked for one.
