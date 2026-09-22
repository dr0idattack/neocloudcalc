#!/usr/bin/env python3
"""Build the offline Excel edition of the coding-model TCO calculator.

Every number in the delivered workbook is a formula over the Inputs sheet, so
the file recalculates like the web app rather than freezing one scenario. No
macros: the workbook is a plain .xlsx and every function used here predates
Excel 2016, which keeps it working on Windows, macOS, LibreOffice and Google
Sheets alike.

Run:  python3 tools/build_xlsx.py  [output.xlsx]
"""
import sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.formatting.rule import CellIsRule, DataBarRule
from openpyxl.chart import BarChart, LineChart, Reference

OUT = sys.argv[1] if len(sys.argv) > 1 else "Coding-Model-TCO-Calculator.xlsx"

# ── house style ──────────────────────────────────────────────────────────
FONT = "Arial"
INK      = "1A1A1A"
MUTED    = "6B7280"
INPUT_B  = "0000FF"          # blue: type here
LINK_G   = "008000"          # green: pulled from another sheet
RULE     = "D4D8DE"
BAND     = "F4F6F8"
HEAD_BG  = "1F3A5F"
ACCENT   = "125EC4"
GOOD     = "0F7B4F"
BAD      = "B42318"

MONEY  = '$#,##0;($#,##0);"-"'
MONEY2 = '$#,##0.00;($#,##0.00);"-"'
PCT    = '0.0%'
NUM    = '#,##0'
NUM1   = '#,##0.0'
NUM2   = '#,##0.00'
MULT   = '0.00"x"'

thin = Side(style="thin", color=RULE)
BOX  = Border(left=thin, right=thin, top=thin, bottom=thin)
UNDER = Border(bottom=thin)


def f(sz=10, b=False, color=INK, i=False):
    return Font(name=FONT, size=sz, bold=b, color=color, italic=i)


class Sheet:
    """Thin wrapper that remembers where it put things."""

    def __init__(self, wb, title, widths):
        self.ws = wb.create_sheet(title)
        self.title = title
        self.r = 1
        for i, w in enumerate(widths, start=1):
            self.ws.column_dimensions[get_column_letter(i)].width = w
        self.ws.sheet_view.showGridLines = False

    def cell(self, row, col, value=None, font=None, fmt=None, fill=None,
             align=None, border=None, wrap=False):
        c = self.ws.cell(row=row, column=col)
        if value is not None:
            c.value = value
        c.font = font or f()
        if fmt:
            c.number_format = fmt
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)
        if align or wrap:
            c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=wrap)
        if border:
            c.border = border
        return c

    def title_row(self, text, sub=None):
        self.cell(self.r, 1, text, f(16, True, HEAD_BG))
        self.r += 1
        if sub:
            self.cell(self.r, 1, sub, f(9, color=MUTED))
            self.r += 1
        self.r += 1

    def section(self, text, span=5):
        for col in range(1, span + 1):
            self.cell(self.r, col, None, fill=HEAD_BG)
        self.cell(self.r, 1, text.upper(), f(9, True, "FFFFFF"), fill=HEAD_BG)
        self.r += 1

    def blank(self, n=1):
        self.r += n


# ═══ catalogues, verbatim from index.html ════════════════════════════════
MODELS = [
    ("Qwen3-Coder 480B-A35B", 480, 35, 0.25),
    ("DeepSeek-V3 671B-A37B", 671, 37, 0.07),
    ("Kimi K2 1T-A32B", 1000, 32, 0.06),
    ("GLM 355B-A32B", 355, 32, 0.22),
    ("Llama 3.1 405B dense", 405, 405, 0.52),
    ("gpt-oss 120B-A5.1B", 117, 5.1, 0.14),
    ("Llama 3.3 70B dense", 70, 70, 0.31),
    ("Qwen3 32B dense", 32, 32, 0.26),
    ("Devstral 24B dense", 24, 24, 0.16),
    ("gpt-oss 20B-A3.6B", 21, 3.6, 0.09),
]
QUANTS = [("BF16 / FP16", 2.0, 1.0), ("FP8 / INT8", 1.0, 0.5), ("INT4 / MXFP4", 0.55, 0.5)]
GPUS = [
    ("A100 80GB SXM", 80, 2039, 312, 12000, 1.10, 400),
    ("H100 80GB SXM", 80, 3350, 990, 31000, 2.40, 700),
    ("H200 141GB SXM", 141, 4800, 990, 34000, 3.20, 700),
    ("B200 180GB", 180, 8000, 2250, 55000, 6.00, 1000),
    ("MI300X 192GB", 192, 5300, 1300, 18000, 2.00, 750),
    ("L40S 48GB", 48, 864, 362, 8000, 1.10, 350),
    ("RTX 6000 Ada 48GB", 48, 960, 364, 7000, 0.90, 300),
    ("RTX 5090 32GB", 32, 1792, 838, 2500, 0.70, 575),
]
PLANS = [
    ("GitHub Copilot Pro - individual", 10, 0, 300),
    ("Claude Pro - individual", 20, 0, 350),
    ("Cursor Pro - individual", 20, 0, 350),
    ("ChatGPT Plus - individual", 20, 0, 350),
    ("Claude Max 5x - individual", 100, 0, 1800),
    ("Claude Max 20x - individual", 200, 0, 7000),
    ("ChatGPT Pro - individual", 200, 0, 7000),
    ("Cursor Standard - team", 40, 0, 900),
    ("Cursor Premium - team", 120, 0, 2200),
    ("GitHub Copilot Enterprise", 39, 21, 900),
]
FRONTIER = [
    ("Claude Sonnet 5", "Anthropic", 2, 10, 0.20),
    ("Claude Opus 5", "Anthropic", 15, 75, 1.50),
    ("Claude Haiku 4.5", "Anthropic", 1, 5, 0.10),
    ("GPT-5.6 Sol", "OpenAI", 4, 20, 0.40),
]
# label, acceptF, acceptO, repairF, repairO, hardF, hardO   (as fractions)
PROFILES = [
    ("Observed - mid-range of published results", .45, .34, .35, .30, .05, .12),
    ("Optimistic - top of SWE-bench Pro", .58, .48, .40, .35, .03, .08),
    ("Conservative - hard, unfamiliar repos", .36, .25, .28, .22, .10, .22),
]

ROUTES = [
    ("laptop",     "Local model on laptops",            "Your own hardware"),
    ("buy",        "GPUs you buy",                      "Your own hardware"),
    ("rent",       "GPUs you rent by the hour",         "Your own hardware"),
    ("serverless", "Open model, hosted by someone else","Serverless open weights"),
    ("bedrock",    "AWS Bedrock",                       "Cloud platform"),
    ("azure",      "Azure OpenAI",                      "Cloud platform"),
    ("anthropic",  "Anthropic API",                     "Direct from the lab"),
    ("openai",     "OpenAI API",                        "Direct from the lab"),
    ("hybrid",     "Open model, frontier fallback",     "Hybrid"),
    ("seats",      "Flat per-seat plans",               "Direct from the lab"),
]

wb = Workbook()
wb.remove(wb.active)
NAMES = {}


def name(key, sheet, ref):
    NAMES[key] = "'{}'!{}".format(sheet, ref)


def register():
    for k, v in NAMES.items():
        wb.defined_names.add(DefinedName(k, attr_text=v))


print("scaffold ready")

# ═══ 1. Catalogues ═══════════════════════════════════════════════════════
cat = Sheet(wb, "Catalogues", [34, 13, 13, 13, 13, 13, 13])
cat.title_row("Catalogues",
              "Specifications and list prices the dropdowns on Inputs read from. "
              "Every figure here is a published list price or vendor spec; edit a cell to use your own.")

SPANS = {}


def table(key, head, rows, note=None):
    cat.section(head[0], span=len(head))
    for i, h in enumerate(head, start=1):
        cat.cell(cat.r, i, h, f(9, True, MUTED), align="center" if i > 1 else "left",
                 border=UNDER, wrap=True)
    cat.r += 1
    first = cat.r
    for j, row in enumerate(rows):
        for i, val in enumerate(row, start=1):
            fmt = None
            if i > 1 and isinstance(val, float) and val < 1:
                fmt = NUM2
            elif i > 1 and isinstance(val, (int, float)):
                fmt = NUM
            cat.cell(cat.r, i, val, f(9), fmt=fmt,
                     align="right" if i > 1 else "left",
                     fill=BAND if j % 2 else None)
        cat.r += 1
    SPANS[key] = (first, cat.r - 1)
    if note:
        cat.cell(cat.r, 1, note, f(8, color=MUTED, i=True))
        cat.r += 1
    cat.blank()
    return SPANS[key]


table("models", ["Open-weight model", "Total B", "Active B", "KV MB/k tok"],
      MODELS, "Active parameters drive decode speed; total parameters drive memory. "
              "A mixture-of-experts model holds all of the first and reads only the second.")
table("quants", ["Weight precision", "Bytes/param", "KV factor"], QUANTS)
table("gpus", ["Accelerator", "Memory GB", "Bandwidth GB/s", "Dense TFLOPS",
               "Buy $", "Rent $/h", "Draw W"], GPUS,
      "Purchase prices are street estimates for whole systems, not quotes.")
table("plans", ["Flat plan", "$/seat/mo", "Platform seat $", "Sustained tok/min"], PLANS,
      "Sustained tok/min is an ESTIMATE of what each plan's rate limits allow an agent to pull, "
      "not a published figure. Treat it as a starting point and measure your own.")
table("frontier", ["Frontier rate card", "Lab", "In $/M", "Out $/M", "Cache read $/M"], FRONTIER,
      "List prices move. Check them against the vendor's pricing page before quoting anyone.")
table("profiles", ["Effectiveness profile", "Frontier 1st pass", "Open 1st pass",
                   "Frontier repair", "Open repair", "Frontier never", "Open never"],
      PROFILES,
      "Anchored on SWE-bench Pro pass@1. To depart from a profile, type your own number into the "
      "Override column on Inputs - it beats the catalogue wherever it is not blank.")

for key, cols in (("models", "A"), ("quants", "A"), ("gpus", "A"),
                  ("plans", "A"), ("frontier", "A"), ("profiles", "A")):
    a, b = SPANS[key]
    name("cat_" + key, "Catalogues", "${0}${1}:${0}${2}".format(cols, a, b))

for key, last in (("models", "D"), ("quants", "C"), ("gpus", "G"),
                  ("plans", "D"), ("frontier", "E"), ("profiles", "G")):
    a, b = SPANS[key]
    name("tbl_" + key, "Catalogues", "$A${0}:${1}${2}".format(a, last, b))

for p in SPANS.values():
    for row in range(p[0], p[1] + 1):
        pass

print("catalogues:", SPANS)

# ═══ 2. Inputs ═══════════════════════════════════════════════════════════
inp = Sheet(wb, "Inputs", [42, 15, 13, 14, 74])
inp.title_row(
    "Coding assistant - three-year cost of ownership",
    "Offline edition. Change the blue cells; every other sheet recalculates. "
    "No macros, no add-ins, nothing to enable.")

legend = [
    ("Blue cells", "yours to change - these are the only cells you need to touch", INPUT_B),
    ("Override column", "leave blank to use the catalogue; type a number to beat it", INPUT_B),
    ("Black cells", "formulas - they recalculate, do not type over them", INK),
    ("Answer tab", "the recommendation, the ranking and the chart", LINK_G),
]
for lab, txt, col in legend:
    inp.cell(inp.r, 1, lab, f(9, True, col))
    inp.cell(inp.r, 2, txt, f(9, color=MUTED))
    inp.r += 1
