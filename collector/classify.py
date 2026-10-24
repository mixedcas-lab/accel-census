"""Classification and spec extraction for AI-accelerator and compute-in-memory papers.

Pure functions (no network, no files) so they can be unit-tested and re-run over the
cached records whenever the rules change. Abstracts are inputs only; they are never
written to the output.
"""
import re

I = re.IGNORECASE

# ---------------------------------------------------------------- relevance
# a machine-learning workload ...
ML = (r"neural[- ]networks?|\b[DCRG]NNs?\b|\bDNN|\bCNN|\bRNN|\bLSTM|\bGCN|\bGNN|\bMLP|deep[- ]learning|"
      r"transformers?\b|\bLLMs?\b|large[- ]language|attention|\bBERT|\bViT\b|\bGPT|diffusion model|"
      r"machine[- ]learning|\bAI\b|artificial intelligence|(?:on[- ]device|edge|model) inference|on[- ]chip (?:training|learning)|"
      r"training (?:processor|accelerator|engine|chip)|spiking|\bSNNs?\b|neuromorphic|"
      r"recommend(?:ation|er)|\bDLRM|binar(?:y|ized) (?:neural|weight)|\bBNN|quantized (?:neural|DNN|model)|"
      r"keyword[- ]spotting|speech recognition|edge intelligence|neural (?:processing|engine)|\bML\b|learning[- ]based|"
      r"\bembedded (?:ML|AI)|tinyML")
# ... run on hardware
HW = (r"accelerat(?:or|ors|ion)\b|processors?\b|\bNPUs?\b|\bTPU|engines?\b|chips?\b|\bSoCs?\b|\bcores?\b|macros?\b|"
      r"arrays?\b|architectures?\b|hardware|\bASIC|\bFPGA|silicon|dataflow|systolic|units?\b|\bICs?\b|"
      r"in[- ]memory|near[- ]memory|in[- ]sensor|\bPIM\b|\bCIM\b|\bMAC\b|datapath|microarchitecture")
ML_RX = re.compile(ML, I)
HW_RX = re.compile(HW, I)

# compute-in-memory / processing-in-memory is in scope whatever the workload
CIM_RX = re.compile(r"(?:compute|computing|computation|processing)[- ](?:in|near)[- ]memory|in[- ]memory (?:comput|process)|"
                    r"\bCIM\b|\bPIM\b|\bIMC\b|memory[- ]centric (?:comput|accelerat)|near[- ]memory (?:comput|process)|"
                    r"\b(?:SRAM|RRAM|ReRAM|DRAM|eDRAM|MRAM|memristor)\b.*\bin[- ]memory\b|\bin[- ]memory\b.*\b(?:SoC|macro|accelerat\w*|processor)", I)

# RF and power "transformers", "attention" and "training sequences" are not machine learning
RF_POWER = re.compile(r"\b(?:PA|LNA|VCO|mixer|balun|antenna|oscillator|receiver|transmitter|transceiver|amplifier|DC[-–]DC|isolat\w+|"
                      r"converter|inductor|coil|[GM]Hz|dB|wireless power|gate driver|rectifier|resonan\w+)\b", I)
ML_STRONG = re.compile(r"neural[- ]network|\bDNN|\bCNN|\bLLM|deep[- ]learning|machine[- ]learning|\bAI\b|inference|"
                       r"neural (?:processing|engine)|spiking|neuromorphic|vision transformer|transformer (?:model|inference|accelerat|processor)", I)

# not accelerators: machine learning used *for* design automation, test or devices; biomedical "neural" circuits
ML_FOR_EDA = re.compile(r"placement|routing|\brouter\b|timing (?:prediction|analysis|closure)|layout|lithograph|hotspot|"
                        r"(?:logic|high[- ]level) synthesis|verification|testing\b|test pattern|yield|sizing|floorplan|"
                        r"congestion|netlist|\bOPC\b|mask|circuit (?:design|optimization)|"
                        r"\bEDA\b|power (?:grid|delivery) analysis|IR[- ]drop|aging prediction|reliability analysis", I)
NOT_ML_HW = re.compile(r"neural (?:recording|interface|probe|stimulat|signal|implant|activity|sensing|front[- ]end)|"
                       r"neural[- ]recording|brain[- ]machine|neuro[- ]?stimulat|acceleromet|gyroscope", I)

