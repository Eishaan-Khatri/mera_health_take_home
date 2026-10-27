"""Write ablation variants of the frozen extract.py: each one undoes exactly one fix.

Usage: python experiments/make_variants.py   -> experiments/variants/extract_<name>.py

extract.py itself is never edited. Each patch must match the frozen file exactly once, so a
variant can't silently drift from what it claims to undo.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "variants"

PATCHES = {
    # fix 1: only the first PDF page is rendered (pdftoppm -f 1 -l 1), as in the baseline
    "no_all_pages": [
        ('["pdftoppm", "-r", str(DPI),', '["pdftoppm", "-f", "1", "-l", "1", "-r", str(DPI),'),
    ],
    # fix 2: value forced to a number again (baseline prompt rule, example and float() coercion)
    "no_values_as_printed": [
        ('"value": "...", "unit"', '"value": 0.0, "unit"'),
        ("- value is a string, copied exactly as printed: keep words (e.g. Negative), symbols (e.g. < or >) "
         "and ranges (e.g. 2-3) as they appear.", "- value must be a number."),
        ('value, reference_range = as_printed(t.get("value")),', 'value, reference_range = to_number(t.get("value")),'),
        ("def clean(tests: list[dict]) -> list[dict]:",
         "def to_number(value):\n    try:\n        return float(value)\n    except (TypeError, ValueError):\n"
         "        return None\n\n\ndef clean(tests: list[dict]) -> list[dict]:"),
    ],
    # fix 3: the model is told to fill in a standard range again
    "no_range_rule": [
        ("- reference_range is copied as printed for that test. If the report prints no range for it, use null. "
         "Never fill in a standard range.",
         "- If a reference range is missing from the report, fill in the standard reference range for that test."),
    ],
    # fixes 4-6 (status): the model computes status again, as in the baseline
    "no_status_in_code": [
        ('"reference_range": "..."}]}', '"reference_range": "...", "status": "normal"}]}'),
        ("- Be thorough. Do not miss any tests.",
         '- status is "normal", "high" or "low", based on the value and the reference range.\n'
         "- Be thorough. Do not miss any tests."),
        ('"status": compute_status(value, reference_range),', '"status": t.get("status"),'),
    ],
    # not an ablation: same code at 150 DPI, to check whether 60 DPI hurts on degraded copies
    "dpi150": [
        ("DPI = 60\n", "DPI = 150\n"),
    ],
}


def main():
    src = (ROOT / "extract.py").read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, patches in PATCHES.items():
        text = src
        for old, new in patches:
            n = text.count(old)
            if n != 1:
                raise SystemExit(f"{name}: expected 1 match, found {n}: {old[:60]!r}")
            text = text.replace(old, new)
        (OUT / f"extract_{name}.py").write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote experiments/variants/extract_{name}.py ({len(patches)} change(s))")


if __name__ == "__main__":
    main()
