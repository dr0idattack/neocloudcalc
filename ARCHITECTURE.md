# Architecture & specification

`neocloudcalc` is one file: `index.html`. Markup, styles and the whole cost model
live in it. There is no build step, no bundler, no framework, no package.json.
Open the file and it runs.

That is a deliberate constraint. The value here is the model, not the plumbing.

---

## 1. Shape of the page

```
topbar        brand · preset buttons · theme · reset
layout        CSS grid, 344px rail + fluid results column
  rail        six <details> panels of inputs, sticky on desktop
  results     KPIs → sizing → capacity → cost chart → route cards → caveats
```

Under 1020px the grid collapses to one column and the rail stops sticking.
Under 560px the chart drops its axis and the bars go full width.

### Rendering

There is one function, `render()`. Any `input` or `change` event in the document
calls it. It recomputes everything and rewrites four containers with
`innerHTML`. No virtual DOM, no diffing, no state store. The inputs in the rail
*are* the state.

This is fine because the whole model is a few dozen arithmetic operations. A
keystroke-to-repaint takes well under a millisecond.

---

## 2. Data catalogues

Three arrays near the top of the script. Each entry is plain data — add a row and
it appears in its dropdown, no other change needed.

### `MODELS` — open-weight models published on Hugging Face

| Field | Meaning |
| --- | --- |
| `total` | Total parameters, in billions |
| `active` | Parameters read per token. Equals `total` for dense models; much smaller for mixture-of-experts |
| `kvMB` | Megabytes of KV cache per token at FP16 |

`kvMB` is derived as `layers × kv_heads × head_dim × 2 tensors × 2 bytes`.
Models using latent attention (DeepSeek, Kimi) compress the cache hard, which is
why their numbers look impossibly small. That is not a typo.

### `QUANTS` — weight precision

`bytes` is bytes per parameter. `kv` is the multiplier applied to KV cache when
the cache is quantised alongside the weights. INT4 is listed at 0.55 bytes, not
0.5, because real INT4 checkpoints carry FP16 scales and unquantised layers.

### `GPUS` — accelerators

`vram` in GB, `bw` is HBM bandwidth in GB/s, `buy` is a street price for one
card, `rent` an hourly on-demand rate, `w` the board power. Selecting a card
copies these five numbers into editable fields — change the card to reset them,
or type over them to model your own quote.

---

## 3. The sizing model

### Memory

```
weightsGB = total_params_B × bytes_per_param
kvGB      = batch × context_tokens × kvMB × kv_multiplier / 1024
overhead  = weightsGB × 0.15
vramNeed  = weightsGB + kvGB + overhead
```

The 15% covers activations, CUDA graphs and allocator fragmentation. It is a
rule of thumb, not a measurement.

```
cardsPerReplica = ceil(vramNeed / vram_per_card)
```

### Throughput

Decode on a batched server is memory-bandwidth bound: every token read requires
streaming the active weights out of HBM. Tensor parallelism adds bandwidth;
batching amortises the read across concurrent requests.

```
bytesPerToken = active_params_B × bytes_per_param     (GB read per token)
perStream     = min( cardsPerReplica × bw / bytesPerToken × bandwidth_efficiency,
                     single_stream_ceiling )
replicaTPS    = perStream × min(batch, 32)
```

Two guards, both calibrated against published vLLM measurements on H100 and both
exposed as editable fields:

- **Batch multiplier capped at 32.** With the default 65% efficiency that gives
  an effective ~21×. Llama 70B FP8 on 4 cards measures ~3,400 output tok/s at
  256 concurrency; this predicts ~4,000. Llama 8B FP8 on 1 card measures
  ~11,200; this predicts ~8,700. Within about 25% either way.
- **Single-stream ceiling, default 250 tok/s.** The bandwidth term alone claims
  a 5B-active mixture-of-experts model decodes at 1,280 tok/s on one stream.
  Nothing does — kernel launches, attention and sampling cap a single stream far
  below the weights-read limit.

