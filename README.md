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
| Anthropic API | Direct from the lab | Tokens |
| OpenAI API | Direct from the lab | Tokens |
| Flat per-seat plans | Direct from the lab | Seats |

Every route is scored on the same five components — hardware written down, power
and rack and storage, people, tokens and seats and GPU rent, and developer time
lost — so the bars stack on one scale.

## What it works out for you

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

## Using it

1. Hit a preset — Solo, Startup, Midsize, Enterprise.
2. Set team size and tokens per developer per day in **Team & workload**.
3. Pick your model, precision and card in **Open-weight model** and
   **Accelerators**.
4. Open **Model rates** and replace the list prices with your contract rates.
5. Read the ranking. Then set **Open-model time penalty** to 0 in **Money & time**
   and read it again — that one field decides the whole argument.

## Health warning

Every rate, card price and model spec is a default typed in from public figures.
They move. They are assumptions in a model, not a quote. `ARCHITECTURE.md` has
every formula, where each default came from, and an explicit list of what is not
modelled.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | The entire application — markup, styles, sizing, capacity and cost model |
| `ARCHITECTURE.md` | Specification: catalogues, formulas, design tokens, omissions |
| `AGENTS.md` | Directions for AI agents working in this repo |