NON_PAPER = re.compile(
    r"^(front cover|back cover|table of contents|contents|author index|index|"
    r"call for papers|editorial|guest editorial|reviewers|session \d+ overview|"
    r"(?:tutorials?|short course|evening (?:event|session)|forum|panel|keynote|plenary)(?=\s*:|\s*$)|"
    r"(ieee )?(transactions|journal|micro) .*information|blank page|copyright|in this issue|"
    r"introduction to the special|special issue)\b", I)


def relevance(title, abstract):
    """Return 'core' (the paper is an AI accelerator or a CIM/PIM design), 'related' or None."""
    t = title or ""
    if NOT_ML_HW.search(t):
        return None
    if CIM_RX.search(t):
        return "core"
    if ML_RX.search(t) and HW_RX.search(t):
        if RF_POWER.search(t) and not ML_STRONG.search(t):
            return None
        if ML_FOR_EDA.search(t) and not re.search(r"accelerator|processor|\bNPU|in[- ]memory|\bPIM\b|\bCIM\b", t, I):
            return None
        return "core"
    a = abstract or ""
    if re.search(r"(?:neural[- ]network|DNN|CNN|transformer|AI|deep[- ]learning|inference)[- ]accelerator|"
                 r"\bNPU\b|compute[- ]in[- ]memory|processing[- ]in[- ]memory|in[- ]memory computing", a, I) \
            and not ML_FOR_EDA.search(t) and not NOT_ML_HW.search(t):
        return "related"
    return None


# ------------------------------------------------------------- type / architecture / application
def accel_type(title, abstract):
    text = (title or "") + " " + (abstract or "")
    if CIM_RX.search(title or "") or re.search(r"(?:compute|computing|processing)[- ]in[- ]memory|in[- ]memory comput", text, I):
        return "CIM/PIM"
    return "Digital"


ARCH_RULES = [
    ("SRAM CIM",           r"\bSRAM\b.*(?:in[- ]memory|\bCIM|\bIMC)|(?:in[- ]memory|\bCIM|\bIMC).*\bSRAM\b"),
    ("DRAM/HBM PIM",       r"\bDRAM\b.*(?:in[- ]memory|\bPIM|near[- ]memory)|\bHBM[- ]?PIM|\bPIM\b.*\bDRAM|\bHBM\b|\bGDDR|\bLPDDR"),
    ("NVM CIM",            r"\bRRAM|\bReRAM|memristor|\bPCM\b|phase[- ]change|\bMRAM|\bFeFET|\bFeRAM|\bNOR[- ]flash|flash[- ]based (?:CIM|in[- ]memory)"),
    ("Analog CIM",         r"analog[- ](?:in[- ]memory|CIM|computing|MAC|domain)|charge[- ](?:domain|based|sharing)|current[- ](?:domain|mode)|time[- ]domain|capacit(?:or|ive)[- ]based"),
    ("Digital CIM",        r"digital[- ](?:in[- ]memory|CIM|IMC|comput\w+[- ]in[- ]memory)|\bDCIM\b|all[- ]digital (?:CIM|in[- ]memory)"),
    ("Systolic/dataflow",  r"systolic|dataflow|spatial architecture|\bCGRA\b|coarse[- ]grained reconfigurable"),
    ("Sparsity",           r"sparse|sparsity|pruning|pruned|zero[- ]skipping|zero[- ]gating"),
    ("Low precision",      r"\bbinar(?:y|ized)|ternary|\b[1-4][- ]?bits?\b|\bINT[248]\b|quantiz|mixed[- ]precision|bit[- ](?:serial|scalable|precision)|\blog(?:arithmic)?[- ]domain|\bposit\b"),
    ("Floating point",     r"floating[- ]point|\bFP(?:8|16|32)\b|\bBF16\b|bfloat|block floating"),
    ("Reconfigurable",     r"reconfigur|\bFPGA\b|programmable|flexible|multi[- ]mode"),
    ("Near-memory",        r"near[- ](?:memory|data|DRAM)|3[- ]?D[- ](?:stack|integrat)|chiplet"),
    ("Spiking/neuromorphic", r"spiking|\bSNNs?\b|neuromorphic"),
    ("In-sensor",          r"in[- ]sensor|near[- ]sensor|always[- ]on|in[- ]pixel"),
]
ARCH_RX = [(n, re.compile(p, I)) for n, p in ARCH_RULES]


