# neocloudcalc

**What a coding model really costs.** A single-page calculator that compares the
three-year total cost of ownership of an AI coding assistant across eight ways to
run one — and tells you how many developers each one can actually carry.

Open `index.html` in a browser. That is the whole app. No build step, no install,
no dependencies.

## The question it answers

Someone asks "should we just self-host a coding model?" An honest answer needs
capex, power, rack space, model storage, the people who babysit it, the hours
developers lose to a weaker model, and whether the thing can serve the team at
all. Not just a price per token.

This puts all of it on one scale.

## The eight routes

| Route | Group | Cost is mostly |
| --- | --- | --- |
| Local model on laptops | Your own hardware | Laptop uplift + lost developer time |
| GPUs you buy | Your own hardware | Card capex, power, rack, platform staff |
| GPUs you rent by the hour | Your own hardware | Hourly card rent |
| AWS Bedrock | Cloud platform | Tokens + cloud plumbing staff |
| Azure OpenAI | Cloud platform | Tokens + cloud plumbing staff |
| Anthropic API | Direct from the lab | Tokens + baseline platform team |
| OpenAI API | Direct from the lab | Tokens + baseline platform team |
| Flat per-seat plans | Direct from the lab | Seats + baseline platform team |
| Open model, frontier fallback | Hybrid | A small fleet + escalation tokens |

Every centralised route carries a baseline platform team — a gateway, secrets,
IAM, observability, evals and a security review do not appear only because the
endpoint is Bedrock. Bedrock, Azure and the self-hosted routes pay that **plus**
their own incremental staff. A switch zeroes it if you already run one.

Every route is scored on the same five components — hardware written down, power
and rack and storage, people, tokens and seats and GPU rent, and developer time
lost — so the bars stack on one scale.

## What it works out for you

**Cash, month by month.** Capital lands on day one; the cumulative chart shows
the cheque, not the accounting entry, and marks the month each self-hosted route
catches renting tokens — or says plainly that it never does. Plus the team size
above which owning wins, both at your quality assumption and at equal quality.

**A bill of materials.** If you are set on owning the iron, the itemised list
that goes to procurement: cards, spares, chassis, fabric, rack and smart hands,
then the setup hours, then the monthly run rate. One switch counts or excludes
setup and running labour — off, it models a team that already exists and absorbs
the work, which is the assumption most self-hosting business cases make silently.

**What moves the answer.** Every assumption swung 30% either way against the gap
between hosting it yourself and renting tokens. Bars that cross zero change the
winner, not just the bill.

**Beyond cost.** Where your code goes, time to stand up, what it costs to change
your mind, and whether it needs a hire.

**Sizing.** Pick an open-weight model from the catalogue (Qwen3-Coder, DeepSeek,
Kimi K2, GLM, Llama, gpt-oss, Devstral), a weight precision and an accelerator.
It computes weights in memory, KV cache, cards per replica, replica throughput,
replicas needed for your peak, checkpoint storage — and whether the thing fits in
a laptop at all.

**Capacity.** How many concurrent agentic coding sessions each route can sustain,
how many developers that is, and the headroom against your actual demand. Below
1.0× the route throttles and your developers queue. This is where per-seat plans
get interesting.

**Cost.** Monthly and over the full horizon, per developer and per million output
tokens, broken down by where the money goes.

## Two modes

**Simple** gives you three levers, because three is what actually moves the
answer: how many developers, how hard they use it, and how often the open-weight
model gets it right first time. The third shows you live what it costs as a
percentage of coding time.

Effectiveness comes as named profiles — Optimistic, Observed, Conservative,
Custom — anchored on SWE-bench Pro pass@1, which spans roughly 27–60% and is far
from saturated. Touch any of the six fields and the profile drops to Custom.

**Advanced** opens all six panels — workload, model and precision, money and
time, accelerators, facility and laptops, and every published rate — plus team
presets for Solo, Startup, Midsize and Enterprise.

Works on a phone, a tablet and a desktop.

## Using it

1. Start in **Simple**. Set the team size and pick a usage tier.
2. Drag **open-model first-pass acceptance** up to match the frontier and watch
   the ranking flip. That slider decides the whole argument.
3. Switch to **Advanced** to pick your model, precision and card, replace the
   list prices in **Model rates** with your contract rates, and put your own
   numbers in **Effectiveness** — those four fields are the only ones you cannot
   check against a vendor price list, and they are the ones that decide it.

## The finding

At 60 developers a frontier API bill is about $200 per developer per month.
Those developers cost roughly $10,000 each per month in loaded coding time. So a
**2% productivity penalty costs as much as the entire API bill.**

The tool no longer asks you to guess that penalty. It models the failure path:
**attempt → repair → retry → escalate → accept, or a person writes it.** Each
tier has a first-pass rate, a repair rate for the second and later tries, and a
share it never solves however many times you ask. Attempts are spent on the
hopeless share too, which is exactly why retry budgets cost money.

That produces the interesting result. **Open model with frontier fallback finishes
more work than either alone**, because it gets two independent shots — about 11%
of tasks still need a person against 26% on the frontier alone. Turn on *"cost the
tasks the agent cannot finish"* and the hybrid stops being sixth cheapest and
becomes first, by a factor of three. That switch is off by default, because
45 minutes of hand-written code is a softer number than a token price and should
not quietly swamp the rest of the model.

Every route reports **AI cost per accepted task** — named that way deliberately.
It is the AI spend plus the *differential* developer time, not the fully loaded
cost of shipping the change; ordinary review and engineering labour exists on
every route and is not this tool's to count. Accepted output is held constant
across routes, so the figure is comparable in a way cost per developer per month
is not.

The **Quality budget** figure shows the share of developer time the self-hosted
saving actually buys. When it is smaller than what your acceptance gap costs, no
amount of GPU shopping changes the answer. Self-hosting a coding model is a bet
on the open model being nearly as good — not on it being cheaper.

## Health warning

Every rate, card price and model spec is a default typed in from public figures
checked in September 2026. They move. They are assumptions in a model, not a
quote.

`SOURCES.md` records where each one came from, which three were wrong enough to
change the answer, and how the model checks out against published break-even
guidance. Short version: cost per developer per month lands at $200 against
Anthropic's reported $150–250, and the self-hosting break-even lands at ~67
developers and ~$160K/year of API spend, inside the published $50K–500K hybrid
band.

## Getting it out of the browser

**Print or save as PDF** gives a clean document: the verdict, all eight routes,
the bill of materials, and every assumption listed at the end so nobody has to
ask what you plugged in.

**CSV** carries the same thing as numbers a spreadsheet can work with —
assumptions, sizing, the route comparison with its five cost components, and the
bill of materials line by line. Download asks you to confirm and writes the file;
Copy is there for anywhere that will not let a page save one.

## Deploying it

`.github/workflows/pages.yml` publishes the site to GitHub Pages on every push.
It needs one switch flipped first: **Settings → Pages → Source → GitHub Actions**.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | The entire application — markup, styles, sizing, capacity, cash and cost model |
| `ARCHITECTURE.md` | Specification: catalogues, formulas, design tokens, omissions |
| `SOURCES.md` | Every default's provenance, the corrections, and validation against published figures |
| `.github/workflows/pages.yml` | Publishes the site to GitHub Pages |
| `AGENTS.md` | Directions for AI agents working in this repo |
