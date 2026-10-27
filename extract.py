"""Extract structured lab results from a lab report.

Usage:
    python extract.py reports/report_01.pdf

Prints JSON matching schema.json to stdout.
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
DPI = 60

PROMPT = """You are an expert at reading medical lab reports.

Look at this lab report and extract every test result from it.

Return JSON in exactly this format:
{"tests": [{"test_name": "...", "value": "...", "unit": "...", "reference_range": "..."}]}

Rules:
- Use the standard medical name for each test.
- value is a string, copied exactly as printed: keep words (e.g. Negative), symbols (e.g. < or >) and ranges (e.g. 2-3) as they appear.
- reference_range is copied as printed for that test. If the report prints no range for it, use null. Never fill in a standard range.
- Be thorough. Do not miss any tests.
"""

MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
RETRY_CODES = {429, 500, 502, 503, 504}  # rate limit and server overload: worth waiting for
BACKOFF = (5, 15, 45)  # seconds before each retry
# Measured on 144 successful calls: median 12 s, p95 73 s, max 169 s; 2% took over 90 s.
READ_TIMEOUT_S = 90  # per request; a slower call is retried rather than waited on
TOTAL_BUDGET_S = 300  # whole run, retries and waits included
MIN_ATTEMPT_S = 20  # don't start a request with less time than this left
START = time.monotonic()


def retry_after(error):
    """Seconds the server asked us to wait (Retry-After), capped at a minute; None if it didn't say."""
    value = error.headers.get("Retry-After", "") if error.headers else ""
    return min(int(value), 60) if value.isdigit() else None


def load_images(path: Path) -> list[tuple[str, str]]:
    """Return (media_type, base64 data) for every page of the report, in page order."""
    if path.suffix.lower() == ".pdf":
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "page"
            try:
                subprocess.run(["pdftoppm", "-r", str(DPI), "-png", str(path), str(prefix)],
                               check=True, capture_output=True)
            except FileNotFoundError:
                raise RuntimeError("Install Poppler (pdftoppm); see README.md.") from None
            except subprocess.CalledProcessError as error:
                raise RuntimeError(f"pdftoppm could not render {path}: "
                                   f"{error.stderr.decode(errors='replace').strip()[:200]}") from None
            # pdftoppm zero-pads page numbers, so name order is page order
            pages = sorted(Path(directory).glob("page*.png"))
            return [("image/png", base64.standard_b64encode(p.read_bytes()).decode()) for p in pages]
    if path.suffix.lower() not in MEDIA_TYPES:
        raise RuntimeError(f"Unsupported file type {path.suffix!r}; expected .pdf, .jpg, .jpeg or .png.")
    if not path.is_file():
        raise RuntimeError(f"No such file: {path}")
    return [(MEDIA_TYPES[path.suffix.lower()], base64.standard_b64encode(path.read_bytes()).decode())]


def call_model(images: list[tuple[str, str]]) -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Set GEMINI_API_KEY; see README.md. No API call made.")
    body = {
        "contents": [{"role": "user", "parts": [
            *({"inlineData": {"mimeType": media_type, "data": data}} for media_type, data in images),
            {"text": PROMPT},
        ]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 16000},
    }
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(), headers={"x-goog-api-key": key, "Content-Type": "application/json"},
    )
    deadline = START + TOTAL_BUDGET_S
    for attempt in range(len(BACKOFF) + 1):
        timeout = min(READ_TIMEOUT_S, deadline - time.monotonic())
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.load(response)
            break
        except urllib.error.HTTPError as error:
            if error.code not in RETRY_CODES:
                raise RuntimeError(f"Gemini HTTP {error.code}; check API access, model and quota. "
                                   "See README.md.") from None
            reason, what = f"http_{error.code}", f"HTTP {error.code}"
            wait = retry_after(error) or BACKOFF[min(attempt, len(BACKOFF) - 1)]
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            timed_out = isinstance(error, TimeoutError) or "timed out" in str(error)
            reason, what = ("timeout", "request timed out") if timed_out else ("connection", "connection failed")
            wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
        out_of_time = time.monotonic() + wait + MIN_ATTEMPT_S > deadline
        if attempt == len(BACKOFF) or out_of_time:
            why = f"time budget of {TOTAL_BUDGET_S} s used" if out_of_time else "retries used up"
            raise RuntimeError(f"Gemini {what} on attempt {attempt + 1}; gave up ({why}). "
                               "Check API access, network and quota. See README.md.") from None
        print("RETRY " + json.dumps({"attempt": attempt + 1, "reason": reason, "wait_s": wait}), file=sys.stderr)
        time.sleep(wait)
    usage = result.get("usageMetadata", {})
    print("USAGE " + json.dumps({"model": MODEL, "prompt_tokens": usage.get("promptTokenCount"),
                                 "output_tokens": usage.get("candidatesTokenCount"),
                                 "thinking_tokens": usage.get("thoughtsTokenCount"),
                                 "total_tokens": usage.get("totalTokenCount")}), file=sys.stderr)
    candidate = result.get("candidates", [{}])[0]
    return "".join(part["text"] for part in candidate.get("content", {}).get("parts", [])
                   if "text" in part and not part.get("thought"))


