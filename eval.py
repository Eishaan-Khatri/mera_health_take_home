"""Evaluate lab-report extraction against labels/.

Usage:
    python eval.py run --extractor extract.py --tag NAME [--repeats 3] [--reports 01,02,...]
    python eval.py score runs/NAME [--labels gold]
    python eval.py diff runs/A runs/B

`run` calls `python <extractor> <report>` exactly as the graders will, with timeouts,
retries, quota pacing and token/cost logging, then scores the outputs.
`score` re-scores a saved run without any API calls.
`diff` shows, per label row, what got fixed / broken / is unstable across all repeats.

Held-out reports (04, 07, 10, 12) are only run when passed explicitly in --reports.
Names and unit spellings live in eval_vocab.json.
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TUNING = ["01", "02", "03", "05", "06", "08", "09", "11"]
HELD_OUT = ["04", "07", "10", "12"]
VOCAB_PATH = ROOT / "eval_vocab.json"

# USD per 1M tokens: (input, output). Thinking tokens are billed as output.
# Source: ai.google.dev/gemini-api/docs/pricing, read 2026-10-27 (paid tier; free tier is $0).
PRICES = {
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.8-flash": (0.75, 3.75),
}
ELECTROLYTES = {"sodium", "potassium", "chloride"}  # mEq/L == mmol/L only for these

# ---------------------------------------------------------------- normalisation


def clean_name(name):
    s = str(name or "").lower().replace(".", "").replace("μ", "µ")
    for a, b in (("haem", "hem"), ("colour", "color"), ("leuco", "leuko")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9µ]+", " ", s).strip()
    return re.sub(r"^(serum|s) ", "", s)


def clean_unit(unit):
    s = str(unit).lower().replace("μ", "µ").replace("mcg", "µg")
    s = re.sub(r"[\s.()]", "", s)
    s = re.sub(r"^x(?=10)", "", s)
    return re.sub(r"(^|/)u(?=g|iu|l$)", r"\1µ", s)


VOCAB = json.loads(VOCAB_PATH.read_text(encoding="utf-8"))
NAME_KEY = {clean_name(v): c for c, vs in VOCAB["synonyms"].items() for v in [c.replace("_", " ")] + vs}
UNIT_KEY = {clean_unit(v): b for b, vs in VOCAB["unit_buckets"].items() for v in vs}


def name_key(name):
    """Canonical test name. "Full Name (ABBR)" falls back to the abbreviation only when neither
    the whole name nor the full name is recognised, so "Pus Cells (WBC)" stays urine_wbc."""
    s = clean_name(name)
    if s in NAME_KEY:
        return NAME_KEY[s]
    m = re.fullmatch(r"(.*?)\s*\(([^()]*)\)\s*", str(name or ""))
    if m:
        full, abbr = clean_name(m.group(1)), clean_name(m.group(2))
        if full in NAME_KEY:
            return NAME_KEY[full]
        if abbr in NAME_KEY:
            return NAME_KEY[abbr]
    return s


def urine_base(name):
    """For a name with a leading 'Urine', the canonical name of the rest ('Urine Leucocytes' ->
    key of 'Leucocytes'). Used only to pair with a bare label name, never a 'Serum ...' one."""
    m = re.match(r"\s*urine\s+(.+)", str(name or ""), re.I)
    return name_key(m.group(1)) if m else None


def is_bare(name):
    return not re.match(r"\s*(serum|s\.)\s", str(name or ""), re.I)


def unit_bucket(unit):
    return UNIT_KEY.get(clean_unit(unit))


NO_UNIT = {"", "n/a", "na", "-", "none"}  # placeholders that mean "no unit printed"


def split_unit(unit, rng):
    """Move a unit printed inside the range cell into the unit field (report_06 rule)."""
    unit = None if unit is None or str(unit).strip().lower() in NO_UNIT else unit
    if rng is None or not str(rng).strip():
        return unit, None
    toks = str(rng).split()
    for n in (2, 1):
        if len(toks) > n:
            tail = " ".join(toks[-n:])
            b = unit_bucket(tail)
            if b and (unit is None or unit_bucket(unit) == b or clean_unit(unit) == clean_unit(tail)):
                return (unit if unit is not None else tail), " ".join(toks[:-n])
    return unit, rng


NUM = r"\d[\d,]*(?:\.\d+)?"


def norm_quantity(v):
    """Normalise a value or a range: ('num', op, low, high) or ('text', s). None if empty."""
    if v is None or isinstance(v, bool) or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, (int, float)):
        return ("num", "", float(v), None)
    s = str(v).strip().lower()
    for a, b in (("–", "-"), ("—", "-"), ("≤", "<="), ("≥", ">=")):
        s = s.replace(a, b)
    m = re.fullmatch(rf"(<=|>=|<|>)?\s*({NUM})(?:\s*-\s*({NUM}))?", s)
    if m:
        lo, hi = (float(x.replace(",", "")) if x else None for x in m.group(2, 3))
        return ("num", m.group(1) or "", lo, hi)
    return ("text", re.sub(r"\s*([()+/-])\s*", r"\1", re.sub(r"\s+", " ", s)))


def is_abnormal(label):
    """True if the label's value is outside its own printed range (what a doctor acts on)."""
    _, rng = split_unit(label.get("unit"), label.get("reference_range"))
    v, r = norm_quantity(label.get("value")), norm_quantity(rng)
    if v is None or r is None:
        return False
    if v[0] == "text" or r[0] == "text":
        return v != r
    lo, hi = v[2], v[3] if v[3] is not None else v[2]
    if r[3] is not None:
        return lo < r[2] or hi > r[3]
    op, bound = r[1], r[2]
    return {"<": hi >= bound, "<=": hi > bound, ">": lo <= bound, ">=": lo < bound}.get(op, False)


