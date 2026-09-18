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
replicaTPS    = (cardsPerReplica × bw / bytesPerToken)
                × bandwidth_efficiency
                × min(batch, 64)
```

This is the right first-order answer and wrong at the edges. It ignores prefill,
ignores the compute-bound regime at very large batch, and ignores interconnect
stalls in tensor parallelism. The `bandwidth_efficiency` input (default 65%) is
where you absorb that; the batch multiplier is capped at 64 so the number cannot
run away.

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

## 6. Design system

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

### Layout idiom

Repeated groups are laid out as a grid with `gap: 1px` over a line-coloured
background, which draws hairline rules between cells without per-cell borders.
Where a grid can leave an uneven tail (the sizing strip), the container is
surface-coloured and each cell carries a 1px `outline` instead, so empty space
reads as empty rather than as a grey block.

---

## 7. Deliberate omissions

Not modelled, and worth saying out loud:

- Procurement lead time and the cost of waiting for cards
- Security review, compliance, and data-residency work
- Fine-tuning, evaluation harnesses, and model upgrade cycles
- Prefill cost and the compute-bound regime at very large batch
- Spot and committed-use discounts, reserved capacity, enterprise agreements
- Network egress
- The cost of shipping a year behind

Several of these are large. The tool is a frame for an argument, not a quote.