inp.blank()

HEADS = ["Assumption", "Value", "Unit", "Override", "Where it comes from"]


def heads():
    for i, h in enumerate(HEADS, start=1):
        inp.cell(inp.r, i, h, f(9, True, MUTED), border=UNDER,
                 align="left" if i in (1, 5) else "center")
    inp.r += 1


VALIDATIONS = []


def add_sel(key, label, cat_key, default, note):
    a, b = SPANS[cat_key]
    dv = DataValidation(type="list",
                        formula1="=Catalogues!$A${}:$A${}".format(a, b),
                        allow_blank=False, showDropDown=False)
    inp.ws.add_data_validation(dv)
    c = inp.cell(inp.r, 2, default, f(10, True, INPUT_B), align="left", border=BOX,
                 fill="FFFDE7")
    dv.add(c)
    inp.cell(inp.r, 1, label, f(10, True))
    inp.cell(inp.r, 5, note, f(8, color=MUTED), wrap=True)
    name(key, "Inputs", "$B${}".format(inp.r))
    inp.r += 1


def add_yn(key, label, default, note):
    dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=False,
                        showDropDown=False)
    inp.ws.add_data_validation(dv)
    c = inp.cell(inp.r, 2, default, f(10, True, INPUT_B), align="center", border=BOX,
                 fill="FFFDE7")
    dv.add(c)
    inp.cell(inp.r, 1, label, f(10))
    inp.cell(inp.r, 5, note, f(8, color=MUTED), wrap=True)
    name(key, "Inputs", "$B${}".format(inp.r))
    inp.r += 1


def add_in(key, label, unit, default, fmt, note=""):
    inp.cell(inp.r, 1, label, f(10))
    inp.cell(inp.r, 2, default, f(10, color=INPUT_B), fmt=fmt, align="right", border=BOX)
    inp.cell(inp.r, 3, unit, f(9, color=MUTED))
    inp.cell(inp.r, 5, note, f(8, color=MUTED), wrap=True)
    name(key, "Inputs", "$B${}".format(inp.r))
    inp.r += 1


def add_cat(key, label, unit, cat_key, col, fmt, sel_name, note=""):
    """Catalogue value, beaten by anything typed into the Override column."""
    a, b = SPANS[cat_key]
    last = get_column_letter(len(MODELS[0]) if cat_key == "models" else 7)
    rng = "tbl_" + cat_key
    r = inp.r
    inp.cell(r, 1, label, f(10))
    inp.cell(r, 2, "=IF($D${0}<>\"\",$D${0},INDEX({1},MATCH({2},cat_{3},0),{4}))"
             .format(r, rng, sel_name, cat_key, col), f(10), fmt=fmt, align="right", border=BOX)
    inp.cell(r, 3, unit, f(9, color=MUTED))
    inp.cell(r, 4, None, f(10, color=INPUT_B), fmt=fmt, align="right", border=BOX, fill="FFFDE7")
    inp.cell(r, 5, note, f(8, color=MUTED), wrap=True)
    name(key, "Inputs", "$B${}".format(r))
    inp.r += 1


inp.section("The three choices that decide everything else")
heads()
add_sel("sel_model", "Open-weight model", "models", MODELS[5][0],
        "Which weights you would host yourself. Drives memory, fleet size and storage.")
add_sel("sel_quant", "Weight precision", "quants", QUANTS[1][0],
        "How hard you squeeze the weights. Halving the bytes halves the memory and roughly doubles decode speed.")
add_sel("sel_gpu", "Accelerator", "gpus", GPUS[1][0],
        "The card you would buy or rent.")
add_sel("sel_plan", "Flat per-seat plan", "plans", PLANS[8][0],
        "Which subscription the per-seat route prices. Individual plans are in this list too.")
add_sel("sel_profile", "Effectiveness profile", "profiles", PROFILES[0][0],
        "How well the models actually do. This is the single biggest lever in the whole model.")
inp.blank()

inp.section("Team and workload")
heads()
add_in("devs", "Developers", "", 60, NUM, "Everyone who would hold a licence or a session.")
add_in("workdays", "Working days", "/ mo", 21, NUM)
add_in("inTok", "Input tokens / dev / day", "M", 10, NUM1,
       "Agentic coding is input-heavy: the repo, the diff and the tool output go in on every turn.")
add_in("outTok", "Output tokens / dev / day", "k", 300, NUM,
       "Output is what the accelerators actually spend their time on.")
add_in("cacheShare", "Input served from cache", "%", 0.75, PCT,
       "Prompt caching is the largest single discount on any metered route.")
add_in("codeHrs", "Hours in the tool / dev / day", "h", 5, NUM1)
inp.blank()

inp.section("Effectiveness - the failure path, not just first pass")
heads()
for k, lab, col, note in (
        ("acceptFrontier", "Frontier first-pass acceptance", 2,
         "Share of tasks the frontier model gets right first time."),
        ("acceptOpen", "Open first-pass acceptance", 3,
         "The same for the open model you would host. The gap between these two rows is the whole argument."),
        ("repairFrontier", "Frontier repair success", 4,
         "A repair pass is worse than the first: the easy wins are already gone."),
        ("repairOpen", "Open repair success", 5, ""),
        ("hardFrontier", "Frontier never solves", 6,
         "Share no number of retries will clear. Retries are spent on these too, which is why retry budgets cost money."),
        ("hardOpen", "Open never solves", 7, "")):
    add_cat(k, lab, "%", "profiles", col, PCT, "sel_profile", note)
add_in("tasksDay", "Accepted tasks / dev / day", "", 5, NUM,
       "Held constant across routes, which is what makes cost per accepted task comparable.")
add_in("minPerAttempt", "Developer minutes per attempt", "min", 8, NUM,
       "Prompting, waiting, reading the diff.")
add_in("maxRetries", "Repair attempts before giving up", "", 2, NUM)
add_in("minPerHumanTask", "Minutes to write it by hand", "min", 45, NUM)
add_yn("countFallback", "Cost the tasks the agent cannot finish", "No",
       "Yes charges the human time to finish what the agent abandoned. It usually changes the ranking.")
inp.blank()
print("inputs through effectiveness:", inp.r)

inp.section("Serving and sizing")
heads()
add_in("ctxK", "Live context per request", "k tok", 64, NUM,
       "Drives the KV cache, which is often larger than people expect.")
add_in("batch", "Concurrent requests / replica", "", 16, NUM)
add_in("bwEff", "Bandwidth efficiency", "%", 0.65, PCT,
       "How much of the card's paper bandwidth a real serving stack reaches.")
add_in("streamCap", "Single-stream ceiling", "tok/s", 250, NUM,
       "Kernel launches, attention and sampling cap one stream far below the weights-read limit.")
add_in("ckpts", "Checkpoints kept on disk", "", 3, NUM)
add_in("sessConc", "Developers with a live session", "%", 0.60, PCT)
add_in("activeHrs", "Busy hours / day", "h", 8, NUM)
add_in("peak", "Peak-to-average", "x", 2, NUM1,
       "The fleet is sized on the busy hour, not the daily average.")
add_in("nodeSize", "Accelerators per node", "", 8, NUM)
add_in("multiNodeLoss", "Multi-node interconnect loss", "%", 0.20, PCT,
       "Crossing a node boundary costs real throughput: the fabric between nodes is far slower than the one inside.")
add_in("lapBw", "Laptop memory bandwidth", "GB/s", 546, NUM,
       "A high-end workstation laptop with unified memory.")
add_in("lapRam", "Laptop unified memory", "GB", 128, NUM)
inp.blank()

inp.section("Accelerator")
heads()
for k, lab, unit, col, fmt, note in (
        ("gpuVram", "Memory / card", "GB", 2, NUM, ""),
        ("gpuBw", "Memory bandwidth", "GB/s", 3, NUM, "Decode is bandwidth bound, so this sets throughput."),
        ("gpuTf", "Dense compute", "TFLOPS", 4, NUM, "Prefill is compute bound, so this sets time to first token."),
        ("gpuBuy", "Purchase price / card", "$", 5, MONEY, ""),
        ("gpuRent", "On-demand rent / card", "$/h", 6, MONEY2, ""),
        ("gpuW", "Card draw", "W", 7, NUM, "")):
    add_cat(k, lab, unit, "gpus", col, fmt, "sel_gpu", note)
add_in("hostCost", "Host, NIC, fabric / 8 cards", "$", 45000, MONEY)
add_in("rentUtil", "Rented fleet uptime", "%", 0.70, PCT,
       "Rented cards bill by the hour whether they are busy or idle.")
inp.blank()

inp.section("Facility and laptops")
heads()
add_in("pue", "Datacentre PUE", "x", 1.4, NUM2, "Power drawn per watt delivered to the card.")
add_in("kwhDc", "Datacentre electricity", "$/kWh", 0.10, MONEY2)
add_in("coloKw", "Rack space and cooling", "$/kW/mo", 200, MONEY)
add_in("storGb", "Model storage", "$/GB/mo", 0.08, MONEY2)
add_in("lapUplift", "Laptop uplift / dev", "$", 3000, MONEY,
       "What the memory-heavy machine costs over the standard issue.")
add_in("lapWatts", "Laptop draw while running", "W", 90, NUM)
add_in("lapSupport", "Laptop fiddling / dev / yr", "h", 6, NUM)
add_in("itRate", "IT support cost", "$/h", 75, MONEY)
add_in("kwhOffice", "Office electricity", "$/kWh", 0.14, MONEY2)
inp.blank()

inp.section("Build and labour")
heads()
add_yn("labourYN", "Count setup and running labour", "Yes",
       "No strips every hour of human time out of the comparison. It flatters self-hosting heavily.")
add_in("netFabric", "Fabric, optics and cabling", "$/host", 12000, MONEY)
add_in("installHost", "Rack, PDU and smart hands", "$/host", 3500, MONEY)
add_in("spares", "Spare cards held", "% of fleet", 0.05, PCT)
add_in("warranty", "Hardware support", "%/yr of capex", 0.10, PCT)
add_in("setupArch", "Architecture and procurement", "h", 80, NUM)
add_in("setupRack", "Rack, cable and bring-up", "h/host", 60, NUM)
add_in("setupStack", "Serving stack and cluster", "h", 120, NUM)
add_in("setupEval", "Model evaluation", "h", 80, NUM)
add_in("setupSec", "Security and compliance review", "h", 60, NUM)
inp.blank()

inp.section("Money and people")
heads()
add_in("horizon", "Horizon", "mo", 36, NUM)
add_in("amort", "Hardware write-off", "mo", 36, NUM)
add_in("devRate", "Loaded developer cost", "$/h", 95, MONEY)
add_in("fteCost", "Loaded platform engineer", "$/yr", 260000, MONEY)
add_in("platformFte", "Baseline AI platform team", "FTE", 0.5, NUM2,
       "Gateway, secrets, IAM, observability, evals and cost control. Every centralised route pays this, not just the cloud ones.")
add_in("platformAt", "Full platform team at", "devs", 20, NUM,
       "Staffing ramps with headcount and reaches full strength here. A solo developer does not employ a fifth of an engineer.")
add_in("soloAt", "Small-team advice up to", "devs", 3, NUM,
       "At or below this the recommendation talks about subscriptions instead of platforms.")
