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

### Replaying the model at other inputs

Use `withOv({id: value}, compute)`. Do not write a second copy of the cost model
for a scan or a chart — that is how the two drift apart.

Anything called from inside `withOv` must not call `render()`.

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

0. **Retries are not fresh coin flips.** The funnel separates first pass, repair
   pass, and the share never solved. Do not collapse it back to
   `attempts = 1/p` — that assumes a failed task has the same chance next time,
   which is not how coding agents fail, and it silently deletes the hybrid's
   whole reason to exist.
1. **Effectiveness stays derived, and its cost stays visible.** The
   developer-time penalty is computed from first-pass acceptance, never typed in
   as a flat percentage — that was an effectiveness assumption wearing an
   infrastructure costume. But the derived percentage must stay on screen, next
   to the acceptance slider and in every export, because a modelled number can
   hide a guess better than a typed one. Deriving it relocated the uncertainty;
   it did not remove it.
2. **A weaker model costs twice.** More attempts per accepted task means more
   developer minutes *and* more tokens, so own-hardware routes are sized and
   billed on `tokens × openTokenMultiplier`. Dropping the second half makes
   self-hosting look better than it is, which is the failure mode this tool
   exists to avoid.
3. **Every centralised route pays the baseline platform team.** Gateways,
   secrets, IAM, observability, evals and security review do not appear only
   because the endpoint is Bedrock. Charging that to the cloud platforms alone
   was a fairness bug; do not reintroduce it.
4. **Replica sizing stays topology-aware.** A power of two inside a node, whole
   nodes past it, and an interconnect haircut for multi-node. `ceil(vram/card)`
   alone claims nine cards is one more than eight.
5. **Cost and capacity stay separate.** A route that is cheap and cannot carry
   the team is not cheap. Do not collapse the capacity table into the cost chart.
6. **The labour switch stays wired to the model.** It is not a display toggle.
   Off, it must zero every labour line on every route, so the ranking reflects
   the assumption. A switch that only hides rows would let someone believe a
   self-hosting case that quietly ships the work to an imaginary team.
7. **Accounting view and cash view stay distinct.** Amortised capital in the
   monthly comparison, the real cheque in the cumulative chart. Collapsing them
   loses the thing a finance reader came for.
8. **Throughput stays calibrated.** The batch cap of 32 and the single-stream
   ceiling exist because the uncapped model overstated throughput by 2.3x
   against measured vLLM numbers, which quietly flattered self-hosting. If you
   change either, re-check them against published benchmarks and record it in
   `SOURCES.md`.
9. **Export stays in sync with the model.** A new input, route or cost component
   must appear in the CSV and in the printed appendix. An export that silently
   omits an assumption is worse than no export — someone will act on it.
10. **Keep both download paths.** A download the page starts itself is inert
   inside embedded viewers, which instead grant one through the `downloads`
   capability; served as an ordinary page it is the other way round. The handler
   tries the capability and falls back to a blob. Deleting either half breaks
   export in one of the two places it runs, and neither failure is loud.
11. **Keep the omissions list current.** `ARCHITECTURE.md` §7 lists what is not
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
- The labour switch changes the totals, not just the bill of materials.
- Print preview is clean: no rail, no top bar, no export panel, the appendix
  present, and the cash chart sized to the page.
- The CSV opens in a spreadsheet and every number is a number.
- Toggling "cost the tasks the agent cannot finish" reorders the routes. If it
  does not, the fallback term is not reaching the totals.
- Per-route demand differs between hosted and self-hosted routes in the capacity
  table. One shared demand figure is the bug that was there before.
- Dragging a slider stays smooth. Each render runs roughly 200 extra `compute()`
  calls for the break-even scan and sensitivity pass; if you add more, check it.
- No `NaN`, no `Infinity`, no `$0` where a figure belongs. Setting Developers to
  0 is the fastest way to find a divide-by-zero.

Commit to the branch you were given. Do not open a pull request unless you were
asked for one.
