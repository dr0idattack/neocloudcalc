# Where the numbers come from

Every default in `index.html` is a figure typed in from a public source, checked
in September 2026. This file records what each one is, what the research said,
and whether the tool agreed. **Prices move. Re-check before you quote any of
this to anyone.**

Three of the original defaults were wrong enough to change the answer. They are
marked **CORRECTED**.

---

## 1. API token rates

| Default | Was | Now | Source |
| --- | --- | --- | --- |
| Anthropic input / output | $3 / $15 | **$2 / $10** | Claude Sonnet 5 current rate. Sonnet 4.6 stays at $3/$15; Opus 5 is $5/$25 |
| Anthropic cache read | $0.30 | **$0.20** | Prompt caching cuts cached input by 90% |
| OpenAI input / output | $1.25 / $10 | **$4 / $20** | GPT-5.6 Sol promotional rate, held at least through 21 Nov 2026. List is $5/$30 |
| OpenAI cached input | $0.125 | **$0.40** | Cached input is 10% of standard input on the GPT-5.4–5.6 tiers |
| Bedrock | $3 / $15 | **$2 / $10** | Base per-token rates are identical across Bedrock, Claude Platform on AWS and the direct API |
| Azure | $1.25 / $10 | **$4 / $20** | Tracks OpenAI list. Claude on Microsoft Foundry bills at standard Anthropic API rates |
| Serverless open weights | — | **$0.30 / $1.20** | Blended rates across OpenRouter, Together AI and Fireworks AI for 70B/MoE models ($0.08 cache read, 5% aggregator fee) |

**CORRECTED.** The original rates were a model generation stale in both
directions — Anthropic had come down, OpenAI had gone up. The tool had OpenAI
as the cheap option; it is now the expensive one.

**Frontier simulation rate cards (`FRONTIER`).** The candidate model table compares
the workload across four frontier cards at list prices:
- **Claude Sonnet 5**: $2.00 input / $10.00 output / $0.20 cache read
- **Claude Opus 5**: $15.00 input / $75.00 output / $1.50 cache read
- **Claude Haiku 4.5**: $1.00 input / $5.00 output / $0.10 cache read
- **GPT-5.6 Sol**: $4.00 input / $20.00 output / $0.40 cache read

**Serverless open weights (`serverless`).** Rates for hosted open weights (e.g. Qwen 2.5 72B,
Llama 3.3 70B, DeepSeek V3) via API aggregators: $0.30 / M input, $1.20 / M output,
$0.08 / M cache read, plus a 5% platform/billing margin (`orFee`). The serverless route
applies the acceptance token multiplier (`openTokenMult`) to bill for extra retry attempts.

Worth knowing: because Bedrock and Azure carry the same per-token rates as going
direct, the only thing separating them in the tool is the platform staff line.
That is the honest difference, and it is what the cloud-ops FTE field is for.

Other rates not modelled, deliberately: batch processing is 50% cheaper across
both providers, and long-context requests above 272K tokens roughly double on
GPT-5.6.

## 2. Per-seat plans

| Plan | Price | Ceiling (`tpm`) | Target Audience / Notes |
| --- | --- | --- | --- |
| GitHub Copilot Pro | $10/mo | 300 | Individual inline suggestions and basic chat |
| Claude Pro | $20/mo | 350 | Individual 5-hour rolling message quota (~5.8 tok/s sustained) |
| Cursor Pro | $20/mo | 350 | Individual 500 fast requests/mo before slow-pool queueing |
| ChatGPT Plus | $20/mo | 350 | Individual rolling 3-hour caps on GPT-4o / reasoning |
| Claude Max 5x | $100/mo | 1,800 | 5× standard Pro volume for daily agentic workflows (~30 tok/s) |
| ChatGPT Pro | $200/mo | 7,000 | Unlimited reasoning and priority high-compute capacity (~116 tok/s) |
| Claude Max 20x | $400/mo | 7,000 | 20× volume tier for heavy autonomous agent sessions (~116 tok/s) |
| Cursor Standard | $40/mo | 900 | Small team pool with team management |
| Cursor Premium | $120/mo | 2,200 | Heavy team agent usage (~37 tok/s sustained) |
| GitHub Copilot Enterprise | $39/mo | 900 | Enterprise tier, requires $21 GitHub Enterprise Cloud base |

Default plan changed from $150 to **$120** — Cursor's Premium tier, the one actually
aimed at team agentic coding.