add_in("adminFte", "Platform engineers on the fleet", "FTE", 0.4, NUM2)
add_in("cloudOps", "Cloud plumbing staff", "FTE", 0.15, NUM2)
add_yn("ownsPlatform", "We already run an AI platform", "No",
       "Yes charges no baseline platform team, because you already pay for it.")
add_in("apiDiscount", "Negotiated API discount", "%", 0.00, PCT,
       "Applies to metered tokens only, never to seats.")
inp.blank()

inp.section("Rate cards")
heads()
for pre, lab in (("an", "Anthropic"), ("oa", "OpenAI"), ("bed", "Bedrock"), ("az", "Azure")):
    add_in(pre + "In", lab + " - input", "$/M", {"an": 2, "oa": 4, "bed": 2, "az": 4}[pre], MONEY2)
    add_in(pre + "Out", lab + " - output", "$/M", {"an": 10, "oa": 20, "bed": 10, "az": 20}[pre], MONEY2)
    add_in(pre + "Cache", lab + " - cache read", "$/M", {"an": .2, "oa": .4, "bed": .2, "az": .4}[pre], MONEY2)
    add_in(pre + "Tpm", lab + " ceiling", "k tok/min",
           {"an": 2000, "oa": 2000, "bed": 1000, "az": 1000}[pre], NUM)
add_in("orIn", "Serverless open - input", "$/M", 0.30, MONEY2,
       "Open weights bought by the token from an aggregator or a serving provider.")
add_in("orOut", "Serverless open - output", "$/M", 1.20, MONEY2)
add_in("orCache", "Serverless open - cache read", "$/M", 0.08, MONEY2)
add_in("orFee", "Aggregator credit fee", "%", 0.05, PCT)
add_in("orTpm", "Serverless ceiling", "k tok/min", 10000, NUM)
add_cat("seat", "Seat price", "$/dev/mo", "plans", 2, MONEY, "sel_plan")
add_cat("seatBase", "Platform seat it rides on", "$/dev/mo", "plans", 3, MONEY, "sel_plan",
        "Copilot Enterprise needs a GitHub Enterprise Cloud seat. Many buyers already hold one.")
add_cat("seatTpm", "Per-seat ceiling", "tok/min", "plans", 4, NUM, "sel_plan",
        "ESTIMATE of sustained throughput inside the plan's limits, not a published figure.")
add_yn("ownsBase", "We already pay for the platform seat", "No", "")

inp.ws.freeze_panes = "A4"
print("inputs done, last row", inp.r, "| names:", len(NAMES))

# ═══ 3. Workings ═════════════════════════════════════════════════════════
wk = Sheet(wb, "Workings", [40, 18, 11, 11, 11, 11, 11, 11, 11, 11])
wk.title_row("Workings",
             "Every intermediate the Answer sheet stands on. Nothing here is an input - "
             "it is all formulas over the Inputs tab, laid out so each step can be checked by hand.")


def w(label, formula, fmt=NUM2, key=None, note="", bold=False):
    wk.cell(wk.r, 1, label, f(10, bold))
    wk.cell(wk.r, 2, formula, f(10, bold), fmt=fmt, align="right", border=BOX)
    if note:
        wk.cell(wk.r, 3, note, f(8, color=MUTED))
    if key:
        name(key, "Workings", "$B${}".format(wk.r))
    wk.r += 1
    return "$B${}".format(wk.r - 1)


wk.section("1. Token volumes for the month", span=3)
w("Input tokens", "=devs*inTok*1000000*workdays", NUM, "m_inTok")
w("Output tokens", "=devs*outTok*1000*workdays", NUM, "m_outTok")
w("Input served from cache", "=m_inTok*MIN(1,cacheShare)", NUM, "m_cached")
w("Fresh input", "=m_inTok-m_cached", NUM, "m_fresh")
w("Accepted tasks", "=devs*tasksDay*workdays", NUM, "acceptedTasks")
w("Developer hours in the tool", "=devs*codeHrs*workdays", NUM, "codingHours")
w("Loaded engineer, per month", "=fteCost/12", MONEY, "fteMo")
w("Loaded engineer, per hour", "=fteCost/2080", MONEY, "engHr")
w("Metered-token discount factor", "=MAX(0,1-apiDiscount)", NUM2, "disc")
w("One session, output tok/s", "=IF(codeHrs>0,outTok*1000/(codeHrs*3600),0)", NUM1, "sessTps",
  "the rate one developer pulls while working")
w("Live sessions at once", "=devs*sessConc", NUM1, "liveSessions")
wk.blank()

# ── funnel ───────────────────────────────────────────────────────────────
wk.section("2. The failure funnel - first pass, repair passes, and what is never solved", span=10)
wk.cell(wk.r, 1, "Attempts are spent on the hopeless share too, which is exactly why retry budgets cost money. "
                 "A repair pass is worse than the first because the easy wins are gone.",
        f(8, color=MUTED, i=True))
wk.r += 1
fh = ["Pass", "Frontier pool in", "attempts", "solved", "pool out",
      "Open pool in", "attempts", "solved", "pool out"]
for i, h in enumerate(fh, start=1):
    wk.cell(wk.r, i, h, f(9, True, MUTED), border=UNDER, align="right" if i > 1 else "left")
wk.r += 1
FUNNEL_FIRST = wk.r
MAXPASS = 5
for k in range(MAXPASS + 1):
    r = wk.r
    wk.cell(r, 1, "First pass" if k == 0 else "Repair {}".format(k), f(9))
    for base, acc, rep, hard in ((2, "acceptFrontier", "repairFrontier", "hardFrontier"),
                                 (6, "acceptOpen", "repairOpen", "hardOpen")):
        cin, cat_, cgot, cout = (get_column_letter(base + i) for i in range(4))
        if k == 0:
            wk.cell(r, base, "=1", NUM2)
            wk.cell(r, base + 1, "=1", NUM2)
            wk.cell(r, base + 2, "={}{}*{}".format(cin, r, acc), NUM2)
            wk.cell(r, base + 3, "={0}{2}-{1}{2}".format(cin, cgot, r), NUM2)
        else:
            pr = r - 1
            live = "AND({}<={},{}{}>0.000000001)".format(k, "maxRetries", cout, pr)
            wk.cell(r, base, "={}{}".format(cout, pr), NUM2)
            wk.cell(r, base + 1, "=IF({},{}{},0)".format(live, cin, r), NUM2)
            wk.cell(r, base + 2, "=IF({},MAX(0,{}{}-{})*{},0)".format(live, cin, r, hard, rep), NUM2)
            wk.cell(r, base + 3, "={0}{2}-{1}{2}".format(cin, cgot, r), NUM2)
        for c in range(base, base + 4):
            wk.cell(r, c, None, f(9), fmt=NUM2, align="right")
            wk.ws.cell(row=r, column=c).font = f(9)
    wk.r += 1
FUNNEL_LAST = wk.r - 1
tot = wk.r
wk.cell(tot, 1, "Totals per unit of work started", f(9, True))
for base in (2, 6):
    at, got, out = (get_column_letter(base + i) for i in (1, 2, 3))
    wk.cell(tot, base + 1, "=SUM({0}{1}:{0}{2})".format(at, FUNNEL_FIRST, FUNNEL_LAST), f(9, True), fmt=NUM2, align="right")
    wk.cell(tot, base + 2, "=SUM({0}{1}:{0}{2})".format(got, FUNNEL_FIRST, FUNNEL_LAST), f(9, True), fmt=NUM2, align="right")
    wk.cell(tot, base + 3, "={}{}".format(out, FUNNEL_LAST), f(9, True), fmt=NUM2, align="right")
name("F_att", "Workings", "$C${}".format(tot))
name("F_acc", "Workings", "$D${}".format(tot))
name("F_unres", "Workings", "$E${}".format(tot))
name("O_att", "Workings", "$G${}".format(tot))
name("O_acc", "Workings", "$H${}".format(tot))
name("O_unres", "Workings", "$I${}".format(tot))
wk.r += 2

wk.section("3. Hybrid - the open model tries first, the frontier takes what is left", span=3)
w("Escalated to the frontier", "=O_unres", NUM2, "H_esc")
w("Accepted overall", "=O_acc+H_esc*F_acc", NUM2, "H_acc")
w("Still unresolved", "=H_esc*F_unres", NUM2, "H_unres")
w("Attempts on the open tier", "=O_att", NUM2, "H_openAtt")
w("Attempts on the frontier tier", "=H_esc*F_att", NUM2, "H_frontAtt")
wk.blank()
print("funnel rows", FUNNEL_FIRST, FUNNEL_LAST, "totals", tot)

wk.section("4. Effectiveness per strategy, against the frontier yardstick", span=10)
eh = ["Strategy", "Attempts / accepted task", "on open tier", "on frontier tier",
      "Unfinished / accepted", "Token volume vs frontier", "own share", "API share",
      "Developer min / task", "Developer time charged $/mo"]
for i, h in enumerate(eh, start=1):
    wk.cell(wk.r, i, h, f(9, True, MUTED), border=UNDER, wrap=True,
            align="right" if i > 1 else "left")
wk.r += 1
EFF_FIRST = wk.r
EFFROWS = [
    ("Frontier only", "=F_att/F_acc", "=0", "=F_att/F_acc", "=F_unres/F_acc"),
    ("Open model only", "=O_att/O_acc", "=O_att/O_acc", "=0", "=O_unres/O_acc"),
    ("Open first, frontier fallback", "=(H_openAtt+H_frontAtt)/H_acc",
     "=H_openAtt/H_acc", "=H_frontAtt/H_acc", "=H_unres/H_acc"),
]
for j, (lab, att, oa, fa, un) in enumerate(EFFROWS):
    r = wk.r
    wk.cell(r, 1, lab, f(9))
    for col, formula, fmt in ((2, att, NUM2), (3, oa, NUM2), (4, fa, NUM2), (5, un, PCT)):
        wk.cell(r, col, formula, f(9), fmt=fmt, align="right")
    yard = "$B${}".format(EFF_FIRST)
    wk.cell(r, 6, "=IF({0}>0,B{1}/{0},1)".format(yard, r), f(9), fmt=MULT, align="right")
    wk.cell(r, 7, "=IF({0}>0,C{1}/{0},0)".format(yard, r), f(9), fmt=MULT, align="right")
    wk.cell(r, 8, "=IF({0}>0,D{1}/{0},0)".format(yard, r), f(9), fmt=MULT, align="right")
    wk.cell(r, 9, '=B{0}*minPerAttempt+IF(countFallback="Yes",E{0}*minPerHumanTask,0)'.format(r),
            f(9), fmt=NUM1, align="right")
    wk.r += 1
EFF_LAST = wk.r - 1
base_r = wk.r
wk.cell(base_r, 1, "Fewest minutes of the three (the baseline)", f(9, True))
wk.cell(base_r, 9, "=MIN($I${}:$I${})".format(EFF_FIRST, EFF_LAST), f(9, True), fmt=NUM1, align="right")
name("baseMins", "Workings", "$I${}".format(base_r))
for j, tag in enumerate(("f", "o", "h")):
    name("mins_" + tag, "Workings", "$I${}".format(EFF_FIRST + j))
wk.r += 1
wk.cell(wk.r, 1, "Only the DIFFERENTIAL developer time is charged, against whichever strategy needs "
                 "the fewest minutes. Ordinary review labour exists on every route and is not this "
                 "model's to count.", f(8, color=MUTED, i=True))
