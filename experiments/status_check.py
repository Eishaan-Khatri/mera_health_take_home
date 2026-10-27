"""Compare each output row's status with the status implied by the label's own value and printed range.
Expected status comes from labels/ via extract.compute_status (null when no range or a non-numeric value).
Usage: python experiments/status_check.py <run_tag> [<run_tag> ...]   (from the project root)"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(errors="replace")
import eval as ev
from extract import compute_status

for tag in sys.argv[1:]:
    c, examples = Counter(), []
    for rep in sorted(Path("runs", tag).glob("r*")):
        for out_path in sorted(rep.glob("report_*.json")):
            if len(out_path.name) != len("report_01.json"):  # skip .meta.json / .meta.failed.json
                continue
            rid = out_path.name[7:9]
            labels = ev.load_labels(rid, "labels")
            preds = json.loads(out_path.read_text(encoding="utf-8"))["tests"]
            used = set()
            for lab in labels:
                key = ev.name_key(lab["test_name"])
                j = next((j for j, p in enumerate(preds) if j not in used and
                          (ev.name_key(p["test_name"]) == key or ev.urine_base(p["test_name"]) == key)), None)
                if j is None:
                    c["row not found"] += 1
                    continue
                used.add(j)
                want, got = compute_status(lab["value"], lab["reference_range"]), preds[j].get("status")
                if want == got:
                    c["agree"] += 1
                elif want is None:
                    c["status given where none can be computed"] += 1
                    examples.append((rid, lab["test_name"], lab["value"], lab["reference_range"], got, want))
                else:
                    c["wrong status"] += 1
                    examples.append((rid, lab["test_name"], lab["value"], lab["reference_range"], got, want))
    print(f"\n{tag}: {dict(c)}")
    for e in sorted(set(examples)):
        print(f"   report_{e[0]} {e[1]!r}: value {e[2]!r}, printed range {e[3]!r} -> status {e[4]!r} (expected {e[5]!r})")