def parse(text: str) -> list[dict]:
    """The model's 'tests' list. Raises instead of returning [], so a broken reply never looks like 'no tests'."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        tests = json.loads(match.group(0))["tests"]
    except (AttributeError, ValueError, KeyError, TypeError):
        tests = None
    if not isinstance(tests, list):
        raise RuntimeError(f"Model reply had no valid JSON 'tests' list; not reporting it as zero tests. "
                           f"Reply started: {text[:200]!r}")
    return tests


def as_printed(value):
    """Keep the value as read; the schema allows strings, so text like "Negative" or "< 0.5" survives."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return str(value).strip()


NUMBER = r"\d[\d,]*(?:\.\d+)?"


def to_float(text):
    return float(text.replace(",", ""))


def value_span(value):
    """(low, high) for a plain number ("13.5" -> (13.5, 13.5)) or an interval ("8-10" -> (8, 10)); else None."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value), float(value)
    m = re.fullmatch(rf"({NUMBER})(?:\s*[-–]\s*({NUMBER}))?", str(value or "").strip())
    if not m:
        return None  # text like "Negative" or comparators like "< 0.5"
    return to_float(m.group(1)), to_float(m.group(2) or m.group(1))


def as_words(text):
    """Lower-cased words of a value or range, without a trailing unit such as '/hpf'."""
    return " ".join(re.sub(r"\s*/\S+$", "", str(text)).lower().split())


def compute_status(value, reference_range):
    """'low' / 'normal' / 'high' from the value and the printed range. Bounds count as normal.
    A word range (Negative, Nil, Absent, Pale Yellow): 'normal' if the value matches it, else 'review',
    since code can't tell how far off 'Present (+)' or '1-2' is.
    None when there is no value or range, or an interval straddles a bound (4-6 vs 0 - 5)."""
    if value is None or reference_range is None:
        return None
    rng = str(reference_range).strip()
    if not re.search(r"\d", rng):
        return "normal" if as_words(value) == as_words(rng) else "review"
    span = value_span(value)
    if span is None:
        return None
    vlo, vhi = span
    m = re.match(rf"({NUMBER})\s*[-–]\s*({NUMBER})", rng)
    if m:
        lo, hi = to_float(m.group(1)), to_float(m.group(2))
        return ("low" if vhi < lo else "high" if vlo > hi else
                "normal" if lo <= vlo and vhi <= hi else None)
    m = re.match(rf"(<=|>=|<|>|≤|≥)\s*({NUMBER})", rng)
    if m:
        op, bound = m.group(1), to_float(m.group(2))
        if op == "<":
            return "normal" if vhi < bound else "high" if vlo >= bound else None
        if op in ("<=", "≤"):
            return "normal" if vhi <= bound else "high" if vlo > bound else None
        if op == ">":
            return "normal" if vlo > bound else "low" if vhi <= bound else None
        return "normal" if vlo >= bound else "low" if vhi < bound else None
    return None


def clean(tests: list[dict]) -> list[dict]:
    out = []
    for t in tests:
        value, reference_range = as_printed(t.get("value")), t.get("reference_range") or None
        out.append({
            "test_name": str(t.get("test_name", "")).strip(),
            "value": value,
            "unit": t.get("unit") or None,
            "reference_range": reference_range,
            "status": compute_status(value, reference_range),
        })
    return out


def extract(path: Path) -> dict:
    return {"tests": clean(parse(call_model(load_images(path))))}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    try:
        print(json.dumps(extract(Path(sys.argv[1])), indent=2, ensure_ascii=False))
    except RuntimeError as error:
        # Still schema-valid JSON on stdout, but the error field and exit code 1 say it's a failure,
        # not a report with no tests.
        print(json.dumps({"tests": [], "error": str(error)}, indent=2, ensure_ascii=False))
        print(str(error), file=sys.stderr)
        sys.exit(1)