wk.r += 1
for j in range(3):
    r = EFF_FIRST + j
    wk.cell(r, 10, "=devs*tasksDay*workdays*MAX(0,I{}-baseMins)/60*devRate".format(r),
            f(9), fmt=MONEY, align="right")

for j, tag in enumerate(("f", "o", "h")):
    r = EFF_FIRST + j
    name("att_" + tag, "Workings", "$B${}".format(r))
    name("unres_" + tag, "Workings", "$E${}".format(r))
    name("tm_" + tag, "Workings", "$F${}".format(r))
    name("own_" + tag, "Workings", "$G${}".format(r))
    name("api_" + tag, "Workings", "$H${}".format(r))
    name("drag_" + tag, "Workings", "$J${}".format(r))
wk.blank(2)

wk.section("5. Sizing the fleet the open model would need", span=3)
w("Total parameters", "=INDEX(tbl_models,MATCH(sel_model,cat_models,0),2)", NUM1, "m_total", "B")
w("Active parameters", "=INDEX(tbl_models,MATCH(sel_model,cat_models,0),3)", NUM1, "m_active", "B per token")
w("KV per k token", "=INDEX(tbl_models,MATCH(sel_model,cat_models,0),4)", NUM2, "m_kv", "MB")
w("Bytes per parameter", "=INDEX(tbl_quants,MATCH(sel_quant,cat_quants,0),2)", NUM2, "q_bytes")
w("KV factor", "=INDEX(tbl_quants,MATCH(sel_quant,cat_quants,0),3)", NUM2, "q_kv")
w("Weights in memory", "=m_total*q_bytes", NUM1, "weightsGb", "GB")
w("KV cache", "=batch*ctxK*1000*m_kv*q_kv/1024", NUM1, "kvGb", "GB")
w("Activation and fragmentation overhead", "=weightsGb*0.15", NUM1, "ovGb", "GB, 15%")
w("Memory per replica", "=weightsGb+kvGb+ovGb", NUM1, "vramNeed", "GB")
w("Cards the memory alone needs", "=MAX(1,CEILING(vramNeed/MAX(1,gpuVram),1))", NUM, "rawCards")
w("Cards per replica",
  "=IF(rawCards<=nodeSize,MIN(nodeSize,POWER(2,CEILING(LOG(rawCards,2)-0.0000001,1))),"
  "CEILING(rawCards/nodeSize,1)*nodeSize)", NUM, "gpusPerReplica",
  "inside a node, a power of two; past it, whole nodes")
w("Nodes per replica", "=CEILING(gpusPerReplica/nodeSize,1)", NUM, "nodesPerReplica")
w("Interconnect efficiency", "=IF(nodesPerReplica>1,MAX(0.05,1-multiNodeLoss),1)", NUM2, "linkEff")
w("Bytes read per token", "=m_active*q_bytes", NUM2, "bytesPerTok", "GB")
w("One stream", "=MIN(gpusPerReplica*MAX(1,gpuBw)*linkEff/bytesPerTok*bwEff,streamCap)", NUM, "perStream", "tok/s")
w("One replica", "=perStream*MIN(batch,32)", NUM, "replicaTps", "tok/s")
w("Peak demand, open model", "=IF(AND(workdays>0,activeHrs>0),m_outTok*tm_o/workdays/(activeHrs*3600)*peak,0)",
  NUM, "peakTps", "tok/s in the busy hour")
w("Replicas needed", "=IF(devs=0,0,IF(replicaTps>0,MAX(1,CEILING(peakTps/replicaTps,1)),1))", NUM, "replicas")
w("Cards in the fleet", "=replicas*gpusPerReplica", NUM, "gpus")
w("Sustained fleet throughput", "=replicas*replicaTps", NUM, "fleetTps", "tok/s")
w("Time to first token",
  "=IF(gpusPerReplica*gpuTf*linkEff*bwEff>0,2*m_active*ctxK*1000/(gpusPerReplica*gpuTf*1000*linkEff*bwEff),0)",
  NUM2, "ttft", "s, cold prefill with nothing cached")
w("Checkpoint storage", "=(m_total*2+m_total*q_bytes)*MAX(1,ckpts)", NUM, "storageGb", "GB")
w("Fits a laptop", '=IF(weightsGb+ovGb+4<=lapRam,"Yes","No")', None, "fitsLaptop")
w("One laptop", "=lapBw/MAX(0.001,bytesPerTok)*bwEff", NUM, "lapTps", "tok/s")
wk.blank()

wk.section("6. The hybrid's own fleet - it serves the open tier only", span=3)
w("Peak demand, open tier only",
  "=IF(AND(workdays>0,activeHrs>0),m_outTok*own_h/workdays/(activeHrs*3600)*peak,0)", NUM, "peakTpsH", "tok/s")
w("Replicas needed", "=IF(devs=0,0,IF(replicaTps>0,MAX(1,CEILING(peakTpsH/replicaTps,1)),1))", NUM, "replicasH")
w("Cards in the hybrid fleet", "=replicasH*gpusPerReplica", NUM, "gpusH")
w("Hosts", "=CEILING(gpusH/8,1)", NUM, "hostsH")
w("Sustained hybrid fleet throughput", "=replicasH*replicaTps", NUM, "fleetTpsH", "tok/s")
wk.blank()
print("workings through sizing, row", wk.r)

wk.section("7. What the iron and the people cost", span=3)
w("Hosts", "=CEILING(gpus/8,1)", NUM, "hosts", "eight cards to a host")
w("Cards", "=gpus*gpuBuy", MONEY, "cardsCost")
w("Spare cards held", "=cardsCost*spares", MONEY, "sparesCost")
w("Hosts, NICs and fabric", "=hosts*hostCost", MONEY, "chassisCost")
w("Fabric, optics and cabling", "=hosts*netFabric", MONEY, "fabricCost")
w("Rack, PDU and smart hands", "=hosts*installHost", MONEY, "installCost")
w("Hardware capital", "=cardsCost+sparesCost+chassisCost+fabricCost+installCost", MONEY, "hwCapex")
w("Setup hours", "=setupArch+hosts*setupRack+setupStack+setupEval+setupSec", NUM, "setupHours")
w("Setup labour", '=IF(labourYN="Yes",setupHours*engHr,0)', MONEY, "setupLabour",
  "one-off, and it does NOT scale down with the team")
w("Day-one cheque if you buy", "=hwCapex+setupLabour", MONEY, "buyUpfront")
w("Hardware support", "=hwCapex*warranty/12", MONEY, "warrantyMo", "per month")
w("Bring-up if you rent instead", '=IF(labourYN="Yes",(setupStack+setupEval+setupSec+setupArch/2)*engHr,0)',
  MONEY, "rentSetup", "no rack, but still a serving stack, an evaluation and a security review")
w("Staffing ramp",
  "=IF(platformAt>soloAt,MIN(1,MAX(0,(devs-soloAt)/(platformAt-soloAt))),IF(devs>soloAt,1,0))",
  NUM2, "teamRamp",
  "nobody is employed to run this below the small-team threshold; full strength at platformAt")
w("Baseline AI platform team", '=IF(AND(labourYN="Yes",ownsPlatform="No"),platformFte*fteMo*teamRamp,0)',
  MONEY, "platformMo", "every centralised route pays this")
w("Fleet admin", '=IF(labourYN="Yes",adminFte*fteMo*teamRamp,0)', MONEY, "adminMo")
w("Cloud plumbing", '=IF(labourYN="Yes",cloudOps*fteMo*teamRamp,0)', MONEY, "cloudOpsMo")
w("Fleet draw", "=gpus*gpuW/1000*1.25", NUM1, "fleetKw", "kW, +25% for host, NIC and fans")
w("Storage", "=storageGb*storGb", MONEY, "storMo", "per month")
wk.blank()

wk.section("8. The hybrid: buy its fleet, or rent it?", span=3)
w("Hybrid fleet draw", "=gpusH*gpuW/1000*1.25", NUM1, "hKw", "kW")
w("Hybrid hardware capital", "=gpusH*gpuBuy*(1+spares)+hostsH*(hostCost+netFabric+installHost)",
  MONEY, "hHwCapex", "its OWN fleet, not the standalone one")
w("Written down per month", "=hHwCapex/amort", MONEY, "hybridFleetCapex")
w("Power, rack, storage and support",
  "=hKw*pue*730*kwhDc+hKw*coloKw+storMo+hHwCapex*warranty/12", MONEY, "hybridFleetPower")
w("Rent the same fleet instead", "=gpusH*gpuRent*730*rentUtil", MONEY, "hybridRentMo")
w("Hybrid setup hours", "=setupArch+hostsH*setupRack+setupStack+setupEval+setupSec",
  NUM, "hSetupHours", "racked against the hybrid's own hosts, not the standalone fleet's")
w("Hybrid setup labour", '=IF(labourYN="Yes",hSetupHours*engHr,0)', MONEY, "hSetupLabour")
w("Total if bought", "=hybridFleetCapex+hybridFleetPower+hSetupLabour/amort", MONEY, "hybridBuyTotal")
w("Total if rented", "=hybridRentMo+storMo+rentSetup/amort", MONEY, "hybridRentTotal")
w("Cheaper to buy it?", '=IF(hybridBuyTotal<=hybridRentTotal,"Yes","No")', None, "hybridBuy")
wk.blank()

# ── token-bill helper, written inline per route ──────────────────────────
def toks(i, o, c, mult):
    return ("(m_fresh*{m}/1000000*{i}+m_cached*{m}/1000000*{c}+m_outTok*{m}/1000000*{o})*disc"
            .format(m=mult, i=i, o=o, c=c))


# id: capex, power, people, usage, drag, upfront, capTps, ownMult, perDevUnitTps(or None)
RDEF = {
    "laptop": dict(
        capex="devs*lapUplift/amort",
        power="devs*lapWatts/1000*codeHrs*workdays*kwhOffice",
        people='IF(labourYN="Yes",devs*lapSupport/12*itRate,0)',
        usage="0", drag="drag_o", upfront="devs*lapUplift",
        capTps="devs*lapTps", own="tm_o", unit="lapTps", unres="unres_o"),
    "buy": dict(
        capex="hwCapex/amort",
        power="fleetKw*pue*730*kwhDc+fleetKw*coloKw+storMo+warrantyMo",
        people="platformMo+adminMo+setupLabour/amort",
        usage="0", drag="drag_o", upfront="buyUpfront",
        capTps="fleetTps", own="tm_o", unit=None, unres="unres_o"),
    "rent": dict(
        capex="0", power="storMo",
        people="platformMo+adminMo+rentSetup/amort",
        usage="gpus*gpuRent*730*rentUtil", drag="drag_o", upfront="rentSetup",
        capTps="fleetTps", own="tm_o", unit=None, unres="unres_o"),
    "serverless": dict(
        capex="0", power="0", people="platformMo",
        usage=toks("orIn", "orOut", "orCache", "tm_o") + "*(1+orFee)",
        drag="drag_o", upfront="0", capTps="orTpm*1000/60", own="tm_o", unit=None, unres="unres_o"),
    "bedrock": dict(
        capex="0", power="0", people="platformMo+cloudOpsMo",
        usage=toks("bedIn", "bedOut", "bedCache", "1"),
        drag="drag_f", upfront="0", capTps="bedTpm*1000/60", own="tm_f", unit=None, unres="unres_f"),
    "azure": dict(
        capex="0", power="0", people="platformMo+cloudOpsMo",
        usage=toks("azIn", "azOut", "azCache", "1"),
        drag="drag_f", upfront="0", capTps="azTpm*1000/60", own="tm_f", unit=None, unres="unres_f"),
    "anthropic": dict(
        capex="0", power="0", people="platformMo",
        usage=toks("anIn", "anOut", "anCache", "1"),
        drag="drag_f", upfront="0", capTps="anTpm*1000/60", own="tm_f", unit=None, unres="unres_f"),
    "openai": dict(
        capex="0", power="0", people="platformMo",
        usage=toks("oaIn", "oaOut", "oaCache", "1"),
        drag="drag_f", upfront="0", capTps="oaTpm*1000/60", own="tm_f", unit=None, unres="unres_f"),
    "hybrid": dict(
        capex='IF(hybridBuy="Yes",hybridFleetCapex,0)',
        power='IF(hybridBuy="Yes",hybridFleetPower,storMo)',
        people='platformMo+adminMo+IF(hybridBuy="Yes",hSetupLabour,rentSetup)/amort',
        usage='IF(hybridBuy="Yes",0,hybridRentMo)+' + toks("anIn", "anOut", "anCache", "api_h"),
        drag="drag_h", upfront='IF(hybridBuy="Yes",hHwCapex+hSetupLabour,rentSetup)',
        capTps="fleetTpsH", own="own_h", unit=None, unres="unres_h"),
    "seats": dict(
        capex="0", power="0", people="platformMo",
        usage='devs*(seat+IF(ownsBase="Yes",0,seatBase))',
        drag="drag_f", upfront="0", capTps="devs*seatTpm/60", own="tm_f",
        unit="seatTpm/60", unres="unres_f"),
}
print("route definitions ready:", len(RDEF))