# ---------------------------------------------------------------- comparing rows

CRITICAL = ("wrong_value", "wrong_unit", "wrong_range", "invented_range", "invented_row")
MISS = ("dropped_row", "null_value", "missing_unit", "missing_range")
COLS = (["rows", "correct", "critical", *CRITICAL, "unpaired", "duplicate", "miss_rows", *MISS,
         "review", "out_of_order", "abnormal_rows", "abnormal_critical"])


def compare_fields(lab, pred, key):
    """Issues for a paired row. Unclear cases are 'review_*', never guessed."""
    issues = []
    accepted = [norm_quantity(lab.get("value"))] + [norm_quantity(a) for a in lab.get("accept_values", [])]
    pv = norm_quantity(pred.get("value"))
    if pv not in accepted:
        issues.append("null_value" if pv is None else "wrong_value")

    lu, lr = split_unit(lab.get("unit"), lab.get("reference_range"))
    pu, pr = split_unit(pred.get("unit"), pred.get("reference_range"))
    if lu is None and pu is not None:
        issues.append("review_unit_added")
    elif lu is not None and pu is None:
        issues.append("missing_unit")
    elif lu is not None:
        lb, pb = unit_bucket(lu), unit_bucket(pu)
        same = clean_unit(lu) == clean_unit(pu) or (lb is not None and lb == pb)
        same = same or (key in ELECTROLYTES and {lb, pb} == {"mmol_l", "meq_l"})
        if not same:
            issues.append("wrong_unit" if lb and pb else "review_unit_unknown")

    lrn, prn = norm_quantity(lr), norm_quantity(pr)
    if lrn is None and prn is not None:
        issues.append("invented_range")
    elif lrn is not None and prn is None:
        issues.append("missing_range")
    elif lrn != prn:
        issues.append("wrong_range" if lrn[0] == prn[0] else "review_range_format")
    return issues


def row_sig(r):
    u, rng = split_unit(r.get("unit"), r.get("reference_range"))
    return name_key(r.get("test_name")), norm_quantity(r.get("value")), u and clean_unit(u), norm_quantity(rng)


def lis_len(seq):
    tails = []
    for x in seq:
        i = next((i for i, t in enumerate(tails) if t >= x), len(tails))
        tails[i:i + 1] = [x]
    return len(tails)


def validate(out):
    """Hand-written check against schema.json. Returns an error string or None."""
    if not isinstance(out, dict) or not isinstance(out.get("tests"), list):
        return "top level must be an object with a 'tests' array"
    for i, t in enumerate(out["tests"]):
        if not isinstance(t, dict):
            return f"tests[{i}] is not an object"
        missing = [k for k in ("test_name", "value", "unit", "reference_range") if k not in t]
        if missing:
            return f"tests[{i}] missing {missing}"
        if not isinstance(t["test_name"], str) or isinstance(t["value"], bool) \
                or not isinstance(t["value"], (str, int, float, type(None))) \
                or not all(isinstance(t[k], (str, type(None))) for k in ("unit", "reference_range")):
            return f"tests[{i}] has a field of the wrong type"
    return None