An earlier version had neither guard and overstated throughput by roughly 2.3×.
That understated the fleet, which understated the cost of self-hosting: the tool
was flattering the option it should have been hardest on. See `SOURCES.md` §6.

This is still the right first-order answer and wrong at the edges. It ignores
prefill, the compute-bound regime at very large batch, and interconnect stalls
in tensor parallelism.

### Fleet

```
peakTPS  = (monthly_output_tokens / working_days / (busy_hours × 3600)) × peak_factor
replicas = ceil(peakTPS / replicaTPS)
cards    = replicas × cardsPerReplica
hosts    = ceil(cards / 8)
```

Sizing is done on output tokens because decode is where accelerator time goes.

### Storage

```
storageGB = (total_params_B × 2 + total_params_B × bytes_per_param) × checkpoints_kept
```

The original BF16 release plus the quantised copy you actually serve, times the
number of versions you keep on disk.

### Laptop fit

```
fitsLaptop = (weightsGB × 1.15 + 4) ≤ laptop_unified_memory_GB
```

The +4 GB is the rest of the machine. A failing check does not remove the laptop
route — it prices it anyway and flags it, because "we tried and it didn't fit" is
a real cost.

---

## 4. The cost model

Every route is scored on the same five components, so the stacked bars sit on one
scale and the comparison is honest.

| Component | Chart colour | What lands here |
| --- | --- | --- |
| `capex` | blue | Hardware divided by the write-off period |
| `power` | orange | Electricity × PUE, rack and cooling, model storage |
| `people` | aqua | Platform engineers, IT support, cloud plumbing staff |
| `usage` | yellow | Tokens, seat fees, hourly GPU rent |
| `drag` | magenta | Developer hours lost to a weaker model |

### Token billing

```
inputTokens  = devs × input_M × 1e6 × working_days
outputTokens = devs × output_k × 1e3 × working_days
cached       = inputTokens × cache_share
fresh        = inputTokens − cached

cost = fresh/1e6 × in_rate + cached/1e6 × cache_rate + outputTokens/1e6 × out_rate
```

### The developer-time penalty

```
dragCost = devs × hours_in_tool × working_days × penalty% × loaded_hourly_rate
```

Applied to all three own-hardware routes and to none of the hosted ones.

**This is the single most consequential assumption in the tool, and it is
deliberately exposed as one field.** The open-weight model you can host is not
the frontier model you rent. If your work genuinely does not need frontier
quality, set the penalty to 0 and the ranking flips. The tool does not argue the
point; it makes the argument visible and hands you the dial.

### The eight routes

| Route | capex | power | people | usage |
| --- | --- | --- | --- | --- |
| Local model on laptops | laptop uplift ÷ write-off | laptop watts × hours | IT support hours | — |
| GPUs you buy | (cards × price + hosts × host cost) ÷ write-off | fleet kW × PUE × 730 × $/kWh + rack + storage | platform FTE | — |
| GPUs you rent | — | storage only | platform FTE | cards × $/hr × 730 × uptime% |
| AWS Bedrock | — | — | cloud ops FTE | tokens |
| Azure OpenAI | — | — | cloud ops FTE | tokens |
| Anthropic API | — | — | — | tokens |
| OpenAI API | — | — | — | tokens |
| Flat per-seat plans | — | — | — | devs × seat price |

Fleet power carries a ×1.25 uplift over raw board power for host, NIC and fans.

### Derived per-route figures

```
total      = capex + power + people + usage + drag
perDev     = total / devs
perMOut    = total / (output_tokens / 1e6)
life       = total × horizon_months
```

Routes are sorted ascending by `total`. Rank one gets the "Cheapest" chip; the
last gets "Priciest".

### Accounting view vs cash view

Every route carries both, because they answer different questions:

```
accounting:  total       = capex/amort + power + people + usage + drag
cash:        upfront     = the cheque on day one
             monthlyCash = power + people + usage + drag
             cashAt(m)   = upfront + monthlyCash × m
```