# ═══ 3b. the route table ═════════════════════════════════════════════════
wk.blank()
wk.section("9. The routes - one row each, every column a formula", span=22)
RCOLS = [
    ("Route", 30), ("Group", 22), ("Hardware", 12), ("Power & rack", 12), ("People", 12),
    ("Tokens, seats, rent", 14), ("Developer time", 13), ("Monthly total", 13),
    ("Up front", 12), ("Monthly cash", 13), ("Full term", 14), ("Cash, full term", 14),
    ("Year-one cash", 13), ("Per dev / mo", 12), ("AI $ / task", 11), ("Unfinished", 11),
    ("Sustained tok/s", 13), ("Token mult", 11), ("Session tok/s", 12),
    ("Live sessions", 12), ("Developers held", 13), ("Headroom", 11), ("Rank", 8),
]
for i, (h, wdt) in enumerate(RCOLS, start=1):
    wk.cell(wk.r, i, h, f(9, True, MUTED), border=UNDER, wrap=True,
            align="left" if i <= 2 else "right")
    if i > 10:
        wk.ws.column_dimensions[get_column_letter(i)].width = wdt
wk.r += 1
ROUTE_FIRST = wk.r
for rid, rname, rgroup in ROUTES:
    d = RDEF[rid]
    r = wk.r
    wk.cell(r, 1, rname, f(9))
    wk.cell(r, 2, rgroup, f(9, color=MUTED))
    for col, key in ((3, "capex"), (4, "power"), (5, "people"), (6, "usage"), (7, "drag")):
        wk.cell(r, col, "=" + d[key], f(9), fmt=MONEY, align="right")
    wk.cell(r, 8, "=SUM(C{0}:G{0})".format(r), f(9, True), fmt=MONEY, align="right")
    wk.cell(r, 9, "=" + d["upfront"], f(9), fmt=MONEY, align="right")
    wk.cell(r, 10, "=D{0}+E{0}+F{0}+G{0}".format(r), f(9), fmt=MONEY, align="right")
    wk.cell(r, 11, "=H{}*horizon".format(r), f(9), fmt=MONEY, align="right")
    wk.cell(r, 12, "=I{0}+J{0}*horizon".format(r), f(9), fmt=MONEY, align="right")
    wk.cell(r, 13, "=I{0}+J{0}*MIN(12,horizon)".format(r), f(9), fmt=MONEY, align="right")
    wk.cell(r, 14, "=IF(devs>0,H{}/devs,0)".format(r), f(9), fmt=MONEY, align="right")
    wk.cell(r, 15, "=IF(acceptedTasks>0,H{}/acceptedTasks,0)".format(r), f(9), fmt=MONEY2, align="right")
    wk.cell(r, 16, "=" + d["unres"], f(9), fmt=PCT, align="right")
    wk.cell(r, 17, "=" + d["capTps"], f(9), fmt=NUM, align="right")
    wk.cell(r, 18, "=IF({0}>0,{0},1)".format(d["own"]), f(9), fmt=MULT, align="right")
    wk.cell(r, 19, "=sessTps*R{}".format(r), f(9), fmt=NUM1, align="right")
    if d["unit"]:
        # one laptop, or one seat, per developer: capacity grows with the team, so the
        # real question is whether a single unit keeps up with a single session
        wk.cell(r, 20, "=devs", f(9), fmt=NUM, align="right")
        wk.cell(r, 21, '="scales 1:1"', f(9, color=MUTED), align="right")
        wk.cell(r, 22, "=IF(S{0}>0,({1})/S{0},0)".format(r, d["unit"]), f(9), fmt=MULT, align="right")
    else:
        wk.cell(r, 20, "=IF(S{0}>0,Q{0}/S{0},0)".format(r), f(9), fmt=NUM, align="right")
        wk.cell(r, 21, "=IF(sessConc>0,T{}/sessConc,0)".format(r), f(9), fmt=NUM, align="right")
        wk.cell(r, 22, "=IF(liveSessions*S{0}>0,Q{0}/(liveSessions*S{0}),0)".format(r), f(9),
                fmt=MULT, align="right")
    wk.r += 1
ROUTE_LAST = wk.r - 1
# rank cheapest first; COUNTIF breaks ties so two equal routes do not share a rank
for r in range(ROUTE_FIRST, ROUTE_LAST + 1):
    wk.cell(r, 23, "=RANK(H{0},$H${1}:$H${2},1)+COUNTIF($H${1}:H{0},H{0})-1"
            .format(r, ROUTE_FIRST, ROUTE_LAST), f(9), fmt=NUM, align="right")

for i, (rid, _, _) in enumerate(ROUTES):
    wk.cell(ROUTE_FIRST + i, 24, rid, f(9, color=MUTED))
wk.cell(ROUTE_FIRST - 1, 24, "id", f(9, True, MUTED), border=UNDER)
name("r_id", "Workings", "$X${}:$X${}".format(ROUTE_FIRST, ROUTE_LAST))
name("r_name", "Workings", "$A${}:$A${}".format(ROUTE_FIRST, ROUTE_LAST))
name("r_rank", "Workings", "$W${}:$W${}".format(ROUTE_FIRST, ROUTE_LAST))
name("r_all", "Workings", "$A${}:$W${}".format(ROUTE_FIRST, ROUTE_LAST))
name("r_total", "Workings", "$H${}:$H${}".format(ROUTE_FIRST, ROUTE_LAST))
wk.blank()

wk.section("10. The quality question", span=4)
wk.cell(wk.r, 1, "Self-hosting is cheaper on paper by some margin. How much developer time does "
                 "that margin actually buy? Under a percent and the quality gap settles the "
                 "argument before the spreadsheet does.", f(8, color=MUTED, i=True))
wk.r += 1
own_rows = [ROUTE_FIRST + i for i, (rid, _, _) in enumerate(ROUTES) if rid in ("laptop", "buy", "rent")]
host_rows = [ROUTE_FIRST + i for i, (rid, _, _) in enumerate(ROUTES) if rid not in ("laptop", "buy", "rent")]
w("Cheapest hosted route", "=MIN({})".format(",".join("H{}".format(r) for r in host_rows)),
  MONEY, "cheapestHosted")
w("Cheapest self-hosted, before the quality gap",
  "=MIN({})".format(",".join("H{0}-G{0}".format(r) for r in own_rows)), MONEY, "cheapestOwn")
w("Monthly spend on coding time", "=codingHours*devRate", MONEY, "codingSpend")
w("Quality budget", "=cheapestHosted-cheapestOwn", MONEY, "qualityBudget",
  "what the self-hosted saving is worth")
w("As a share of coding time", "=IF(codingSpend>0,qualityBudget/codingSpend,0)", PCT, "qualityPct")
w("What the acceptance gap actually costs",
  "=IF(codingHours>0,devs*tasksDay*workdays*MAX(0,I{}-baseMins)/60/codingHours,0)"
  .format(EFF_FIRST + 1), PCT, "dragPct")
wk.blank()

wk.section("11. The cheapest flat plan that keeps up with one session", span=5)
ph = ["Flat plan", "$/dev/mo", "Sustained tok/s", "Headroom vs one session", "Keeps up?"]
for i, h in enumerate(ph, start=1):
    wk.cell(wk.r, i, h, f(9, True, MUTED), border=UNDER, align="right" if i > 1 else "left")
wk.r += 1
PLAN_FIRST = wk.r
pa, pb = SPANS["plans"]
for j in range(len(PLANS)):
    r = wk.r
    cr = pa + j
    wk.cell(r, 1, "=Catalogues!$A${}".format(cr), f(9))
    wk.cell(r, 2, '=Catalogues!$B${0}+IF(ownsBase="Yes",0,Catalogues!$C${0})'.format(cr),
            f(9), fmt=MONEY, align="right")
    wk.cell(r, 3, "=Catalogues!$D${}/60".format(cr), f(9), fmt=NUM1, align="right")
    wk.cell(r, 4, "=IF(sessTps>0,C{}/sessTps,0)".format(r), f(9), fmt=MULT, align="right")
    wk.cell(r, 5, '=IF(D{}>=1,B{},"")'.format(r, r), f(9), fmt=MONEY, align="right")
    wk.r += 1
PLAN_LAST = wk.r - 1
w("Cheapest plan that keeps up", "=IFERROR(MIN($E${}:$E${}),0)".format(PLAN_FIRST, PLAN_LAST),
  MONEY, "planFitCost")
w("Its name", '=IFERROR(INDEX($A${0}:$A${1},MATCH(planFitCost,$E${0}:$E${1},0)),"none in the list")'
  .format(PLAN_FIRST, PLAN_LAST), None, "planFitName")
w("For the whole team", "=planFitCost*devs", MONEY, "planFitTeam")
wk.blank()
print("routes", ROUTE_FIRST, ROUTE_LAST, "| workings end", wk.r, "| names", len(NAMES))


# ═══ 4. Answer ═══════════════════════════════════════════════════════════
ans = Sheet(wb, "Answer", [4, 30, 16, 14, 15, 14, 13, 12, 12, 13])
ans.title_row("The answer",
              "Everything here is a formula over Inputs. Change a blue cell there and this page moves.")

BEST = 'INDEX(r_name,MATCH(1,r_rank,0))'
BESTID = 'INDEX(r_id,MATCH(1,r_rank,0))'
WORSTID = 'MATCH({},r_rank,0)'.format(len(ROUTES))


def r_at(rank, col):
    """Column `col` of the route sitting at this rank."""
    return "INDEX(Workings!${0}${1}:${0}${2},MATCH({3},r_rank,0))".format(
        col, ROUTE_FIRST, ROUTE_LAST, rank)