**Throughput ceilings (`tpm`).** Individual $20 plans carry strict rolling-window
request quotas that translate to roughly 350 tokens per minute (~5.8 tok/s) of continuous
output. Because an agent loop generates 20–50+ tok/s while active, a $20 seat throttles
quickly under heavy agentic workloads. Teams either upgrade to premium tiers ($100–$200/mo)
or switch to metered API keys. Reported real all-in spend across seat plus token for
teams mixing inline and agentic tools is $200–600 per developer per month.

## 3. Workload — and the tool's best validation

Anthropic's enterprise deployment data reports **$13 per developer per active
day**, **$150–250 per developer per month**, with 90% of users under $30/day.

The tool's "Heavy" tier is 10M input and 300k output tokens per developer per
day. Priced at Sonnet 5 rates with 75% cache hits, that comes to **$200 per
developer per month** — the middle of Anthropic's reported band. Independently,
a published breakdown puts coding-agent spend at $36/month light, $178/month
daily-pro and $594/month full-day agent; $200 sits where it should.

The workload defaults were already right. No change.

## 4. Accelerators

| Card | Buy (was → now) | Rent $/hr (was → now) |
| --- | --- | --- |
| H100 80GB | $28,000 → **$31,000** | $2.80 → **$2.40** |
| H200 141GB | $33,000 → **$34,000** | $3.40 → **$3.20** |
| B200 180GB | $45,000 → **$55,000** | $6.00 (unchanged) |
| A100 80GB | $16,000 → **$12,000** | $1.80 → **$1.10** |
| MI300X 192GB | $20,000 → **$18,000** | $2.20 → **$2.00** |

Purchase: H100 street prices run $25K–40K, around $31K typical for a new 80GB
card. H200 is about $31K per GPU. An 8-GPU HGX H100 system is $250K–320K, which
is what the "host, NIC, fabric per 8 cards" default of $45,000 reconciles
against ($248K of cards plus chassis). A DGX B200 clears $500K.

Rent: the spread is enormous and the median has been falling.

- H100: $1.49–$6.98/hr across 15+ providers. Vast.ai $1.49, RunPod $1.99,
  Lambda $3.99, CoreWeave $4.25, hyperscaler on-demand up to $12.
- A100: $0.80–$3.00, now sub-$1 on the open market.
- H200: $2.30–$13.78, cohort median ~$4.47, bare metal $2.14–$3.59.
- B200: median $6.11, range $3.44–$16.11.

Defaults sit near the neocloud end rather than the hyperscaler end, because
that is where someone actually shopping for inference capacity would buy.

## 5. Facility and people

| Default | Value | Source |
| --- | --- | --- |
| Rack and cooling | $200/kW/month | GPU-density colocation runs $150–250/kW/month. Wholesale averages $196/kW/month across primary North American markets; $80–130 at 1MW+ |
| Loaded platform engineer | $180,000 → **$260,000** | **CORRECTED.** ML infrastructure base is $130–200K, but fully loaded year-one cost is $210–370K. A $160K base costs $215–240K loaded |
| Loaded developer | $95/hour | Unchanged — consistent with a fully loaded engineer over 2,080 hours |
| Staffing ramp ceiling (`platformAt`) | 20 developers | A solo dev or small team does not employ 0.5+ dedicated platform FTEs; ongoing staffing scales `min(1, devs/20)` |

**The small-team staffing ramp.** Previously, the model billed full platform overhead
even for a single developer (~$10,800/mo in platform, admin rota and cloud-ops FTEs
against ~$200 of tokens), making self-hosting absurdly expensive at small scale.
Ongoing staffing now ramps linearly with team size:
`teamRamp = platformAt > 0 ? Math.min(1, devs / platformAt) : 1` (defaulting to full
headcount at 20 devs). Fixed one-off setup labour (architecture, bring-up, security review)
does not ramp because standing up a serving cluster requires the same hours regardless
of team size.

## 6. Throughput — the biggest correction

**CORRECTED, and it mattered most.**

Published vLLM measurements on H100:

- Llama 70B FP8 on 4 cards: **~3,400 output tok/s** at 256 concurrency
- Llama 8B FP8 on 1 card: **~11,200 output tok/s** at 256 concurrency

The original model predicted ~7,960 tok/s for the first case — **2.3x too
high**. Overstating throughput understates the fleet, which understates the cost
of self-hosting. The tool was flattering the option it should have been hardest
on.