The monthly chart and the route cards use the accounting view — capital spread
over the write-off period, which is how a cost centre sees it. The cumulative
cash chart uses the cash view, because a $208k cheque in month 0 is not the same
thing as $5.8k a month and no CFO thinks it is.

Break-even between two straight cumulative lines is solved directly rather than
scanned:

```
crossMonth = (hosted.upfront − own.upfront) / (own.monthlyCash − hosted.monthlyCash)
```

A negative or absent root means owning never catches renting tokens, because it
costs more to run as well as more to buy.

### Bill of materials

The buy route's capital is itemised rather than rolled into one number, because
this is the list that goes to procurement:

| Line | Derivation |
| --- | --- |
| Accelerators | `cards × gpuBuy` |
| Spare cards | `cards × spares%` |
| GPU host chassis | `hosts × hostCost` |
| Fabric, optics, cabling | `hosts × netFabric` |
| Rack, PDU, smart hands | `hosts × installHost` |
| One-time labour | `(setupArch + hosts×setupRack + setupStack + setupEval + setupSec) × fteCost/2080` |

Recurring adds hardware support (`hwCapex × warranty%/12`), rack and cooling,
electricity, checkpoint storage, the platform FTE, and the one-time labour
written down over the amortisation period.

**The labour switch** (`#labour`, on by default) is not cosmetic — it feeds the
model. Off, it zeroes the platform FTE, the cloud-ops FTE, laptop IT support and
all setup labour on every route. That models a team that already exists and
absorbs the work, which is the assumption most self-hosting business cases make
silently. The tool makes you make it out loud.

Renting GPUs skips the hardware but not the bring-up: it still carries the
serving stack, model evaluation, security review and half the architecture time.

### Sensitivity

The metric is the **decision margin**: cheapest hosted route minus the cheaper of
buying or renting GPUs, per month. Laptops are excluded — one model per developer
is a different animal from standing up shared serving, and this section is about
whether to stand one up.

Each knob is swung ±30% and the margin recomputed through `withOv`. A bar whose
range crosses zero changes the *winner*, not just the size of the bill; those are
drawn in the warning hue and labelled "flips".

Knobs that read "no effect" are reporting something real rather than failing: the
fleet is at its minimum size, so that assumption cannot move it. Self-hosted cost
is a step function.

### The quality budget

The headline figure, and the reason the tool exists:

```
qualityBudget$ = cheapest_hosted_total − cheapest_own_hardware_total_excluding_drag
codingSpend    = devs × hours_in_tool × working_days × loaded_hourly_rate
qualityBudget% = qualityBudget$ / codingSpend × 100
```

This is the percentage of developer time that self-hosting's saving actually
buys. At 60 developers the frontier API bill is about $200 per developer per
month against roughly $10,000 of loaded coding time — so a **2% productivity
penalty costs as much as the entire API bill.** When the quality budget is
smaller than the penalty you believe in, the spreadsheet is not what decides the
question. The KPI turns red in that case.

---

## 5. The capacity model

Cost alone does not settle the argument. A route that is cheap and cannot carry
the team is not cheap. This section answers: **how many developers can actually
work on this at once?**

An agentic coding session is a near-continuous stream of output tokens while its
developer is working:

```
sessionTPS   = (output_tokens_per_dev_per_day) / (hours_in_tool × 3600)
liveSessions = devs × live_session_share
demandTPS    = liveSessions × sessionTPS
```

Each route declares a `capTps` — the sustained output tokens per second it can
deliver.

| Route | `capTps` |
| --- | --- |
| Local model on laptops | `devs × laptopTPS`, where `laptopTPS = laptop_bandwidth / bytesPerToken × efficiency` |
| GPUs you buy / rent | `replicas × replicaTPS` |
| Bedrock / Azure / Anthropic / OpenAI | account quota, `k tok/min × 1000 / 60` |
| Flat per-seat plans | `devs × per-seat ceiling / 60` |