def architectures(title, abstract):
    def scan(text):
        return [n for n, rx in ARCH_RX if rx.search(text or "")]
    tags = scan(title)
    if abstract:
        first = " ".join(re.split(r"(?<=[.!?])\s+", abstract)[:3])   # the design itself, not the comparisons
        for t in scan(first):
            if t not in tags:
                tags.append(t)
    return tags


APP_RULES = [
    ("Transformer/LLM",   r"transformer|\bLLMs?\b|large[- ]language|attention|\bBERT|\bGPT|\bViT\b|language model"),
    ("CNN/vision",        r"\bCNN|convolution|vision|image|object detection|classification|\bResNet|\bVGG|MobileNet|segmentation|super[- ]resolution"),
    ("Training",          r"\btraining\b|on[- ]chip learning|on[- ]device learning|back[- ]?propagation|fine[- ]tun"),
    ("Speech/audio",      r"speech|keyword[- ]spotting|\bKWS\b|audio|voice"),
    ("Edge/IoT",          r"\bedge\b|\bIoT\b|mobile|wearable|always[- ]on|battery|ultra[- ]low[- ]power|tiny ?ML|[µμu]W\b"),
    ("Datacenter",        r"data[- ]?center|cloud|server|warehouse|\bTPU\b|exascale|\bHPC\b"),
    ("Graph/recommendation", r"\bgraph\b|\bGNN|\bGCN|recommend|\bDLRM|embedding table"),
    ("Generative/diffusion", r"diffusion|generative|\bGAN\b"),
    ("Autonomous/robotics", r"autonomous|robot|drone|\bSLAM\b|driving|automotive|point cloud|LiDAR|navigation"),
]
APP_RX = [(n, re.compile(p, I)) for n, p in APP_RULES]

# measured silicon (a fabricated chip) as opposed to a simulated architecture
SILICON_RX = re.compile(r"fabricated|test[- ]?chip|prototype chip|\bmeasured\b|measurement results|silicon[- ](?:proven|verified|measured)|"
                        r"\btaped[- ]out|die (?:area|photo)|generation silicon|in production", I)
SILICON_VENUES = {"ISSCC", "VLSI", "JSSC", "CICC", "A-SSCC", "ESSCIRC", "SSC-L"}


def applications(title, abstract):
    text = (title or "") + " " + (abstract or "")
    return [n for n, rx in APP_RX if rx.search(text)]


def is_silicon(title, abstract, venue):
    return venue in SILICON_VENUES or bool(SILICON_RX.search((title or "") + " " + (abstract or "")))


# ------------------------------------------------------------- spec parsing
NUM = r"(\d+(?:,\d{3})*(?:\.\d+)?)"
_SI = {"a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6,
       "m": 1e-3, "": 1.0, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15}
_RANGE = r"(?:" + NUM + r"\s*(?:-|–|to|-to-|~)\s*)?"          # "5.3-to-89.6 TOPS/W": keep the upper end

# energy efficiency in TOPS/W: "35.2 TOPS/W", "1.2 POPS/W", "650 GOPS/W", "3.1 GOPS/mW"; "TOPS/W/mm2" is skipped
EFF_RX = re.compile(_RANGE + NUM + r"\s*-?\s*([GTP])(?:FL)?OPS\s*/\s*(m?)W\b(?!\s*/)", I)
EFF_WATT_RX = re.compile(_RANGE + NUM + r"\s*-?\s*([GTP])(?:FL)?OPS\s*(?:per\s+watt|/\s*watt)", I)
# energy per operation: "4.2 fJ/op", "0.33 pJ/MAC" (1 MAC = 2 ops)
EOP_RX = re.compile(NUM + r"\s*-?\s*([afpn])J\s*/\s*(op|operation|MAC|SOP)\b", I)
# throughput: "4.1 TOPS", "820 GOPS", "1.2 TFLOPS" (not followed by /W or /mm2)
THR_RX = re.compile(_RANGE + NUM + r"\s*-?\s*([GTP])(?:FL)?OPS\b(?!\s*/)(?!\s*per)", I)
AEFF_RX = re.compile(_RANGE + NUM + r"\s*-?\s*([GTP])(?:FL)?OPS\s*/\s*mm\s*(?:2|²|\^2)", I)
FREQ_RX = re.compile(r"(?<![\w.])" + NUM + r"\s*-?\s*([MG])Hz\b")
MEM_RX = re.compile(NUM + r"\s*-?\s*([KkMG])(B|b|bit|byte)s?\b[- ]?(?:\w+[- ]){0,2}?(?:SRAM|eDRAM|RRAM|ReRAM|MRAM|CIM|IMC|macro|"
                    r"on[- ]chip|buffer|memory|cache|scratchpad|global)", I)