Two guards fixed it:

1. **Batch multiplier capped at 32** (was 64). With 65% bandwidth efficiency
   that gives an effective ~21x. Against the two benchmarks: ~4,000 predicted
   vs 3,400 measured (+17%), and ~8,700 predicted vs 11,200 measured (−22%).
   Both within about 25%, which is the right accuracy for a planning tool.
2. **A single-stream ceiling, default 250 tok/s.** The bandwidth term alone
   claimed a 5B-active mixture-of-experts model decodes at 1,280 tok/s on one
   stream. Nothing does. Kernel launches, attention and sampling cap a single
   stream far below the weights-read limit. This is what dropped the gpt-oss
   120B replica figure from an absurd 20,494 tok/s to a believable 4,000.

Both are editable fields, not buried constants.

## 7. Does the whole thing gel?

Published break-even guidance:

- Self-hosting a 70B breaks even near **5–10M tokens per day** against a premium
  API tier.
- Under **~$50K/year** of spend, use the API — the volume will not keep a GPU
  busy and one engineer costs more than the bill.
- **$50K–500K/year**: hybrid.
- Over **~$500K/year** of steady volume, a well-utilised cluster usually wins.
- Self-hosting costs 10–20 engineering hours per month in maintenance, $750–3,000
  in labour.

Replaying the corrected simulator's own formulas:

| Test | Result | Verdict |
| --- | --- | --- |
| Cost per developer per month, heavy usage, Anthropic rates | **$200** | Matches Anthropic's reported $150–250 |
| Break-even team size, buying H100s, equal quality assumed | **67 developers**, ~$160K/year of API spend | Lands in the published $50K–500K hybrid band |
| Output volume at break-even | ~20M output tokens/day | Same order as the published 5–10M, on the conservative side |
| Renting instead of buying | Beats the API at 63 developers | Rent crosses slightly earlier than buying, as expected |
| Same test after itemising the real build | **125 developers** | See below |
| Same test again, after topology-aware sizing, the baseline platform team and the acceptance-driven token multiplier | **150 developers** | Each correction moved it further from self-hosting |
| With the default acceptance gap | Self-hosting never wins, even at 1,000 developers | See below |

The break-even figures above were measured before the bill of materials existed.
Itemising what a real build actually costs — spare cards, fabric and optics,
rack and smart hands, hardware support, and 400 hours of setup labour — pushed
break-even from **67 developers to 125**, nearly double, and later corrections
took it to **150**. None of those lines are
exotic; they are simply the ones a napkin comparison of "GPU price versus token
price" leaves out. That gap is the single best argument for itemising.

The tool agrees with the literature wherever the literature is specific, and it
is conservative — it asks for a slightly bigger team before self-hosting wins
than the published rules of thumb do.

## 9. Effectiveness — the least knowable numbers in the model

The flat 15% "open-model time penalty" was the weakest thing in the tool. It was
an effectiveness assumption presented as an infrastructure one, and it swamped
every other input. It is now derived from first-pass acceptance, which is at
least a measurable quantity.

**Benchmark acceptance.** On SWE-bench Verified the frontier sits around 95–96%
(GPT-5.6 Sol 96.2%, Fable 5 95.0%) and the best open-weight models around 77–81%
(DeepSeek V4 Pro 80.6%, MiniMax M3 80.5%, Qwen3.6-27B 77.2%). Two warnings come
with those figures: Verified is close to saturated, so the discriminating
benchmarks have moved to SWE-bench Pro, FrontierSWE and Terminal-Bench, where
the gap is wider; and the numbers are overwhelmingly vendor self-reported — one
tracker lists 0 of 104 entries as independently verified.

**Real-world acceptance is far lower.** On production codebases, top agent
harnesses land **35–50%** first-pass, with the best model-and-harness combination
resolving 38.8% pass@1. That is the number that matters, and it is roughly half
the benchmark figure.

**A better anchor.** SWE-bench Pro pass@1 spans roughly **27.4% to 59.9%** across
current models and is nowhere near saturated, which makes it a far better guide
than Verified. The tool's three named profiles are pinned to that spread:
Optimistic 58/48, Observed 45/34, Conservative 36/25 (frontier/open first pass).

**Defaults chosen:** frontier 45%, open 34%. The frontier figure sits inside the
published 35–50% band. The open figure applies a ratio slightly harsher than the
benchmark gap, because the gap widens on the harder, less saturated benchmarks.