### Two kinds of scaling

**Pooled routes** (servers, APIs) share one ceiling:

```
sessions = capTps / sessionTPS
devs     = sessions / live_session_share
headroom = capTps / demandTPS
```

**Per-developer routes** (laptops, per-seat plans) add a unit with every hire, so
they never run out. The real question is whether *one* unit keeps up with *one*
session:

```
sessions = devs           (one each)
devs     = "scales 1:1"
headroom = unitTPS / sessionTPS
```

Headroom below 1.0× means the route throttles and developers queue. This is where
per-seat plans get interesting: a seat ceiling of 900 tok/min is 15 tok/s, and a
busy agentic session wants more than that.

---

## 6. Replaying the model at other inputs

`v(id)` normally reads the DOM. A module-level `OV` map overrides it, and
`withOv(overrides, fn)` sets it for one call and restores it after:

```js
var o = withOv({devs: 250, drag: 0}, compute);
```

This is what the break-even scan and the sensitivity pass are built on, and it
is why neither needs a second copy of the cost model. Roughly 200 extra
`compute()` calls run per render; each is a few dozen arithmetic operations, so
the whole render stays well inside a frame.

`compute()` must never call anything that calls `render()`, or the override
stack unwinds into recursion.

## 7. Modes

**Simple** shows three levers and nothing else: developers, a usage tier, and
the open-model time penalty. They are the three inputs that move the answer
most. The tier buttons write into the same `inTok` / `outTok` / `codeHrs`
fields the advanced panels use, and the sliders write into `devs` and `drag`,
so `compute()` never knows which mode is on. Switching to Simple re-syncs the
sliders from the canonical inputs.

Usage tiers, anchored on Anthropic's reported ~$13 per developer per active day:

| Tier | Input/dev/day | Output/dev/day | Hours |
| --- | --- | --- | --- |
| Light | 3M | 90k | 2 |
| Steady | 6M | 180k | 4 |
| Heavy (default) | 10M | 300k | 5 |
| All-day agent | 20M | 700k | 7 |

**Advanced** reveals all six panels plus the team-size presets.

## 8. Export

Two paths out, because the two audiences want different things.

**Print / PDF** is a `@media print` stylesheet, not a separate document. It
forces the light palette regardless of the on-screen theme, sets
`print-color-adjust: exact` so charts and status chips survive, hides the rail,
top bar and export panel, and replaces the route cards — which waste paper — with
a print-only comparison table. Two blocks are print-only (`.printonly`): a header
carrying the date and the full run line, and an appendix listing every assumption
in three columns, so nobody receiving the document has to ask what was plugged in.
The bill of materials and the appendix each start on a fresh page. Roughly seven
pages at default settings.

The cumulative chart is drawn at measured pixel width, so `beforeprint` and
`afterprint` both re-render it at the new page width.

**CSV** is built by `buildCsv()` into four labelled blocks — assumptions, sizing,
the route comparison with all five cost components broken out, and the bill of
materials line by line — separated by blank lines, which spreadsheets read as
sections. Values are raw numbers with no currency symbols or thousands
separators, so they compute on arrival. The run line is the second row, so a
spreadsheet sitting in someone's inbox still says what produced it.

Download takes two paths from one file. **Embedded viewers block a download a
page starts itself** — `<a download>` with a blob href is inert inside the
artifact sandbox — but they grant one through the `downloads` capability, so the
handler tries `claude.use("downloads")` first and falls back to the blob when the
capability is absent, which is the case whenever the page is served normally.
Rejections are branched by code: `declined` reads as "Cancelled", `rate_limited`
as "Try again", anything else points at Copy.

Copy stays for anywhere neither path works. It falls back from the async
Clipboard API to a hidden textarea and `execCommand`, and tells the user to press
Ctrl+C if both fail. Every button flashes its result rather than firing a dialog.

## 9. Responsive behaviour

