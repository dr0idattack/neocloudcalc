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

**CORRECTED.** The original rates were a model generation stale in both
directions — Anthropic had come down, OpenAI had gone up. The tool had OpenAI
as the cheap option; it is now the expensive one.

Worth knowing: because Bedrock and Azure carry the same per-token rates as going
direct, the only thing separating them in the tool is the platform staff line.
That is the honest difference, and it is what the cloud-ops FTE field is for.

Other rates not modelled, deliberately: batch processing is 50% cheaper across
both providers, and long-context requests above 272K tokens roughly double on
GPT-5.6.

## 2. Per-seat plans

| Plan | Price |
| --- | --- |
| GitHub Copilot Enterprise | $39/user, but requires a GitHub Enterprise Cloud seat at $21 — $60 effective |
| Cursor Standard / Premium | $40 / $120 per month, Premium being 5x usage for heavy agent workloads |
| Claude Code enterprise | $20/seat plus usage at API rates |

Default changed from $150 to **$120** — Cursor's Premium tier, the one actually
aimed at agentic coding. Reported real all-in spend across seat plus token for
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
| Break-even team size, buying H100s, quality penalty off | **67 developers**, ~$160K/year of API spend | Lands in the published $50K–500K hybrid band |
| Output volume at break-even | ~20M output tokens/day | Same order as the published 5–10M, on the conservative side |
| Renting instead of buying | Beats the API at 63 developers | Rent crosses slightly earlier than buying, as expected |
| Same test after itemising the real build | **125 developers** | See below |
| With the 15% penalty on | Self-hosting never wins, even at 1,000 developers | See below |

The break-even figures above were measured before the bill of materials existed.
Itemising what a real build actually costs — spare cards, fabric and optics,
rack and smart hands, hardware support, and 400 hours of setup labour — pushed
break-even from **67 developers to 125**, nearly double. None of those lines are
exotic; they are simply the ones a napkin comparison of "GPU price versus token
price" leaves out. That gap is the single best argument for itemising.

The tool agrees with the literature wherever the literature is specific, and it
is conservative — it asks for a slightly bigger team before self-hosting wins
than the published rules of thumb do.

## 8. The finding that actually settles it

At 60 developers the frontier API bill is about **$200 per developer per month**.
Those same 60 developers cost roughly **$10,000 each per month** in loaded
coding time.

So a **2% productivity penalty costs exactly as much as the entire frontier API
bill.** At the tool's default 15% penalty, the drag term is about $1,500 per
developer per month — more than seven times the API spend — and no fleet
arithmetic can recover it.

This is why the tool now shows a **Quality budget** figure: the percentage of
developer time that the self-hosted saving actually buys. When that number is
smaller than the penalty you believe in, the spreadsheet is not the thing
deciding the question, and no amount of GPU shopping changes that.

The honest conclusion is not "never self-host". It is that self-hosting a coding
model is a bet on the open-weight model being *nearly as good*, not on it being
cheaper. Set the penalty to 0 where that bet is safe — a well-scoped internal
task, a batch job, a non-frontier workload — and the cost case comes back
immediately.

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