ans.cell(ans.r, 2, "THE RECOMMENDATION", f(9, True, MUTED))
ans.r += 1
head = ('=IF(AND(devs>0,devs<=soloAt),IF(devs=1,"You are one developer. Buy a plan.",'
        '"A team this small should buy plans."),'
        'IF({0}="serverless","Rent the open weights. Do not run them.",'
        'IF({0}="hybrid","Run the cheap model first. Escalate what it cannot finish.",'
        'IF(OR({0}="laptop",{0}="buy",{0}="rent"),"Run it on your own hardware.",'
        '"Rent the model. Do not buy the hardware."))))').format(BESTID)
c = ans.cell(ans.r, 2, head, f(20, True, HEAD_BG), wrap=True)
ans.ws.merge_cells(start_row=ans.r, start_column=2, end_row=ans.r + 1, end_column=10)
ans.ws.row_dimensions[ans.r].height = 30
ans.ws.row_dimensions[ans.r + 1].height = 30
ans.r += 2

sub = ('=IF(AND(devs>0,devs<=soloAt),'
       '"The cheapest flat plan that keeps up with a live session is "&planFitName&" at "'
       '&TEXT(planFitCost,"$#,##0")&" a developer a month, "&TEXT(planFitTeam,"$#,##0")&" for "'
       '&TEXT(devs,"#,##0")&". If your use is bursty a metered key is cheaper still: the open '
       'weights on a serverless provider come to "&TEXT({sv},"$#,##0")&" a month at this volume. '
       'Nothing here needs a platform team, a rack or a purchase order.",'
       'IF({bid}="serverless",'
       '"Someone else already owns a warm fleet of these weights and sells them by the token. At '
       'this size that beats both your own accelerators and the frontier rate card, and it carries '
       'no capital, no rota and no lead time.",'
       'IF({bid}="hybrid",'
       '"Two independent attempts finish more work than either approach alone: only "'
       '&TEXT(unres_h,"0%")&" of accepted tasks still need a person, against "&TEXT(unres_f,"0%")'
       '&" on the frontier model by itself.",'
       'IF(OR({bid}="laptop",{bid}="buy",{bid}="rent"),'
       '"At this size the fleet is cheaper than metered tokens even after the extra attempts '
       'the weaker model needs are counted. That advantage is narrow and it depends on quality '
       'holding up.",'
       '"At this team size, owning accelerators costs more than renting tokens, before the '
       'weaker output of the open model is even counted."))))').format(
    bid=BESTID, sv="Workings!$H${}".format(ROUTE_FIRST + 3))
ans.cell(ans.r, 2, sub, f(10, color=INK), wrap=True)
ans.ws.merge_cells(start_row=ans.r, start_column=2, end_row=ans.r + 2, end_column=10)
for k in range(3):
    ans.ws.row_dimensions[ans.r + k].height = 15
ans.r += 4

# ── KPI strip ────────────────────────────────────────────────────────────
KPIS = [
    ("Cheapest route", "=" + BEST, '="at "&TEXT({},"$#,##0")&" a month"'.format(r_at(1, "H")), None),
    ("Bill over the horizon", "=" + r_at(1, "K"),
     '="for "&TEXT(devs,"#,##0")&" developer"&IF(devs=1,"","s")', MONEY),
    ("Priciest route", "=" + "INDEX(r_name,MATCH({},r_rank,0))".format(len(ROUTES)),
     '="at "&TEXT({},"$#,##0")&" a month"'.format(r_at(len(ROUTES), "H")), None),
    ("Spread, full term", "=({}-{})*horizon".format(r_at(len(ROUTES), "H"), r_at(1, "H")),
     '="saved by picking first over last"', MONEY),
    ("Quality budget", "=qualityPct",
     '="developer time the self-hosted saving buys; your acceptance gap costs "&TEXT(dragPct,"0.0%")',
     PCT),
]
for i, (lab, val, note, fmt) in enumerate(KPIS):
    col = 2 + i * 2
    ans.cell(ans.r, col, lab, f(8, True, MUTED))
    ans.cell(ans.r + 1, col, val, f(13, True, ACCENT), fmt=fmt, wrap=True)
    ans.cell(ans.r + 2, col, note, f(8, color=MUTED), wrap=True)
    for k in range(3):
        ans.ws.cell(row=ans.r + k, column=col).border = Border(left=Side(style="thick", color=ACCENT))
ans.ws.row_dimensions[ans.r + 1].height = 20
ans.ws.row_dimensions[ans.r + 2].height = 24
ans.r += 4

# ── ranked table ─────────────────────────────────────────────────────────
ans.section("Every route, cheapest first", span=10)
AH = [("#", "W"), ("Route", "A"), ("Monthly", "H"), ("Up front", "I"), ("Full term", "K"),
      ("Per dev / mo", "N"), ("AI $ / task", "O"), ("Unfinished", "P"),
      ("Sustained tok/s", "Q"), ("Headroom", "V")]
for i, (h, _) in enumerate(AH, start=1):
    ans.cell(ans.r, i, h, f(9, True, MUTED), border=UNDER,
             align="left" if i == 2 else "right", wrap=True)
ans.r += 1
ARANK_FIRST = ans.r
for rank in range(1, len(ROUTES) + 1):
    r = ans.r
    fill = "E8F0FB" if rank == 1 else (BAND if rank % 2 == 0 else None)
    ans.cell(r, 1, rank, f(9, color=MUTED), align="center", fill=fill)
    for i, (h, col) in enumerate(AH[1:], start=2):
        fmt = {"Monthly": MONEY, "Up front": MONEY, "Full term": MONEY, "Per dev / mo": MONEY,
               "AI $ / task": MONEY2, "Unfinished": PCT, "Sustained tok/s": NUM,
               "Headroom": MULT}.get(h)
        ans.cell(r, i, "=" + r_at(rank, col), f(9, rank == 1), fmt=fmt,
                 align="left" if i == 2 else "right", fill=fill)
    ans.r += 1
ARANK_LAST = ans.r - 1
ans.ws.conditional_formatting.add(
    "C{}:C{}".format(ARANK_FIRST, ARANK_LAST),
    DataBarRule(start_type="num", start_value=0, end_type="max", color=ACCENT, showValue=True))
ans.ws.conditional_formatting.add(
    "J{}:J{}".format(ARANK_FIRST, ARANK_LAST),
    CellIsRule(operator="lessThan", formula=["1"], font=Font(name=FONT, size=9, bold=True, color=BAD)))
ans.ws.conditional_formatting.add(
    "J{}:J{}".format(ARANK_FIRST, ARANK_LAST),
    CellIsRule(operator="greaterThanOrEqual", formula=["1.5"],
               font=Font(name=FONT, size=9, color=GOOD)))
ans.cell(ans.r, 2, "Headroom below 1.0x means the route throttles and your developers queue. "
                   "Laptops and per-seat plans scale one unit per developer, so their headroom is "
                   "one unit against one session, not a shared pool.", f(8, color=MUTED, i=True))
ans.r += 2

# ── what would change this answer ────────────────────────────────────────
ans.section("What would change this answer", span=10)
QROWS = [
    ('="We judge the open model purely on infrastructure, quality set aside"',
     '=IF(be_devs>0,"Owning accelerators wins above "&TEXT(be_devs,"#,##0")'
     '&" developers","Owning still never wins")'),
    ('="We count the work the agent cannot finish at all"',
     '=IF(countFallback="Yes","Already counted - it is in the numbers above",'
     '"Turn it on in Inputs; it usually moves the ranking")'),
    ('="Code may not leave our own network"', '="Cost stops being the question"'),
    ('="We just want one price per developer, with no surprises"',
     '=planFitName&" at "&TEXT(planFitTeam,"$#,##0")&" a month"'),
    ('="We need every developer served at once, without queueing"',
     '=IF({0}<1,"The cheapest route throttles at "&TEXT({0},"0.0")&"x","The cheapest route keeps up")'
     .format(r_at(1, "V"))),
]
for q, a in QROWS:
    ans.cell(ans.r, 2, q, f(10), wrap=True)
    ans.ws.merge_cells(start_row=ans.r, start_column=2, end_row=ans.r, end_column=5)
    ans.cell(ans.r, 6, a, f(10, True, ACCENT), wrap=True)
    ans.ws.merge_cells(start_row=ans.r, start_column=6, end_row=ans.r, end_column=10)
    ans.ws.row_dimensions[ans.r].height = 16
    ans.r += 1
ans.r += 1

# ── chart data, rank ordered ─────────────────────────────────────────────
CHART_TOP = ans.r
ans.cell(ans.r, 2, "Chart data - monthly cost by where it goes", f(9, True, MUTED))
ans.r += 1
COMPS = [("Hardware, written down", "C"), ("Power, rack and storage", "D"),
         ("People to run it", "E"), ("Tokens, seats and rent", "F"),
         ("Developer time lost", "G")]
ans.cell(ans.r, 2, "Route", f(9, True, MUTED), border=UNDER)
for i, (lab, _) in enumerate(COMPS):
    ans.cell(ans.r, 3 + i, lab, f(9, True, MUTED), border=UNDER, wrap=True, align="right")
ans.r += 1
CDATA_FIRST = ans.r
for rank in range(1, len(ROUTES) + 1):
    ans.cell(ans.r, 2, "=" + r_at(rank, "A"), f(9))
    for i, (_, col) in enumerate(COMPS):
        ans.cell(ans.r, 3 + i, "=" + r_at(rank, col), f(9), fmt=MONEY, align="right")
    ans.r += 1
CDATA_LAST = ans.r - 1

chart = BarChart()
chart.type = "bar"
chart.grouping = "stacked"
chart.overlap = 100
chart.title = "Monthly cost by where it goes"
chart.y_axis.title = "$ per month"
chart.height = 11
chart.width = 26
data = Reference(ans.ws, min_col=3, max_col=7, min_row=CDATA_FIRST - 1, max_row=CDATA_LAST)
cats = Reference(ans.ws, min_col=2, min_row=CDATA_FIRST, max_row=CDATA_LAST)
chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)
ans.ws.add_chart(chart, "B{}".format(CHART_TOP + 2 + len(ROUTES) + 2))
ans.r += 24
ans.ws.freeze_panes = "A4"


# ═══ 5. Models ═══════════════════════════════════════════════════════════
mdl = Sheet(wb, "Models", [30, 14, 11, 11, 15, 13, 11, 11, 11, 11, 11, 11, 13, 13, 13, 14, 11])
mdl.title_row("Which model, at your workload",
              "The same month of work, priced on every candidate. Rate cards are list prices from "
              "Catalogues; the self-hosted block replays the whole fleet calculation once per set "
              "of weights, because changing the model changes the iron under it.")

mdl.section("Pay per token", span=7)
mh = ["Model", "Lab", "In $/M", "Out $/M", "Your bill / mo", "AI $ / task", "vs cheapest"]
for i, h in enumerate(mh, start=1):
    mdl.cell(mdl.r, i, h, f(9, True, MUTED), border=UNDER, align="left" if i <= 2 else "right", wrap=True)
mdl.r += 1
API_FIRST = mdl.r
fa, fbb = SPANS["frontier"]
for j in range(len(FRONTIER)):
    r, cr = mdl.r, fa + j
    mdl.cell(r, 1, "=Catalogues!$A${}".format(cr), f(9))
    mdl.cell(r, 2, "=Catalogues!$B${}".format(cr), f(9, color=MUTED))
    mdl.cell(r, 3, "=Catalogues!$C${}".format(cr), f(9), fmt=MONEY2, align="right")
    mdl.cell(r, 4, "=Catalogues!$D${}".format(cr), f(9), fmt=MONEY2, align="right")
    mdl.cell(r, 5, "=(m_fresh/1000000*C{0}+m_cached/1000000*Catalogues!$E${1}"
                   "+m_outTok/1000000*D{0})*disc".format(r, cr), f(9), fmt=MONEY, align="right")
    mdl.r += 1