**Review burden is real and rising.** Median review duration is reported up
441.5% since teams adopted AI, and time to first review roughly doubled — which
is what `minutes_per_attempt` stands in for. Notably, "effective cost per
accepted task" is itself now a named 2026 benchmark outcome, alongside first-pass
success, retries and review burden. The framing is not this tool's invention.

**Retries are not fresh coin flips.** An earlier version used
`attempts = 1 / firstPassAcceptance`, which assumes every retry is an independent
Bernoulli trial at the same probability. Coding agents do not behave that way:
benchmark pass@1 is measured across independent rollouts, not as the chance a
*failed* task succeeds next time, and some tasks are simply beyond a given model —
one reported case went 0-for-64 across every configuration tried. The model now
separates a first pass, a weaker repair pass, and a share never solved at all,
and spends attempts on the hopeless share too.

**Treat these fields as the ones to measure yourself.** Every other default
here can be checked against a vendor price list. These cannot. They vary by
workload, by repository, by harness, and by what your team will tolerate — an
open model might be no worse on a well-scoped change and unusable on an
autonomous refactor. A single acceptance rate is a deliberate simplification of a
distribution, and the tool's sensitivity pass marks both acceptance fields as
able to flip the answer rather than merely move the bill.

## 10. The finding that actually settles it

At 60 developers the frontier API bill is about **$200 per developer per month**.
Those same 60 developers cost roughly **$10,000 each per month** in loaded
coding time.

So a **2% productivity penalty costs exactly as much as the entire frontier API
bill.** At the tool's default acceptance gap the drag term is several times the
API spend, and no fleet arithmetic recovers it.

This is why the tool now shows a **Quality budget** figure: the percentage of
developer time that the self-hosted saving actually buys. When that number is
smaller than the penalty you believe in, the spreadsheet is not the thing
deciding the question, and no amount of GPU shopping changes that.

The honest conclusion is not "never self-host". It is that self-hosting a coding
model is a bet on the open-weight model being *nearly as good*, not on it being
cheaper. Raise open-model acceptance to match the frontier where that bet is safe
— a well-scoped internal task, a batch job, a non-frontier workload — and the cost
case comes back immediately.

And there is a third answer the earlier versions could not express. Routing the
open model first and escalating what it cannot finish gets **two independent
shots**, so it finishes more work than either tier alone. Cost the tasks that
still need a person and that hybrid stops being sixth and becomes first, by a
wide margin. The question worth asking is not open versus frontier. It is which
routing policy minimises cost per accepted task.

---

## Sources