Three layouts, with breakpoints deliberately set *off* the common device widths
(1099px and 679px rather than 1024 and 640). Chrome evaluates media queries
against the viewport including the classic scrollbar, so a breakpoint sitting
exactly on 1024 flips on and off at iPad-landscape width. That bug was real and
is why the numbers look odd.

| Width | Layout |
| --- | --- |
| 1100px+ | Two panes. Sticky input rail on the left, results scroll on the right |
| 680–1099px | One column. Rail panels reflow into an auto-fit grid, simple-mode levers sit side by side |
| Up to 679px | Fully stacked. The capacity and beyond-cost tables become one block per route via `data-label` pseudo-elements, the chart drops its axis and the bars go full width, controls grow to touch size |
| Up to 399px | Usage tiers and sizing cells drop to a single column |

Verified with a scripted pass measuring `scrollWidth` and every element's right
edge at 500 / 640 / 700 / 768 / 834 / 900 / 1024 / 1100 / 1280 / 1440. No
horizontal page scroll at any width.

## 10. Design system

### Colour

Neutrals are cool slate, biased toward the accent blue. No purple anywhere. Every
token is declared on bare `:root` first, then redefined under
`@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`,
then again under `:root[data-theme="dark"]` so the toggle wins in both directions.

| Role | Light | Dark |
| --- | --- | --- |
| ground / surface | `#eef1f5` / `#ffffff` | `#0a0e13` / `#121820` |
| ink / muted | `#0b1220` / `#6a7687` | `#e9eef4` / `#7e8b9b` |
| accent | `#125ec4` | `#5a9bea` |
| good / bad / warn | `#0a6b42` / `#a23a2b` / `#8a5a06` | `#4dc089` / `#e98a7f` / `#dfa63c` |

Chart series are a separate, validated categorical set — blue `#2a78d6`, orange
`#eb6834`, aqua `#1baf7a`, yellow `#eda100`, magenta `#e87ba4` (dark-mode steps
in the token block). Assigned in fixed order, never cycled. The order matters:
it is the one that clears colour-vision-deficiency separation on adjacent pairs,
which is exactly what a stacked bar puts side by side. Three of the light steps
sit under 3:1 contrast, so every segment is also named and numbered in the route
cards — colour is never the only encoding.

Semantic colour (good / warning / bad) is reserved for state and never reused as
a sixth series.

### Type

IBM Plex Sans for interface text, IBM Plex Mono for every figure, with
`font-variant-numeric: tabular-nums` so columns of money line up. Loaded from
Google Fonts with a real fallback stack.

### Charts

The monthly chart is HTML flex bars. The cumulative cash chart is inline SVG
drawn at **measured pixel width** (`container.clientWidth`) rather than a scaled
`viewBox`, so its labels stay at their true size instead of shrinking with the
page; a debounced `resize` listener re-renders it. SVG marks take their colour
through `style="stroke:var(--s1)"`, because `var()` is not permitted in SVG
presentation attributes.

### Layout idiom

Repeated groups are laid out as a grid with `gap: 1px` over a line-coloured
background, which draws hairline rules between cells without per-cell borders.
Where a grid can leave an uneven tail (the sizing strip), the container is
surface-coloured and each cell carries a 1px `outline` instead, so empty space
reads as empty rather than as a grey block.

---

## 11. Deliberate omissions

Not modelled, and worth saying out loud:

- Procurement lead time and the cost of waiting for cards (named in the
  beyond-cost table, never priced)
- Power upgrades to the room, and the second cluster you buy when the first fills
- Spot, committed-use and reserved-capacity discounts
- Security review, compliance, and data-residency work
- Fine-tuning, evaluation harnesses, and model upgrade cycles
- Prefill cost and the compute-bound regime at very large batch
- Spot and committed-use discounts, reserved capacity, enterprise agreements
- Network egress
- The cost of shipping a year behind

Several of these are large. The tool is a frame for an argument, not a quote.

Every default's provenance, the corrections made after checking them against
published figures, and the validation of the model against published break-even
guidance are in `SOURCES.md`.