def score_report(labels, output, failure=None):
    """Score one report. `output` is the parsed extractor JSON (or None on failure).
    `row_status[i]` is the outcome of label row i: correct / critical / miss / review / failed."""
    s = {c: 0 for c in COLS}
    s.update(rows=len(labels), failed=None, details=[],
             abnormal_rows=sum(is_abnormal(r) for r in labels), row_status=["miss"] * len(labels))
    if failure is None:
        failure = validate(output) if output is not None else "no output"
        if failure is None and not output["tests"] and labels:
            failure = "empty_output"
    if failure:
        s.update(failed=failure, dropped_row=len(labels), miss_rows=len(labels), row_status=["failed"] * len(labels))
        return s
    preds = output["tests"]
    lkeys = [name_key(r["test_name"]) for r in labels]
    pkeys = [name_key(r.get("test_name")) for r in preds]
    used_l, used_p, pairs = set(), set(), []

    def flag(pred, issue, status, note):
        s["details"].append({"pred": pred, "issues": [issue], "status": status, "note": note})

    # 1) exact canonical-name pairing in printed order; same-name collisions become review
    for key in dict.fromkeys(lkeys + pkeys):
        lis = [i for i, k in enumerate(lkeys) if k == key]
        pis = []
        for j in (j for j, k in enumerate(pkeys) if k == key):
            if any(row_sig(preds[j]) == row_sig(preds[q]) for q in pis):
                s["invented_row"] += 1
                s["duplicate"] += 1
                flag(preds[j], "invented_row", "critical", "exact duplicate")
                used_p.add(j)
            else:
                pis.append(j)
        if not lis or not pis:
            continue
        kind = "exact" if len(lis) == 1 and len(pis) == 1 else "collision"
        pairs += [(i, j, kind) for i, j in zip(lis, pis)]
        used_l.update(lis[:len(pis)])
        used_p.update(pis[:len(lis)])
        for j in pis[len(lis):]:
            s["review"] += 1
            flag(preds[j], "review_collision", "review", f"extra '{key}' row; unclear which label it belongs to")
            used_p.add(j)

    # 1b) 'Urine X' pairs with a leftover bare label 'X' of the same test, in printed order.
    #     Never with 'Serum X': urine albumin is not serum albumin.
    for j in range(len(preds)):
        base = urine_base(preds[j].get("test_name"))
        if j in used_p or base is None:
            continue
        i = next((i for i in range(len(labels)) if i not in used_l and lkeys[i] == base
                  and is_bare(labels[i]["test_name"])), None)
        if i is not None:
            pairs.append((i, j, "exact"))
            used_l.add(i)
            used_p.add(j)

    # 2) fuzzy fallback for leftovers: paired for review only, never counted correct
    cands = sorted(((difflib.SequenceMatcher(None, clean_name(labels[i]["test_name"]),
                                             clean_name(preds[j].get("test_name"))).ratio(), i, j)
                    for i in range(len(labels)) if i not in used_l
                    for j in range(len(preds)) if j not in used_p), reverse=True)
    for ratio, i, j in cands:
        if ratio >= 0.8 and i not in used_l and j not in used_p:
            pairs.append((i, j, "fuzzy"))
            used_l.add(i)
            used_p.add(j)

    # 3) classify paired rows
    for i, j, kind in sorted(pairs):
        issues = compare_fields(labels[i], preds[j], lkeys[i])
        if kind != "exact":  # pairing itself is uncertain: show field issues, don't count them
            issues, status = [f"review_{kind}"] + issues, "review"
            s["review"] += 1
        else:
            for x in issues:
                if x in s:
                    s[x] += 1
            status = ("critical" if any(x in CRITICAL for x in issues) else
                      "review" if any(x.startswith("review_") for x in issues) else
                      "miss" if issues else "correct")
            if status != "critical":
                s[{"review": "review", "miss": "miss_rows", "correct": "correct"}[status]] += 1
        s["row_status"][i] = status
        if status == "critical" and is_abnormal(labels[i]):
            s["abnormal_critical"] += 1
        if issues:
            s["details"].append({"label": labels[i], "pred": preds[j], "pairing": kind, "issues": issues,
                                 "status": status})
    for i in (i for i in range(len(labels)) if i not in used_l):
        s["dropped_row"] += 1
        s["miss_rows"] += 1
        s["details"].append({"label": labels[i], "issues": ["dropped_row"], "status": "miss"})
    for j in (j for j in range(len(preds)) if j not in used_p):
        s["invented_row"] += 1
        s["unpaired"] += 1
        s["details"].append({"pred": preds[j], "issues": ["invented_row"], "status": "critical", "note": "unpaired"})
    s["critical"] = sum(s[k] for k in CRITICAL)
    exact = sorted((j, i) for i, j, kind in pairs if kind == "exact")
    s["out_of_order"] = len(exact) - lis_len([i for _, i in exact])
    return s