PREC_INT_RX = re.compile(r"\bINT[- ]?(\d{1,2})\b|\b(\d{1,2})[- ]?b(?:it)?s?\b[- ](?:\w+[- ]){0,1}?(?:precision|weights?|activations?|inputs?|integer|fixed|quantiz|MAC|operands?)", I)
PREC_B_RX = re.compile(r"(?<![\w.])(\d{1,2})[- ]?b\b(?![- ]?(?:it|yte))")     # "8b", "-4b" (case-sensitive: "8B" is bytes)
PREC_FP_RX = re.compile(r"\b(?:FP|BF)(\d{1,2})\b|\bbfloat(16)\b", I)
NODE_NM_RX = re.compile(r"(?<![\w.])(\d{1,3})\s*-?\s*nm\b", I)
NODE_UM_RX = re.compile(r"(?<![\w.])(0\.\d{1,3})\s*-?\s*[µμu]m\b", I)
POWER_VAL = NUM + r"\s*-?\s*([nuµμm]?)W\b(?!\s*/)"
POWER_CTX_RX = re.compile(r"(?:consum\w*|dissipat\w*|power(?:\s+consumption)?|draw(?:s|ing)|drains?|burns?)[^.;]{0,40}?" + POWER_VAL, I)
POWER_AFTER_RX = re.compile(POWER_VAL + r"\s*(?:of\s+)?(?:total\s+|overall\s+|average\s+)?(?:power|consumption|dissipation)", I)
POWER_TITLE_RX = re.compile(POWER_VAL)
AREA_RX = re.compile(NUM + r"\s*-?\s*mm\s*(?:2|²|\^2)(?!\s*/)", I)

_FIXES = [(re.compile(r"(\d)\.\s(\d)"), r"\1.\2"), (re.compile(r"(\d)\s*-?\s*mu(m|W|A|V|s|J)\b"), r"\1 µ\2"),
          (re.compile(r"([µμ])\s+m\b"), r"\1m"), (re.compile(r"\\?hbox\s*"), ""), (re.compile(r"TOPs\b"), "TOPS")]


def _norm(text):
    for rx, rep in _FIXES:
        text = rx.sub(rep, text)
    return text


def _num(s):
    return float(s.replace(",", ""))


def _best(rx, text, conv, lo, hi):
    """Largest plausible value of rx in text (the peak figure of a paper that lists several)."""
    best = None
    for m in rx.finditer(text or ""):
        v = conv(m)
        if v is not None and lo <= v <= hi and (best is None or v > best):
            best = v
    return best


def _tops(m):
    return _num(m.group(2)) * _SI[m.group(3).upper()] / 1e12


def _eff(m):
    return _tops(m) * (1e3 if m.group(4) else 1.0)                   # per mW -> per W