r = mdl.r
mdl.cell(r, 1, "Open weights, serverless", f(9))
mdl.cell(r, 2, "aggregator or provider", f(9, color=MUTED))
mdl.cell(r, 3, "=orIn", f(9), fmt=MONEY2, align="right")
mdl.cell(r, 4, "=orOut", f(9), fmt=MONEY2, align="right")
mdl.cell(r, 5, "=(m_fresh*tm_o/1000000*orIn+m_cached*tm_o/1000000*orCache"
               "+m_outTok*tm_o/1000000*orOut)*disc*(1+orFee)", f(9), fmt=MONEY, align="right")
mdl.r += 1
API_LAST = mdl.r - 1
for r in range(API_FIRST, API_LAST + 1):
    mdl.cell(r, 6, "=IF(acceptedTasks>0,E{}/acceptedTasks,0)".format(r), f(9), fmt=MONEY2, align="right")
    mdl.cell(r, 7, "=IF(MIN($E${0}:$E${1})>0,E{2}/MIN($E${0}:$E${1}),0)"
             .format(API_FIRST, API_LAST, r), f(9), fmt=MULT, align="right")
mdl.ws.conditional_formatting.add(
    "E{}:E{}".format(API_FIRST, API_LAST),
    DataBarRule(start_type="num", start_value=0, end_type="max", color=ACCENT, showValue=True))
mdl.cell(mdl.r, 1, "The serverless row carries the open model's extra attempts, because a weaker "
                   "model needs more of them for the same accepted work. The frontier rows are the "
                   "yardstick at 1.00x.", f(8, color=MUTED, i=True))
mdl.r += 2

mdl.section("Host it yourself - the whole fleet calculation, once per model", span=17)
oh = ["Open-weight model", "Weights GB", "KV GB", "Memory / replica", "Cards / replica",
      "Replicas", "Cards", "Hosts", "One replica tok/s", "Hardware capital",
      "Written down", "Power & rack", "People", "Developer time", "Own it / mo",
      "vs cheapest", "Fits a laptop"]
for i, h in enumerate(oh, start=1):
    mdl.cell(mdl.r, i, h, f(9, True, MUTED), border=UNDER, align="left" if i == 1 else "right", wrap=True)
mdl.r += 1
OWN_FIRST = mdl.r
ma, mbb = SPANS["models"]
for j in range(len(MODELS)):
    r, cr = mdl.r, ma + j
    T = "Catalogues!$B${}".format(cr)
    A = "Catalogues!$C${}".format(cr)
    KV = "Catalogues!$D${}".format(cr)
    mdl.cell(r, 1, "=Catalogues!$A${}".format(cr), f(9))
    mdl.cell(r, 2, "={}*q_bytes".format(T), f(9), fmt=NUM, align="right")
    mdl.cell(r, 3, "=batch*ctxK*1000*{}*q_kv/1024".format(KV), f(9), fmt=NUM, align="right")
    mdl.cell(r, 4, "=B{0}*1.15+C{0}".format(r), f(9), fmt=NUM, align="right")
    mdl.cell(r, 5, "=IF(MAX(1,CEILING(D{0}/MAX(1,gpuVram),1))<=nodeSize,"
                   "MIN(nodeSize,POWER(2,CEILING(LOG(MAX(1,CEILING(D{0}/MAX(1,gpuVram),1)),2)-0.0000001,1))),"
                   "CEILING(MAX(1,CEILING(D{0}/MAX(1,gpuVram),1))/nodeSize,1)*nodeSize)".format(r),
             f(9), fmt=NUM, align="right")
    # one replica's throughput, with the multi-node haircut when it spans nodes
    mdl.cell(r, 9, "=MIN(E{0}*MAX(1,gpuBw)*IF(CEILING(E{0}/nodeSize,1)>1,MAX(0.05,1-multiNodeLoss),1)"
                   "/({1}*q_bytes)*bwEff,streamCap)*MIN(batch,32)".format(r, A),
             f(9), fmt=NUM, align="right")
    mdl.cell(r, 6, "=IF(devs=0,0,IF(I{0}>0,MAX(1,CEILING(peakTps/I{0},1)),1))".format(r),
             f(9), fmt=NUM, align="right")
    mdl.cell(r, 7, "=F{0}*E{0}".format(r), f(9), fmt=NUM, align="right")
    mdl.cell(r, 8, "=CEILING(G{}/8,1)".format(r), f(9), fmt=NUM, align="right")
    mdl.cell(r, 10, "=G{0}*gpuBuy*(1+spares)+H{0}*(hostCost+netFabric+installHost)".format(r),
             f(9), fmt=MONEY, align="right")
    mdl.cell(r, 11, "=J{}/amort".format(r), f(9), fmt=MONEY, align="right")
    mdl.cell(r, 12, "=G{0}*gpuW/1000*1.25*(pue*730*kwhDc+coloKw)"
                    "+({1}*2+{1}*q_bytes)*MAX(1,ckpts)*storGb+J{0}*warranty/12".format(r, T),
             f(9), fmt=MONEY, align="right")
    mdl.cell(r, 13, '=platformMo+adminMo+IF(labourYN="Yes",(setupArch+H{}*setupRack+setupStack'
                    "+setupEval+setupSec)*engHr,0)/amort".format(r), f(9), fmt=MONEY, align="right")
    mdl.cell(r, 14, "=drag_o", f(9), fmt=MONEY, align="right")
    mdl.cell(r, 15, "=K{0}+L{0}+M{0}+N{0}".format(r), f(9, True), fmt=MONEY, align="right")
    mdl.cell(r, 17, '=IF(B{0}*1.15+4<=lapRam,"Yes","No")'.format(r), f(9), align="right")
    mdl.r += 1
OWN_LAST = mdl.r - 1
for r in range(OWN_FIRST, OWN_LAST + 1):
    mdl.cell(r, 16, "=IF(MIN($O${0}:$O${1})>0,O{2}/MIN($O${0}:$O${1}),0)"
             .format(OWN_FIRST, OWN_LAST, r), f(9), fmt=MULT, align="right")
mdl.ws.conditional_formatting.add(
    "O{}:O{}".format(OWN_FIRST, OWN_LAST),
    DataBarRule(start_type="num", start_value=0, end_type="max", color=GOOD, showValue=True))
mdl.cell(mdl.r, 1, "Fleet size is driven by peak demand, which does not change with the model - "
                   "what changes is how much iron it takes to meet it. The cheapest weights to run "
                   "are rarely the cheapest weights to own.", f(8, color=MUTED, i=True))
mdl.r += 2
mdl.cell(mdl.r, 1, "Cheapest to own", f(10, True))
mdl.cell(mdl.r, 2, "=INDEX($A${0}:$A${1},MATCH(MIN($O${0}:$O${1}),$O${0}:$O${1},0))"
         .format(OWN_FIRST, OWN_LAST), f(10, True, ACCENT))
mdl.r += 1
mdl.cell(mdl.r, 1, "Cheapest per token", f(10, True))
mdl.cell(mdl.r, 2, "=INDEX($A${0}:$A${1},MATCH(MIN($E${0}:$E${1}),$E${0}:$E${1},0))"
         .format(API_FIRST, API_LAST), f(10, True, ACCENT))
mdl.ws.freeze_panes = "A4"



# ═══ 6. Scale ════════════════════════════════════════════════════════════
# The whole model replayed once per team size, one column each. Everything the
# head count touches is recomputed; everything it does not (the model, the
# quantisation, the per-card specs) is read from Workings by name.
SIZES = [1, 2, 5, 10, 25, 50, 100, 200, 350, 500, 750, 1000]
sc = Sheet(wb, "Scale", [40, 22] + [13] * len(SIZES))
sc.title_row("How the answer changes with team size",
             "Every input is exactly as you left it on Inputs - only the head count moves. "
             "This is where the break-even lives.")

FC = 3
CL = [get_column_letter(FC + i) for i in range(len(SIZES))]
SR = {}


def srow(key, label, expr, fmt=NUM2, note="", bold=False, money=False):
    """One replay row: the same formula in every team-size column.

    `expr` is a template - {c} is the column letter, and any other {name} is
    the row number of an earlier row in this block."""
    r = sc.r
    sc.cell(r, 1, label, f(9, bold))
    if note:
        sc.cell(r, 2, note, f(8, color=MUTED))
    for i, col in enumerate(CL):
        sc.cell(r, FC + i, "=" + expr.format(c=col, **SR), f(9, bold),
                fmt=MONEY if money else fmt, align="right")
    SR[key] = r
    sc.r += 1
    return r


sc.section("Team size", span=2 + len(SIZES))
r = sc.r
sc.cell(r, 1, "Developers", f(11, True))
sc.cell(r, 2, "edit these if you like", f(8, color=MUTED))
for i, n in enumerate(SIZES):
    sc.cell(r, FC + i, n, f(11, True, INPUT_B), fmt=NUM, align="right", border=BOX, fill="FFFDE7")
SR["devs"] = r
name("scale_devs", "Scale", "${}${}:${}${}".format(CL[0], r, CL[-1], r))
sc.r += 2

sc.section("Volumes, fleet and staffing at each size", span=2 + len(SIZES))
srow("outT", "Output tokens / mo", "{c}${devs}*outTok*1000*workdays", NUM)
srow("inT", "Input tokens / mo", "{c}${devs}*inTok*1000000*workdays", NUM)
srow("cached", "Cached input", "{c}${inT}*MIN(1,cacheShare)", NUM)
srow("fresh", "Fresh input", "{c}${inT}-{c}${cached}", NUM)
srow("tasks", "Accepted tasks / mo", "{c}${devs}*tasksDay*workdays", NUM)
srow("live", "Live sessions at once", "{c}${devs}*sessConc", NUM1)
srow("peakO", "Peak demand, open model",
     "IF(AND(workdays>0,activeHrs>0),{c}${outT}*tm_o/workdays/(activeHrs*3600)*peak,0)", NUM,
     "tok/s in the busy hour")
srow("reps", "Replicas",
     "IF({c}${devs}=0,0,IF(replicaTps>0,MAX(1,CEILING({c}${peakO}/replicaTps,1)),1))", NUM)
srow("gpus", "Cards in the fleet", "{c}${reps}*gpusPerReplica", NUM)
srow("hosts", "Hosts", "CEILING({c}${gpus}/8,1)", NUM)
srow("fleetTps", "Sustained fleet tok/s", "{c}${reps}*replicaTps", NUM)
srow("hwCapex", "Hardware capital",
     "{c}${gpus}*gpuBuy*(1+spares)+{c}${hosts}*(hostCost+netFabric+installHost)", money=True)
srow("setupL", "Setup labour",
     'IF(labourYN="Yes",(setupArch+{c}${hosts}*setupRack+setupStack+setupEval+setupSec)*engHr,0)',
     money=True)
srow("ramp", "Staffing ramp",
     "IF(platformAt>soloAt,MIN(1,MAX(0,({c}${devs}-soloAt)/(platformAt-soloAt))),"
     "IF({c}${devs}>soloAt,1,0))", NUM2)