# ---------------------------------------------------------------- scoring a run

def load_labels(rid, labels_dir):
    p = ROOT / labels_dir / f"report_{rid}.json"
    return json.loads(p.read_text(encoding="utf-8"))["tests"] if p.exists() else None


def cost_of(usage):
    if not usage or usage.get("model") not in PRICES:
        return None
    pin, pout = PRICES[usage["model"]]
    out = (usage.get("output_tokens") or 0) + (usage.get("thinking_tokens") or 0)
    return ((usage.get("prompt_tokens") or 0) * pin + out * pout) / 1e6


def summarise(values):
    values = [v for v in values if v is not None]
    if not values:
        return "n/a"
    return f"{statistics.mean(values):.4g} (min {min(values):.4g}, max {max(values):.4g})"


def load_run(run_dir, labels_dir="labels"):
    """Score every repeat in a run dir. Returns (per_repeat [{rid: score}], metas, labels by rid)."""
    run_dir = Path(run_dir)
    per_repeat, metas, all_labels = [], [], {}
    for rep in sorted(p for p in run_dir.iterdir() if p.is_dir() and re.fullmatch(r"r\d+", p.name)):
        scores = {}
        for meta_path in sorted(rep.glob("report_*.meta.json")):
            rid = meta_path.name[7:9]
            labels = load_labels(rid, labels_dir)
            if labels is None:
                continue
            all_labels[rid] = labels
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            metas.append(meta)
            out_path = rep / f"report_{rid}.json"
            ok = meta.get("status") == "ok" and out_path.exists()
            output = json.loads(out_path.read_text(encoding="utf-8")) if ok else None
            scores[rid] = score_report(labels, output, None if ok else meta.get("status", "no output"))
        per_repeat.append(scores)
    return per_repeat, metas, all_labels


def provenance():
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "eval.py", "eval_vocab.json", "labels"],
                                    cwd=ROOT, capture_output=True, text=True).stdout.strip())
    except OSError:
        commit, dirty = None, None
    return {"git_commit": commit, "eval_files_uncommitted": dirty,
            "vocab_sha256": hashlib.sha256(VOCAB_PATH.read_bytes()).hexdigest()}