- [Anthropic API pricing 2026 — Finout](https://www.finout.io/blog/anthropic-api-pricing)
- [Claude pricing in 2026 — CloudZero](https://www.cloudzero.com/blog/claude-pricing/)
- [Claude API pricing, September 2026 — BenchLM](https://benchlm.ai/anthropic/api-pricing)
- [Claude on AWS: Bedrock vs Claude Platform costs — CloudZero](https://www.cloudzero.com/blog/claude-on-aws-bedrock/)
- [Amazon Bedrock pricing 2026 — CloudZero](https://www.cloudzero.com/blog/amazon-bedrock-pricing/)
- [Amazon Bedrock pricing — AWS](https://aws.amazon.com/bedrock/pricing/)
- [OpenAI API pricing 2026 — Morph](https://www.morphllm.com/openai-api-pricing)
- [OpenAI API pricing, September 2026 — BenchLM](https://benchlm.ai/openai/api-pricing)
- [GPT-5.5 model reference — OpenAI](https://developers.openai.com/api/docs/models/gpt-5.5)
- [AI coding costs 2026 — Morph](https://www.morphllm.com/ai-coding-costs)
- [AI coding assistant pricing and ROI guide 2026 — DX](https://getdx.com/blog/ai-coding-assistant-pricing/)
- [GitHub Copilot Enterprise pricing 2026 — CloudZero](https://www.cloudzero.com/blog/github-copilot-enterprise-pricing/)
- [AI coding tools pricing compared 2026 — amux](https://amux.io/blog/ai-coding-tools-pricing-2026/)
- [How Claude Code is used in practice — Anthropic](https://www.anthropic.com/research/claude-code-expertise)
- [Why Claude Code uses so many tokens — Usagebar](https://usagebar.com/blog/why-does-claude-code-use-so-many-tokens)
- [H100 GPU cost 2026: buy, rent, cloud — CloudZero](https://www.cloudzero.com/blog/h100-gpu-cost/)
- [NVIDIA AI GPU pricing guide 2026 — IntuitionLabs](https://intuitionlabs.ai/articles/nvidia-ai-gpu-pricing-guide)
- [H100 rental prices across 15+ providers — IntuitionLabs](https://intuitionlabs.ai/articles/h100-rental-prices-cloud-comparison)
- [H100/H200/B200 cloud GPU pricing 2026 — Shattered](https://shattered.io/h100-h200-b200-cloud-gpu-pricing-2026/)
- [GPU rental price index — getdeploying](https://getdeploying.com/gpu-price-index)
- [NVIDIA H100 price guide 2026 — Jarvislabs](https://jarvislabs.ai/blog/h100-price)
- [vLLM vs SGLang vs TensorRT-LLM: Llama 3.1 70B bench — Cerebrium](https://cerebrium.ai/blog/benchmarking-vllm-sglang-tensorrt-for-llama-3-1-api)
- [vLLM v0.6.0 performance update — vLLM](https://vllm.ai/blog/2024-09-05-perf-update)
- [GPU cost per token benchmark 2026 — Spheron](https://www.spheron.network/blog/gpu-cost-per-token-benchmark-llm-inference-2026/)
- [Local LLMs vs cloud APIs: 2026 TCO analysis — SitePoint](https://www.sitepoint.com/local-llms-vs-cloud-api-cost-analysis-2026/)
- [Self-hosting an LLM: is it actually cheaper than the API? — LeanLM](https://leanlm.ai/blog/self-hosting-llm-cost)
- [Open source vs closed API LLM cost comparison — Lyceum](https://lyceum.technology/magazine/open-source-vs-closed-api-llm-cost-comparison/)
- [Self-host LLM vs API: real cost breakdown 2026 — DevTk](https://devtk.ai/en/blog/self-hosting-llm-vs-api-cost-2026/)
- [Colocation pricing in 2026: per-kW math — AGI Beacon](https://www.agibeacon.com/post/colocation-pricing-in-2026-per-kw-math-power-premiums-and-what-s-negotiable)
- [Data center pricing benchmarks 2026 — ColocationScout](https://colocationscout.com/data-center-pricing-benchmarks.html)
- [Colocation data center pricing 2026 — datacenterHawk](https://datacenterhawk.com/resources/fundamentals/colocation-data-center-pricing-a-2026-beginner-s-guide)
- [Cost of hiring an ML engineer 2026 — Stealth Agents](https://stealthagents.com/research/cost-of-hiring-a-machine-learning-engineer-2026)
- [MLOps engineer salary 2026 — KORE1](https://www.kore1.com/mlops-engineer-salary-guide/)
- [Platform engineer salary guide 2026 — KORE1](https://www.kore1.com/platform-engineer-salary-guide-2026/)
- [Best open-source coding model 2026 — Morph](https://www.morphllm.com/best-open-source-coding-model-2026)
- [SWE-bench Pro leaderboard — Scale](https://labs.scale.com/leaderboard/swe_bench_pro_public)
- [Coding agent benchmarks 2026 — Presenc AI](https://presenc.ai/research/coding-agent-benchmarks-2026)
- [SWE-bench Pro leaderboard, September 2026 — Morph](https://www.morphllm.com/swe-bench-pro)
- [SWE-bench leaderboard 2026, what the scores mean — CodeAnt](https://codeant.ai/blogs/swe-bench-scores)
- [Your coding agent's leaderboard score isn't a production guarantee — HackerNoon](https://hackernoon.com/your-coding-agents-leaderboard-score-isnt-a-production-guarantee)
- [GitHub Copilot Enterprise pricing 2026 — CloudZero](https://www.cloudzero.com/blog/github-copilot-enterprise-pricing/)
- [OpenRouter model pricing and throughput index — OpenRouter](https://openrouter.ai/docs#models)
- [Together AI serverless inference pricing 2026 — Together AI](https://www.together.ai/pricing)
- [Fireworks AI serverless pricing — Fireworks AI](https://fireworks.ai/pricing)
- [Cursor pricing and usage limits 2026 — Cursor](https://www.cursor.com/pricing)
- [Claude Pro and Max plan limits — Anthropic](https://support.anthropic.com/en/articles/8324991-about-claude-pro-and-team)
- [ChatGPT Plus and Pro pricing and rate limits — OpenAI](https://openai.com/chatgpt/pricing/)