srow("platM", "Baseline platform team",
     'IF(AND(labourYN="Yes",ownsPlatform="No"),platformFte*fteMo*{c}${ramp},0)', money=True)
srow("admM", "Fleet admin", 'IF(labourYN="Yes",adminFte*fteMo*{c}${ramp},0)', money=True)
srow("cldM", "Cloud plumbing", 'IF(labourYN="Yes",cloudOps*fteMo*{c}${ramp},0)', money=True)
srow("kw", "Fleet draw kW", "{c}${gpus}*gpuW/1000*1.25", NUM1)
srow("dragO", "Developer time, open model",
     "{c}${devs}*tasksDay*workdays*MAX(0,mins_o-baseMins)/60*devRate", money=True)
srow("dragF", "Developer time, frontier",
     "{c}${devs}*tasksDay*workdays*MAX(0,mins_f-baseMins)/60*devRate", money=True)
srow("dragH", "Developer time, hybrid",
     "{c}${devs}*tasksDay*workdays*MAX(0,mins_h-baseMins)/60*devRate", money=True)
srow("peakH", "Peak demand, hybrid open tier",
     "IF(AND(workdays>0,activeHrs>0),{c}${outT}*own_h/workdays/(activeHrs*3600)*peak,0)", NUM)
srow("repsH", "Hybrid replicas",
     "IF({c}${devs}=0,0,IF(replicaTps>0,MAX(1,CEILING({c}${peakH}/replicaTps,1)),1))", NUM)
srow("gpusH", "Hybrid cards", "{c}${repsH}*gpusPerReplica", NUM)
srow("hostsH", "Hybrid hosts", "CEILING({c}${gpusH}/8,1)", NUM)
srow("hCapexH", "Hybrid hardware capital",
     "{c}${gpusH}*gpuBuy*(1+spares)+{c}${hostsH}*(hostCost+netFabric+installHost)", money=True)
srow("setupLH", "Hybrid setup labour",
     'IF(labourYN="Yes",(setupArch+{c}${hostsH}*setupRack+setupStack+setupEval+setupSec)*engHr,0)',
     money=True, note="against the hybrid's own hosts")
srow("hBuyT", "Hybrid, if bought",
     "{c}${hCapexH}/amort+{c}${gpusH}*gpuW/1000*1.25*(pue*730*kwhDc+coloKw)+storMo"
     "+{c}${hCapexH}*warranty/12+{c}${setupLH}/amort", money=True)
srow("hRentT", "Hybrid, if rented",
     "{c}${gpusH}*gpuRent*730*rentUtil+storMo+rentSetup/amort", money=True)
srow("hBuy", "Cheaper to buy the hybrid fleet?",
     'IF({c}${hBuyT}<={c}${hRentT},"Yes","No")', None)
sc.blank()


def stoks(i, o, c_, mult):
    return ("({{c}}${fresh}*{m}/1000000*{i}+{{c}}${cached}*{m}/1000000*{c_}"
            "+{{c}}${outT}*{m}/1000000*{o})*disc").format(
        m=mult, i=i, o=o, c_=c_, fresh="{fresh}", cached="{cached}", outT="{outT}")


SROUTE = {
    "laptop": "{c}${devs}*lapUplift/amort+{c}${devs}*lapWatts/1000*codeHrs*workdays*kwhOffice"
              '+IF(labourYN="Yes",{c}${devs}*lapSupport/12*itRate,0)+{c}${dragO}',
    "buy": "{c}${hwCapex}/amort+{c}${kw}*(pue*730*kwhDc+coloKw)+storMo+{c}${hwCapex}*warranty/12"
           "+{c}${platM}+{c}${admM}+{c}${setupL}/amort+{c}${dragO}",
    "rent": "{c}${gpus}*gpuRent*730*rentUtil+storMo+{c}${platM}+{c}${admM}+rentSetup/amort"
            "+{c}${dragO}",
    "serverless": "{c}${platM}+" + stoks("orIn", "orOut", "orCache", "tm_o") + "*(1+orFee)"
                  "+{c}${dragO}",
    "bedrock": "{c}${platM}+{c}${cldM}+" + stoks("bedIn", "bedOut", "bedCache", "1") + "+{c}${dragF}",
    "azure": "{c}${platM}+{c}${cldM}+" + stoks("azIn", "azOut", "azCache", "1") + "+{c}${dragF}",
    "anthropic": "{c}${platM}+" + stoks("anIn", "anOut", "anCache", "1") + "+{c}${dragF}",
    "openai": "{c}${platM}+" + stoks("oaIn", "oaOut", "oaCache", "1") + "+{c}${dragF}",
    "hybrid": 'IF({c}${hBuy}="Yes",{c}${hBuyT},{c}${hRentT})+{c}${platM}+{c}${admM}+'
              + stoks("anIn", "anOut", "anCache", "api_h") + "+{c}${dragH}",
    "seats": '{c}${platM}+{c}${devs}*(seat+IF(ownsBase="Yes",0,seatBase))+{c}${dragF}',
}

sc.section("Monthly cost of every route, at every team size", span=2 + len(SIZES))
r = sc.r
sc.cell(r, 1, "Route", f(9, True, MUTED), border=UNDER)
for i, n in enumerate(SIZES):
    sc.cell(r, FC + i, n, f(9, True, MUTED), border=UNDER, fmt=NUM, align="right")
sc.r += 1
SROUTE_FIRST = sc.r
for rid, rname, _ in ROUTES:
    srow("rt_" + rid, rname, SROUTE[rid], money=True)
SROUTE_LAST = sc.r - 1
sc.blank()

sc.section("Where it crosses", span=2 + len(SIZES))
# The fair fight: accelerators you own against tokens someone else serves, over the
# full term, with each route's developer-time penalty stripped from both sides so
# the comparison is about infrastructure rather than about model quality. Laptops
# are left out - one machine per developer is a different question from a fleet.
srow("cashBuy", "Full-term cash, buying the fleet",
     "({c}${hwCapex}+{c}${setupL})"
     "+({c}${rt_buy}-{c}${hwCapex}/amort-{c}${dragO})*horizon", money=True)
srow("cashRent", "Full-term cash, renting the fleet",
     "rentSetup+({c}${rt_rent}-{c}${dragO})*horizon", money=True)
srow("cashHyb", "Full-term cash, hybrid",
     'IF({c}${hBuy}="Yes",{c}${hCapexH}+{c}${setupLH},rentSetup)'
     '+({c}${rt_hybrid}-IF({c}${hBuy}="Yes",{c}${hCapexH}/amort,0)-{c}${dragH})*horizon',
     money=True)
srow("cashHosted", "Full-term cash, cheapest hosted",
     "MIN(({c}${rt_serverless}-{c}${dragO})*horizon,"
     "({c}${rt_bedrock}-{c}${dragF})*horizon,({c}${rt_azure}-{c}${dragF})*horizon,"
     "({c}${rt_anthropic}-{c}${dragF})*horizon,({c}${rt_openai}-{c}${dragF})*horizon,"
     "({c}${rt_seats}-{c}${dragF})*horizon,{c}${cashHyb})", money=True, bold=True,
     note="serverless, the clouds, the labs, seats and the hybrid")
srow("owned", "Full-term cash, cheapest fleet you own",
     "MIN({c}${cashBuy},{c}${cashRent})", money=True, bold=True,
     note="buying or renting accelerators - laptops are a different question")
srow("wins", "Does owning win here?", 'IF({c}${owned}<{c}${cashHosted},{c}${devs},"")', NUM)
srow("best", "Cheapest route",
     "INDEX(cat_routes,MATCH(MIN({c}${first}:{c}${last}),{c}${first}:{c}${last},0))"
     .replace("{first}", str(SROUTE_FIRST)).replace("{last}", str(SROUTE_LAST)), None, bold=True)
srow("perdev", "Per developer, per month",
     "IF({c}${devs}>0,MIN({c}${first}:{c}${last})/{c}${devs},0)"
     .replace("{first}", str(SROUTE_FIRST)).replace("{last}", str(SROUTE_LAST)), money=True)
sc.blank()

name("cat_routes", "Workings", "$A${}:$A${}".format(ROUTE_FIRST, ROUTE_LAST))
r = sc.r
sc.cell(r, 1, "Owning accelerators first wins at", f(11, True))
sc.cell(r, 2, "developers", f(8, color=MUTED))
sc.cell(r, FC, "=IFERROR(MIN({0}${1}:{2}${1}),0)".format(CL[0], SR["wins"], CL[-1]),
        f(11, True, ACCENT), fmt=NUM, align="right", border=BOX)
name("be_devs", "Scale", "${}${}".format(CL[0], r))
sc.r += 1
sc.cell(sc.r, 1, "Zero means owning never wins inside the sizes above. Both sides are full-term cash "
                 "with the developer-time penalty stripped out, so the comparison is about "
                 "infrastructure rather than about model quality - the fair fight. Put the penalty "
                 "back and owning has to win by that much more.",
        f(8, color=MUTED, i=True))
sc.r += 2

chart2 = LineChart()
chart2.title = "Cost per developer per month, by team size"
chart2.y_axis.title = "$ / developer / month"
chart2.x_axis.title = "Developers"
chart2.height = 11
chart2.width = 26
PICK = ["laptop", "buy", "serverless", "anthropic", "hybrid", "seats"]
for rid in PICK:
    row = SR["rt_" + rid]
    ref = Reference(sc.ws, min_col=1, max_col=FC + len(SIZES) - 1, min_row=row, max_row=row)
    chart2.add_data(ref, titles_from_data=True, from_rows=True)
chart2.set_categories(Reference(sc.ws, min_col=FC, max_col=FC + len(SIZES) - 1,
                                min_row=SR["devs"], max_row=SR["devs"]))
sc.ws.add_chart(chart2, "A{}".format(sc.r))
sc.ws.freeze_panes = "C4"


# ═══ 7. Finishing ════════════════════════════════════════════════════════
wb.move_sheet("Answer", offset=-wb.sheetnames.index("Answer"))
for i, nm in enumerate(["Answer", "Inputs", "Models", "Scale", "Workings", "Catalogues"]):
    wb.move_sheet(nm, offset=i - wb.sheetnames.index(nm))

for nm, colour in (("Answer", "1F3A5F"), ("Inputs", "125EC4"), ("Models", "0F7B4F"),
                   ("Scale", "8A5A00"), ("Workings", "6B7280"), ("Catalogues", "9AA3AE")):
    wb[nm].sheet_properties.tabColor = colour

# Answer and Inputs are the two pages anyone prints.
for nm, area, landscape in (("Answer", "A1:J{}".format(ARANK_LAST + 14), True),
                            ("Inputs", "A1:E{}".format(inp.r), False),
                            ("Models", "A1:Q{}".format(mdl.r), True)):
    ws = wb[nm]
    ws.print_area = area
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.5
    ws.oddFooter.left.text = "Coding assistant TCO - offline edition"
    ws.oddFooter.right.text = "Page &P of &N"

wb["Answer"].sheet_view.zoomScale = 100
wb.properties.title = "Coding assistant - three-year cost of ownership"
wb.properties.creator = "neocloudcalc"
wb.properties.description = (
    "Offline edition of the coding-model TCO calculator. Formulas only, no macros. "
    "Change the blue cells on Inputs; every other sheet recalculates.")

# ===SHEETS-GO-ABOVE-THIS-LINE===
register()
wb.save(OUT)
print("wrote", OUT, "with", len(NAMES), "defined names")