def score_run(run_dir, labels_dir="labels"):
    run_dir = Path(run_dir)
    per_repeat, metas, _ = load_run(run_dir, labels_dir)
    lines = [f"# Score: {run_dir.name} (labels: {labels_dir}/, {len(per_repeat)} repeats)", "",
             "## Per report (mean over repeats)", "",
             "| report | rate | " + " | ".join(COLS) + " | failed |", "|" + "---|" * (len(COLS) + 3)]
    for rid in sorted({r for sc in per_repeat for r in sc}):
        rs = [sc[rid] for sc in per_repeat if rid in sc]
        mean = {c: statistics.mean(r[c] for r in rs) for c in COLS}
        rate = f"{100 * mean['correct'] / mean['rows']:.1f}%" if mean["rows"] else "n/a"
        lines.append(f"| {rid} | {rate} | " + " | ".join(f"{mean[c]:g}" for c in COLS)
                     + f" | {sum(1 for r in rs if r['failed'])}/{len(rs)} |")

    totals = []
    for sc in per_repeat:
        t = {c: sum(r[c] for r in sc.values()) for c in COLS}
        macro = [r["correct"] / r["rows"] for r in sc.values() if r["rows"]]
        t.update(failed=sum(1 for r in sc.values() if r["failed"]),
                 rate=t["correct"] / t["rows"] if t["rows"] else None,
                 macro_rate=statistics.mean(macro) if macro else None)
        totals.append(t)
    lines += ["", "## Headline (per repeat: mean, min, max)", "",
              f"- **Correct-row rate (pooled):** {summarise([t['rate'] for t in totals])}",
              f"- **Critical errors:** {summarise([t['critical'] for t in totals])}",
              f"- Critical errors on abnormal rows: {summarise([t['abnormal_critical'] for t in totals])} "
              f"(of {totals[0]['abnormal_rows'] if totals else 0} abnormal rows)",
              f"- Correct-row rate (mean of reports): {summarise([t['macro_rate'] for t in totals])}",
              f"- Miss rows: {summarise([t['miss_rows'] for t in totals])} | "
              f"Review rows: {summarise([t['review'] for t in totals])} | "
              f"Failed reports: {summarise([t['failed'] for t in totals])}"]
    lines += [f"  - {k}: {summarise([t[k] for t in totals])}" for k in CRITICAL + MISS]

    attempts = [a for m in metas for a in m.get("attempts", [])]
    errors = {}
    for a in attempts:
        if a.get("error"):
            errors[a["error"]] = errors.get(a["error"], 0) + 1
    inner = {}
    for a in attempts:
        for reason in a.get("extractor_retries", []):
            inner[reason] = inner.get(reason, 0) + 1
    lines += ["", "## Reliability (separate from accuracy)", "",
              f"- Report runs: {len(metas)} | runner attempts: {len(attempts)} | runner retries: "
              f"{len(attempts) - len(metas)} | failed report runs: {sum(1 for m in metas if m.get('status') != 'ok')}",
              f"- Errors seen by the runner: {errors or 'none'}",
              f"- Retries inside the extractor: {sum(inner.values())} {inner or ''}"]

    known = [c for c in (cost_of(m.get("usage")) for m in metas) if c is not None]
    walls = [m["wall_s"] for m in metas if m.get("status") == "ok" and m.get("wall_s") is not None]
    tok = lambda k: [m["usage"].get(k) for m in metas if m.get("usage")]
    lines += ["", "## Cost and latency (per report)", ""]
    if known:
        lines += [f"- **$ per report:** mean ${statistics.mean(known):.6f}, max ${max(known):.6f} "
                  f"({len(known)}/{len(metas)} runs with usage)",
                  f"- $ per 10k reports/day: ${statistics.mean(known) * 10_000:.2f}",
                  f"- Tokens per report: prompt {summarise(tok('prompt_tokens'))}, output "
                  f"{summarise(tok('output_tokens'))}, thinking {summarise(tok('thinking_tokens'))}"]
    else:
        lines.append("- $ per report: n/a (extractor did not log usage)")
    if walls:
        lines.append(f"- Latency of successful call: median {statistics.median(walls):.1f}s, max {max(walls):.1f}s; "
                     f"including retries: max {max(m.get('total_wall_s') or 0 for m in metas):.1f}s")
    reviews = [(rid, d) for rid, r in (per_repeat[0] if per_repeat else {}).items()
               for d in r["details"] if d.get("status") == "review"]
    if reviews:
        lines += ["", "## Needs review (repeat 1)", ""]
        lines += [f"- report_{rid}: {d['issues']} label={d.get('label', {}).get('test_name')!r} "
                  f"pred={d.get('pred', {}).get('test_name')!r}" for rid, d in reviews]
    report = "\n".join(lines) + "\n"
    (run_dir / "score.md").write_text(report, encoding="utf-8")
    (run_dir / "score.json").write_text(json.dumps(
        {"labels": labels_dir, **provenance(), "repeats": per_repeat, "totals": totals},
        indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return report, per_repeat, totals


def diff_runs(run_a, run_b, labels_dir="labels"):
    """Per label row: fixed / broken / unstable between two runs, using every repeat."""
    a, _, labels = load_run(run_a, labels_dir)
    b, _, _ = load_run(run_b, labels_dir)
    groups = {"fixed": [], "broken": [], "unstable": [], "still_correct": [], "still_wrong": []}
    for rid in sorted(set().union(*a) & set().union(*b)):
        for i, lab in enumerate(labels[rid]):
            sa = [sc[rid]["row_status"][i] == "correct" for sc in a if rid in sc]
            sb = [sc[rid]["row_status"][i] == "correct" for sc in b if rid in sc]
            if len(set(sa)) > 1 or len(set(sb)) > 1:
                g = "unstable"
            else:
                g = {(False, True): "fixed", (True, False): "broken",
                     (True, True): "still_correct", (False, False): "still_wrong"}[(sa[0], sb[0])]
            groups[g].append(f"report_{rid} {lab['test_name']} (A {sum(sa)}/{len(sa)}, B {sum(sb)}/{len(sb)} correct)")
    invented = lambda runs: statistics.mean(sum(r["invented_row"] for r in sc.values()) for sc in runs)
    lines = [f"# Diff: {Path(run_a).name} -> {Path(run_b).name}", "",
             " | ".join(f"{g}: {len(v)}" for g, v in groups.items()),
             f"Invented rows (mean per repeat): A {invented(a):g}, B {invented(b):g}"]
    for g in ("fixed", "broken", "unstable"):
        if groups[g]:
            lines += ["", f"## {g}"] + [f"- {x}" for x in groups[g]]
    return "\n".join(lines) + "\n", groups


# ---------------------------------------------------------------- running the extractor

RETRYABLE = {"timeout", "http_429", "http_5xx", "connection"}


def classify(stderr):
    low = stderr.lower()
    for error, hit in (("quota_day", "perday" in low or "per day" in low), ("http_429", "429" in low),
                       ("http_5xx", re.search(r"http 5\d\d", low)), ("timeout", "timed out" in low or "timeout" in low),
                       ("connection", "connection" in low)):
        if hit:
            return error
    return "crash"


def parse_usage(stderr):
    for line in stderr.splitlines():
        if line.startswith("USAGE "):
            try:
                return json.loads(line[6:])
            except ValueError:
                pass
    return None


def parse_retries(stderr):
    """Retries the extractor did itself ('RETRY {...}' lines on stderr), so they still show in reliability."""
    out = []
    for line in stderr.splitlines():
        if line.startswith("RETRY "):
            try:
                out.append(json.loads(line[6:]).get("reason", "unknown"))
            except ValueError:
                out.append("unknown")
    return out


class Pacer:
    """Keeps our request counts under free-tier limits, using a ledger shared across runs.
    Tokens-per-minute isn't paced: one call is ~2k tokens, far under any TPM limit at our RPM."""

    def __init__(self, ledger, rpm, rpd, gap):
        self.ledger, self.rpm, self.rpd, self.gap = Path(ledger), rpm, rpd, gap

    def stamps(self):
        return [float(x) for x in self.ledger.read_text().split()] if self.ledger.exists() else []

    def counts(self):
        now, st = time.time(), self.stamps()
        return {w: sum(now - t < secs for t in st) for w, secs in (("minute", 60), ("hour", 3600), ("day", 86400))}

    def wait(self):
        """Block until a call is allowed. Returns False when the daily budget is used up."""
        while True:
            c, st = self.counts(), self.stamps()
            if c["day"] >= self.rpd:
                return False
            if c["minute"] < self.rpm and time.time() - max(st, default=0) >= self.gap:
                return True
            time.sleep(1)

    def record(self):
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a") as f:
            f.write(f"{time.time()}\n")


def run_one(extractor, report, env, timeout, backoff, pacer):
    """Run the extractor on one report with retries. Returns (stdout or None, meta)."""
    meta = {"report": report.name, "model": env.get("GEMINI_MODEL"), "attempts": [], "status": None}
    start, stdout = time.time(), None
    for n in range(len(backoff) + 1):
        if not pacer.wait():
            meta.update(status="quota_stop: local daily budget reached", quota_stop=True)
            break
        t = time.time()
        pacer.record()
        try:
            p = subprocess.run([sys.executable, str(extractor), str(report)], capture_output=True,
                               timeout=timeout, env=env)
            out, err, code = p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"), p.returncode
        except subprocess.TimeoutExpired:
            out, err, code = "", f"runner timeout after {timeout}s", None
        att = {"n": n + 1, "wall_s": round(time.time() - t, 2), "exit": code,
               "error": "timeout" if code is None else classify(err) if code else None,
               "extractor_retries": parse_retries(err)}
        if att["error"] is None:
            try:
                json.loads(out)
            except ValueError:
                att["error"] = "invalid_json"
        meta["usage"] = parse_usage(err) or meta.get("usage")
        if att["error"]:
            att["stderr_tail"] = err.strip()[-300:]
        meta["attempts"].append(att)
        if not att["error"]:
            meta.update(status="ok", wall_s=att["wall_s"])
            stdout = out
            break
        last = n == len(backoff)
        if att["error"] == "quota_day" or (last and att["error"] == "http_429"):
            # a 429 that survives the whole backoff (>1 min) is most likely the daily quota
            meta.update(status=f"quota_stop: {att['error']} after {n + 1} attempt(s)", quota_stop=True)
            break
        if att["error"] not in RETRYABLE or last:
            meta["status"] = f"failed: {att['error']} after {n + 1} attempt(s)"
            break
        time.sleep(backoff[n])
    meta["total_wall_s"] = round(time.time() - start, 2)
    meta["counts_after"] = pacer.counts()
    return stdout, meta


def report_path(rid):
    hits = sorted((ROOT / "reports").glob(f"report_{rid}.*"))
    if not hits:
        raise SystemExit(f"no report file for {rid}")
    return hits[0]


def run(args):
    env = dict(os.environ)
    if (ROOT / ".env").exists():  # keeps the one-command contract; the key never leaves this process tree
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                env.setdefault(*(x.strip() for x in line.split("=", 1)))
    if args.model:
        env["GEMINI_MODEL"] = args.model
    env["PYTHONIOENCODING"] = "utf-8"  # Windows pipes default to cp1252 and mangle µ; Linux is UTF-8 already
    pacer = Pacer(ROOT / "runs" / ".api_calls.log", args.rpm, args.rpd, args.gap)
    backoff = [float(x) for x in args.backoff.split(",")] if args.backoff else []
    out = ROOT / "runs" / args.tag
    for rep in range(1, args.repeats + 1):
        d = out / f"r{rep}"
        d.mkdir(parents=True, exist_ok=True)
        for rid in args.reports.split(",") if args.reports else TUNING:
            stdout, meta = run_one(Path(args.extractor), report_path(rid), env, args.timeout, backoff, pacer)
            if stdout is not None:
                (d / f"report_{rid}.json").write_text(stdout, encoding="utf-8")
            (d / f"report_{rid}.meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
            print(f"r{rep} report_{rid}: {meta['status']} ({meta['total_wall_s']}s, "
                  f"{len(meta['attempts'])} attempt(s))", file=sys.stderr)
            if meta.get("quota_stop"):
                print("Stopping: quota reached. Outputs so far are saved.", file=sys.stderr)
                return print(score_run(out, args.labels)[0])
    print(score_run(out, args.labels)[0])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--extractor", default="extract.py")
    r.add_argument("--tag", required=True)
    r.add_argument("--repeats", type=int, default=3)
    r.add_argument("--reports", help="comma list, e.g. 01,02. Default: the 8 tuning reports. "
                                     "Held-out 04,07,10,12 run only when listed here.")
    r.add_argument("--model", help="sets GEMINI_MODEL for the extractor")
    r.add_argument("--timeout", type=float, default=330,
                   help="seconds before the runner kills one extractor run; above extract.py's own 300 s cap")
    r.add_argument("--backoff", default="10,30,60", help="seconds to wait before each retry")
    r.add_argument("--rpm", type=int, default=10)
    r.add_argument("--rpd", type=int, default=400)
    r.add_argument("--gap", type=float, default=4, help="minimum seconds between calls")
    r.add_argument("--labels", default="labels")
    s = sub.add_parser("score")
    s.add_argument("run_dir")
    s.add_argument("--labels", default="labels")
    d = sub.add_parser("diff")
    d.add_argument("run_a")
    d.add_argument("run_b")
    d.add_argument("--labels", default="labels")
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace")  # Windows consoles can't print every label character
    if args.cmd == "run":
        run(args)
    elif args.cmd == "score":
        print(score_run(args.run_dir, args.labels)[0])
    else:
        print(diff_runs(args.run_a, args.run_b, args.labels)[0])


if __name__ == "__main__":
    main()