def parse_specs(title, abstract):
    t, a = _norm(title or ""), _norm(abstract or "")
    out = {}
    for text in (t, a):
        v = _best(EFF_RX, text, _eff, 1e-4, 1e5) or _best(EFF_WATT_RX, text, _tops, 1e-4, 1e5)
        if v:
            out["eff"] = v
            break
    if "eff" not in out:
        m = EOP_RX.search(t) or EOP_RX.search(a)
        if m:
            e = _num(m.group(1)) * _SI[m.group(2).lower()]                   # J per op or per MAC
            ops = 2.0 if m.group(3).upper() == "MAC" else 1.0
            if e > 0 and 1e-4 <= ops / e / 1e12 <= 1e5:
                out["eff"] = ops / e / 1e12
    for text in (t, a):
        v = _best(THR_RX, text, _tops, 1e-5, 1e5)
        if v:
            out["thr"] = v
            break
    for text in (t, a):
        v = _best(AEFF_RX, text, _tops, 1e-5, 1e5)
        if v:
            out["aeff"] = v
            break
    for text in (t, a):
        v = _best(FREQ_RX, text, lambda m: _num(m.group(1)) * _SI[m.group(2)], 5e6, 5e9)
        if v:
            out["f"] = v
            break
    m = MEM_RX.search(t) or MEM_RX.search(a)
    if m:
        size = _num(m.group(1)) * {"k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9}[m.group(2)]
        out["mem"] = size / 8 if m.group(3) in ("b", "bit") else size        # bytes
    bits = [int(x or y) for x, y in PREC_INT_RX.findall(t + " " + a) if 1 <= int(x or y) <= 32]
    bits += [int(x) for x in PREC_B_RX.findall(t + " " + a) if 1 <= int(x) <= 16]
    fp = [int(x or y) for x, y in PREC_FP_RX.findall(t + " " + a) if 4 <= int(x or y) <= 64]
    if bits or fp:
        out["prec"] = max(bits + fp)
    m = NODE_NM_RX.search(t) or NODE_NM_RX.search(a)
    if m and 2 <= int(m.group(1)) <= 500:
        out["node"] = int(m.group(1))
    else:
        m = NODE_UM_RX.search(t) or NODE_UM_RX.search(a)
        if m:
            out["node"] = int(round(float(m.group(1)) * 1000))
    m = POWER_CTX_RX.search(a) or POWER_AFTER_RX.search(a) or POWER_CTX_RX.search(t) or POWER_TITLE_RX.search(t)
    if m:
        v = _num(m.group(1)) * _SI[m.group(2) or ""]
        if 1e-9 <= v <= 1e4:
            out["p"] = v
    m = AREA_RX.search(a) or AREA_RX.search(t)
    if m and 1e-4 <= _num(m.group(1)) <= 5e4:
        out["area"] = _num(m.group(1))
    return out


def spec_sources(title, abstract):
    """parse_specs() plus where each value came from: {"key": "t" | "a"}."""
    full = parse_specs(title, abstract)
    only_title = parse_specs(title, "")
    return full, {k: ("t" if only_title.get(k) == v else "a") for k, v in full.items()}


def derived(specs):
    """Values computed from others when the paper does not state them."""
    d = {}
    if "aeff" not in specs and specs.get("thr") and specs.get("area"):
        d["aeff_calc"] = round(specs["thr"] / specs["area"], 6)
    if "eff" not in specs and specs.get("thr") and specs.get("p"):
        d["eff_calc"] = round(specs["thr"] / specs["p"], 6)
    return d


# ------------------------------------------------------------- affiliations and dates (same rules as adc-census)
ORG_HINT = re.compile(r"universit|institut|college|school|KAIST|POSTECH|UNIST|DGIST|GIST|\bETH\b|EPFL|\bMIT\b|"
                      r"laborator|\blabs?\b|inc\b|ltd|corp|company|co\.|electronics|semiconductor|technolog|"
                      r"research|centre|center|academy|imec|tsmc|samsung|sk hynix|intel|mediatek|qualcomm|"
                      r"apple|google|huawei|broadcom|analog devices|texas instruments|nvidia|\bamd\b|\bibm\b|microsoft", I)


def org_and_country(aff):
    if not aff:
        return None, None
    parts = [p.strip() for p in aff.split(",") if p.strip()]
    if not parts:
        return None, None
    country = re.sub(r"\s+\d[\d\- ]*$", "", parts[-1])
    if re.fullmatch(r"(korea|south korea|republic of korea|korea \(south\))", country, I):
        country = "South Korea"
    elif re.fullmatch(r"(usa|u\.s\.a\.|united states|united states of america|us)", country, I):
        country = "USA"
    elif re.fullmatch(r"(prc|p\.r\. china|people's republic of china)", country, I):
        country = "China"
    org = None
    for p in parts:
        if ORG_HINT.search(p) and not re.match(r"(department|dept|school of|faculty|division)\b", p, I):
            org = p
            break
    if org is None:
        org = parts[1] if len(parts) > 2 else parts[0]
    if len(country) > 30 or re.search(r"\d", country):
        country = None
    return org, country


MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_month(pubdate, year):
    s = (pubdate or "").lower()
    m = re.match(r"((?:19|20)\d{2})-(\d{2})", s)     # ISO dates from Crossref/OpenAlex
    if m:
        return "%s-%s" % m.groups()
    years = re.findall(r"(?:19|20)\d{2}", s)
    y = years[-1] if years else (str(year) if year else None)
    mon = None
    for tok in re.findall(r"[a-z]{3,}", s):
        if tok[:3] in MONTHS:
            mon = MONTHS[tok[:3]]
            break
    if y and mon:
        return "%s-%02d" % (y, mon)
    return y or ""
