"""Tests for eval.py. Run: python test_eval.py  (no API calls)."""
import copy
import hashlib
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import eval as ev

ALL = ev.TUNING + ev.HELD_OUT


def labels(rid):
    return ev.load_labels(rid, "labels")


def score(rid, tests):
    return ev.score_report(labels(rid), {"tests": tests})


def counts(s):
    keys = ("correct", "critical", "miss_rows", "review", "out_of_order", "unpaired", "duplicate",
            "abnormal_critical") + ev.CRITICAL + ev.MISS  # abnormal_rows is a property of the labels, not counted
    return {k: s[k] for k in keys if s[k]}


def find(tests, name):
    return next(i for i, t in enumerate(tests) if t["test_name"] == name)


class Normalisation(unittest.TestCase):
    def test_values(self):
        q = ev.norm_quantity
        self.assertEqual(q("2,29,000"), q(229000))
        self.assertEqual(q("1.020"), q(1.02))
        self.assertEqual(q("340000"), q(340000.0))
        self.assertNotEqual(q("< 0.5"), q("0.5"))
        self.assertEqual(q("< 0.5"), q("<0.5"))
        self.assertNotEqual(q("Nil"), q("Negative"))
        self.assertEqual(q("Negative"), q("negative"))
        self.assertEqual(q("2-3"), q("2 - 3"))
        self.assertEqual(q("Present (+)"), q("present(+)"))
        self.assertIsNone(q(""))
        self.assertIsNone(q(None))

    def test_ranges(self):
        q = ev.norm_quantity
        self.assertEqual(q("1-6"), q("1 - 6"))
        self.assertEqual(q("13.0 - 17.0"), q("13 - 17"))
        self.assertEqual(q("1,50,000 - 4,10,000"), q("150000 - 410000"))
        self.assertNotEqual(q("< 200"), q("> 200"))

    def test_unit_buckets(self):
        b = ev.unit_bucket
        self.assertEqual(b("mill/cumm"), b("million/µL"))
        self.assertEqual(b("µg/dL"), b("ug/dL"))
        self.assertEqual(b("µg/dL"), b("mcg/dL"))
        self.assertEqual(b("µIU/mL"), b("mIU/L"))
        self.assertEqual(b("/cumm"), b("/µL"))
        self.assertEqual(b("U/L"), b("IU/L"))
        self.assertNotEqual(b("lakh/cumm"), b("/cumm"))
        self.assertNotEqual(b("mmol/L"), b("mEq/L"))
        self.assertIsNone(b("furlongs"))

    def test_meq_only_for_electrolytes(self):
        lab = {"value": "140", "unit": "mmol/L", "reference_range": "136 - 146"}
        pred = dict(lab, unit="mEq/L")
        self.assertEqual(ev.compare_fields(lab, pred, "sodium"), [])
        self.assertEqual(ev.compare_fields(lab, pred, "glucose_fasting"), ["wrong_unit"])

    def test_unit_inside_range(self):
        self.assertEqual(ev.split_unit(None, "0 - 5 /hpf"), ("/hpf", "0 - 5"))
        self.assertEqual(ev.split_unit(None, "Nil /hpf"), ("/hpf", "Nil"))
        self.assertEqual(ev.split_unit(None, "0 - 15 mm/hr"), ("mm/hr", "0 - 15"))
        self.assertEqual(ev.split_unit("/hpf", "0 - 5 /hpf"), ("/hpf", "0 - 5"))
        self.assertEqual(ev.split_unit(None, "Pale Yellow"), (None, "Pale Yellow"))
        self.assertEqual(ev.split_unit(None, "< 5.0"), (None, "< 5.0"))

    def test_names(self):
        k = ev.name_key
        self.assertEqual(k("MCV"), k("Mean Corpuscular Volume"))
        self.assertEqual(k("Haemoglobin"), k("Hemoglobin (Hb)"))
        self.assertEqual(k("TG"), k("Serum Triglycerides"))
        self.assertEqual(k("S. Urea"), k("Urea"))
        self.assertEqual(k("Total WBC Count"), k("Total Leucocyte Count"))
        self.assertEqual(k("Glycated Hb"), k("Glycosylated Haemoglobin (HbA1c)"))

    def test_filler_word_collisions(self):
        k = ev.name_key
        self.assertNotEqual(k("Total RBC Count"), k("RBC"))
        self.assertNotEqual(k("Protein Total"), k("Urine Protein"))
        self.assertNotEqual(k("Pus Cells (WBC)"), k("Total WBC Count"))
        self.assertNotEqual(k("Glucose - Fasting"), k("Urine Glucose"))


class PerfectPrediction(unittest.TestCase):
    def test_labels_as_prediction_score_perfect(self):
        for rid in ALL:
            with self.subTest(report=rid):
                lab = labels(rid)
                s = score(rid, copy.deepcopy(lab))
                self.assertIsNone(s["failed"])
                self.assertEqual(counts(s), {"correct": len(lab)} if lab else {})

    def test_report_12_empty_is_correct(self):
        s = score("12", [])
        self.assertIsNone(s["failed"])
        self.assertEqual(s["critical"], 0)

    def test_cosmetic_variants_stay_correct(self):
        t = copy.deepcopy(labels("09"))
        t[find(t, "Mean Corpuscular Volume")]["test_name"] = "MCV"
        t[find(t, "RBC Count")]["unit"] = "million/µL"
        t[find(t, "Eosinophils")]["reference_range"] = "1-6"
        t[find(t, "Platelets")]["value"] = 229000
        t[find(t, "Platelets")]["reference_range"] = "150000 - 410000"
        s = score("09", t)
        self.assertEqual(counts(s), {"correct": 14})

    def test_unit_in_range_cell_is_cosmetic(self):
        t = copy.deepcopy(labels("06"))
        for r in t:
            if r["unit"] and r["reference_range"]:
                r["reference_range"] = f"{r['reference_range']} {r['unit']}"
                r["unit"] = None
        self.assertEqual(counts(score("06", t)), {"correct": 12})


class Mutations(unittest.TestCase):
    """Apply one change to a perfect prediction; exactly the expected counter must move."""

    def check(self, rid, mutate, expected):
        t = copy.deepcopy(labels(rid))
        mutate(t)
        got = counts(score(rid, t))
        self.assertEqual(got, expected)

    def test_wrong_value(self):
        self.check("01", lambda t: t[0].update(value="15.5"),
                   {"correct": 13, "critical": 1, "wrong_value": 1})

    def test_dropped_row(self):
        self.check("01", lambda t: t.pop(3), {"correct": 13, "miss_rows": 1, "dropped_row": 1})

    def test_invented_row(self):
        self.check("01", lambda t: t.append({"test_name": "Ferritin", "value": "80", "unit": "ng/mL",
                                             "reference_range": "30 - 400"}),
                   {"correct": 14, "critical": 1, "invented_row": 1, "unpaired": 1})

    def test_duplicate_row(self):
        self.check("01", lambda t: t.append(dict(t[0])),
                   {"correct": 14, "critical": 1, "invented_row": 1, "duplicate": 1})

    def test_invented_range(self):
        self.check("03", lambda t: t[find(t, "T3")].update(reference_range="80 - 200"),
                   {"correct": 7, "critical": 1, "invented_range": 1})

    def test_missing_range(self):
        self.check("01", lambda t: t[0].update(reference_range=None),
                   {"correct": 13, "miss_rows": 1, "missing_range": 1})

    def test_missing_unit(self):
        self.check("01", lambda t: t[0].update(unit=None), {"correct": 13, "miss_rows": 1, "missing_unit": 1})

    def test_null_value(self):
        self.check("01", lambda t: t[0].update(value=None), {"correct": 13, "miss_rows": 1, "null_value": 1})

    def test_wrong_unit_scale(self):
        self.check("01", lambda t: t[find(t, "Platelet Count")].update(unit="lakh/cumm"),
                   {"correct": 13, "critical": 1, "wrong_unit": 1})

    def test_wrong_range(self):
        self.check("01", lambda t: t[0].update(reference_range="12.0 - 15.0"),
                   {"correct": 13, "critical": 1, "wrong_range": 1})

    def test_comparator_dropped(self):
        self.check("06", lambda t: t[find(t, "CRP")].update(value="0.5"),
                   {"correct": 11, "critical": 1, "wrong_value": 1})

    def test_reorder_is_reported_not_scored(self):
        t = copy.deepcopy(labels("01"))
        t.reverse()
        s = score("01", t)
        self.assertEqual(s["correct"], 14)
        self.assertEqual(s["critical"], 0)
        self.assertGreater(s["out_of_order"], 0)

    def test_empty_output_is_failed_report(self):
        s = score("01", [])
        self.assertEqual(s["failed"], "empty_output")
        self.assertEqual(s["correct"], 0)
        self.assertEqual(s["dropped_row"], 14)

    def test_schema_invalid_is_failed_report(self):
        s = ev.score_report(labels("01"), {"tests": [{"test_name": "Hb", "value": 1}]})
        self.assertIn("missing", s["failed"])

    def test_crash_is_failed_report(self):
        s = ev.score_report(labels("01"), None, failure="failed: crash")
        self.assertEqual(s["failed"], "failed: crash")
        self.assertEqual(s["miss_rows"], 14)

    def test_invented_rows_on_prescription(self):
        s = score("12", [{"test_name": "Blood Pressure", "value": "133/81", "unit": "mmHg",
                          "reference_range": None}])
        self.assertEqual(counts(s), {"critical": 1, "invented_row": 1, "unpaired": 1})


class Collisions(unittest.TestCase):
    def test_report_11_has_no_cross_pairing(self):
        s = score("11", copy.deepcopy(labels("11")))
        self.assertEqual(counts(s), {"correct": 54})

    def test_swapped_blood_and_urine_rbc_values(self):
        t = copy.deepcopy(labels("11"))
        a, b = find(t, "RBC Count"), find(t, "RBC")
        t[a]["value"], t[b]["value"] = t[b]["value"], t[a]["value"]
        s = score("11", t)
        self.assertEqual(s["wrong_value"], 2)
        self.assertEqual(s["correct"], 52)

    def test_renamed_urine_rbc_into_collision_is_review(self):
        t = copy.deepcopy(labels("11"))
        t[find(t, "RBC")]["test_name"] = "RBC Count"
        s = score("11", t)
        self.assertGreaterEqual(s["review"], 1)
        self.assertEqual(s["critical"], 0)
        self.assertLess(s["correct"], 54)

    def test_bare_albumin_next_to_serum_albumin_is_review(self):
        t = copy.deepcopy(labels("11"))
        t[find(t, "Urine Protein")]["test_name"] = "Albumin"
        s = score("11", t)
        self.assertGreaterEqual(s["review"], 1)
        self.assertEqual(s["critical"], 0)

    def test_unknown_name_is_fuzzy_review_not_correct(self):
        t = copy.deepcopy(labels("02"))
        t[find(t, "Aspartate Aminotransferase")]["test_name"] = "Aspartate Aminotransferas"
        s = score("02", t)
        self.assertEqual(counts(s), {"correct": 15, "review": 1})

    def test_unknown_unit_is_review(self):
        t = copy.deepcopy(labels("01"))
        t[0]["unit"] = "gram per decilitre"
        s = score("01", t)
        self.assertEqual(counts(s), {"correct": 13, "review": 1})


class AmbiguousLabels(unittest.TestCase):
    """report_07 Serum Globulin is partly covered: accepts "3.1" or null, anything else is wrong."""

    def globulin(self, value):
        t = copy.deepcopy(labels("07"))
        t[find(t, "Serum Globulin")]["value"] = value
        return counts(score("07", t))

    def test_label_declares_accepted_values(self):
        row = labels("07")[find(labels("07"), "Serum Globulin")]
        self.assertEqual(row["accept_values"], ["3.1", None])

    def test_reading_accepted(self):
        self.assertEqual(self.globulin("3.1"), {"correct": 10})
        self.assertEqual(self.globulin(3.1), {"correct": 10})

    def test_null_accepted(self):
        self.assertEqual(self.globulin(None), {"correct": 10})

    def test_other_value_is_wrong(self):
        for v in ("3.4", "3.7", "3"):
            with self.subTest(value=v):
                self.assertEqual(self.globulin(v), {"correct": 9, "critical": 1, "wrong_value": 1})

    def test_rows_without_accept_values_still_penalise_null(self):
        t = copy.deepcopy(labels("07"))
        t[find(t, "Serum Albumin")]["value"] = None
        self.assertEqual(counts(score("07", t)), {"correct": 9, "miss_rows": 1, "null_value": 1})


class AbnormalRows(unittest.TestCase):
    def abnormal(self, rid):
        return [r["test_name"] for r in labels(rid) if ev.is_abnormal(r)]

    def test_numeric_ranges(self):
        self.assertEqual(self.abnormal("01"), ["Total RBC Count", "MCV", "Eosinophils"])
        self.assertIn("Cholesterol - HDL", self.abnormal("02"))         # 36 vs "> 40"
        self.assertNotIn("Cholesterol - Total", self.abnormal("02"))    # 179 vs "< 200"
        self.assertNotIn("Basophils", self.abnormal("09"))              # 2 vs "0 - 2", boundary is normal

    def test_text_and_interval_values(self):
        ab = self.abnormal("06")
        self.assertIn("Sugar", ab)            # Present (+) vs Negative
        self.assertIn("Erythrocytes", ab)     # 1-2 vs Nil
        self.assertNotIn("Leucocytes", ab)    # 2-3 vs 0 - 5
        self.assertIn("Pus Cells (WBC)", self.abnormal("11"))  # 8-10 vs 0 - 5

    def test_no_range_is_not_abnormal(self):
        self.assertNotIn("T3", self.abnormal("03"))

    def test_critical_on_abnormal_row_counted(self):
        t = copy.deepcopy(labels("01"))
        t[find(t, "MCV")]["value"] = "87.9"     # hides an abnormal result
        self.assertEqual(counts(score("01", t)),
                         {"correct": 13, "critical": 1, "wrong_value": 1, "abnormal_critical": 1})

    def test_critical_on_normal_row_not_counted_as_abnormal(self):
        t = copy.deepcopy(labels("01"))
        t[find(t, "Haemoglobin")]["value"] = "14.5"
        self.assertNotIn("abnormal_critical", counts(score("01", t)))


class Diff(unittest.TestCase):
    def make_run(self, root, name, per_repeat_values):
        """per_repeat_values: one {test_name: value} override dict per repeat, for report_01."""
        for k, overrides in enumerate(per_repeat_values, 1):
            d = root / name / f"r{k}"
            d.mkdir(parents=True)
            t = copy.deepcopy(labels("01"))
            for n, v in overrides.items():
                t[find(t, n)]["value"] = v
            (d / "report_01.json").write_text(json.dumps({"tests": t}))
            (d / "report_01.meta.json").write_text(json.dumps({"status": "ok", "attempts": [{}]}))
        return root / name

    def test_fixed_broken_unstable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self.make_run(root, "A", [{"MCV": "1", "MCH": "1"}, {"MCV": "1", "MCH": "1"}, {"MCV": "1", "MCH": "1"}])
            b = self.make_run(root, "B", [{"Haemoglobin": "1"}, {"Haemoglobin": "1", "MCH": "1"},
                                          {"Haemoglobin": "1"}])
            text, g = ev.diff_runs(a, b)
            name = lambda xs: [x.split(" (")[0] for x in xs]
            self.assertEqual(name(g["fixed"]), ["report_01 MCV"])
            self.assertEqual(name(g["broken"]), ["report_01 Haemoglobin"])
            self.assertEqual(name(g["unstable"]), ["report_01 MCH"])
            self.assertEqual(len(g["still_correct"]), 11)
            self.assertIn("A 0/3, B 3/3 correct", text)

    def test_failed_repeat_counts_as_not_correct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self.make_run(root, "A", [{}, {}, {}])
            b = self.make_run(root, "B", [{}, {}, {}])
            (b / "r2" / "report_01.meta.json").write_text(json.dumps({"status": "failed: crash", "attempts": [{}]}))
            _, g = ev.diff_runs(a, b)
            self.assertEqual(len(g["unstable"]), 14)


class GoldVsLabels(unittest.TestCase):
    def test_only_known_difference(self):
        diffs = {}
        for rid in ev.TUNING:
            gold = json.loads((ev.ROOT / "gold" / f"report_{rid}.json").read_text(encoding="utf-8"))
            s = ev.score_report(labels(rid), gold)
            if counts(s) != {"correct": len(labels(rid))}:
                diffs[rid] = (counts(s), [(d["label"]["test_name"], d["issues"]) for d in s["details"]])
        self.assertEqual(diffs, {"01": ({"correct": 13, "critical": 1, "wrong_value": 1},
                                         [("Platelet Count", ["wrong_value"])])})


FAKE = textwrap.dedent("""
    import json, os, sys
    state = os.environ["FAKE_STATE"]
    n = int(open(state).read()) if os.path.exists(state) else 0
    open(state, "w").write(str(n + 1))
    mode = os.environ["FAKE_MODE"]
    if mode == "429_then_ok" and n == 0:
        sys.exit("Gemini HTTP 429; check API access, model and quota. See README.md.")
    if mode == "per_day":
        sys.exit("Gemini HTTP 429 GenerateRequestsPerDayPerProjectPerModel")
    if mode == "crash":
        raise ValueError("boom")
    if mode == "micro":
        print(json.dumps({"tests": [{"test_name": "T4", "value": "10.9", "unit": "\u00b5g/dL",
                                     "reference_range": None}]}, ensure_ascii=False))
        sys.exit(0)
    if mode == "always_429":
        sys.exit("Gemini HTTP 429; check API access, model and quota.")
    print('USAGE {"model": "gemini-3.1-flash-lite", "prompt_tokens": 1000, "output_tokens": 200, '
          '"thinking_tokens": 100, "total_tokens": 1300}', file=sys.stderr)
    print(json.dumps({"tests": []}))
""")


class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.fake = d / "fake_extract.py"
        self.fake.write_text(FAKE, encoding="utf-8")
        self.pacer = ev.Pacer(d / "ledger.log", rpm=1000, rpd=1000, gap=0)
        self.env = dict(os.environ, FAKE_STATE=str(d / "state"))

    def tearDown(self):
        self.tmp.cleanup()

    def go(self, mode, backoff=(0, 0, 0)):
        env = dict(self.env, FAKE_MODE=mode)
        return ev.run_one(self.fake, ev.report_path("12"), env, 30, list(backoff), self.pacer)

    def test_retry_then_success_is_logged(self):
        out, meta = self.go("429_then_ok")
        self.assertEqual(meta["status"], "ok")
        self.assertEqual([a["error"] for a in meta["attempts"]], ["http_429", None])
        self.assertEqual(json.loads(out), {"tests": []})

    def test_micro_sign_survives_the_pipe(self):
        env = dict(self.env, FAKE_MODE="micro", PYTHONIOENCODING="utf-8")  # as run() sets it
        out, meta = ev.run_one(self.fake, ev.report_path("12"), env, 30, [], self.pacer)
        self.assertEqual(json.loads(out)["tests"][0]["unit"], "µg/dL")

    def test_run_sets_utf8_for_the_extractor(self):
        self.assertIn('env["PYTHONIOENCODING"] = "utf-8"', Path(ev.__file__).read_text(encoding="utf-8"))

    def test_usage_and_cost(self):
        _, meta = self.go("ok")
        self.assertEqual(meta["usage"]["prompt_tokens"], 1000)
        self.assertAlmostEqual(ev.cost_of(meta["usage"]), (1000 * 0.25 + 300 * 1.50) / 1e6)

    def test_daily_quota_stops(self):
        _, meta = self.go("per_day")
        self.assertTrue(meta["quota_stop"])
        self.assertEqual(len(meta["attempts"]), 1)

    def test_persistent_429_stops_after_backoff(self):
        _, meta = self.go("always_429")
        self.assertEqual(len(meta["attempts"]), 4)
        self.assertTrue(meta["quota_stop"])

    def test_crash_is_not_retried(self):
        out, meta = self.go("crash")
        self.assertIsNone(out)
        self.assertEqual(meta["status"], "failed: crash after 1 attempt(s)")
        self.assertEqual(len(meta["attempts"]), 1)

    def test_local_daily_budget(self):
        self.pacer.rpd = 0
        _, meta = self.go("ok")
        self.assertTrue(meta["quota_stop"])
        self.assertEqual(meta["attempts"], [])

    def test_score_run_end_to_end(self):
        run = Path(self.tmp.name) / "run"
        for rep in ("r1", "r2"):
            (run / rep).mkdir(parents=True)
            for rid in ("01", "12"):
                tests = copy.deepcopy(labels(rid))
                if rep == "r2" and rid == "01":
                    tests[0]["value"] = "99"
                (run / rep / f"report_{rid}.json").write_text(json.dumps({"tests": tests}))
                meta = {"status": "ok", "wall_s": 5.0, "total_wall_s": 5.0, "attempts": [{"n": 1, "error": None}],
                        "usage": {"model": "gemini-3.1-flash-lite", "prompt_tokens": 1000, "output_tokens": 300}}
                (run / rep / f"report_{rid}.meta.json").write_text(json.dumps(meta))
        text, per_repeat, totals = ev.score_run(run)
        self.assertEqual([t["correct"] for t in totals], [14, 13])
        self.assertEqual([t["critical"] for t in totals], [0, 1])
        self.assertIn("$ per report", text)
        self.assertIn("| review | out_of_order |", text)  # needs-review count per report is shown
        self.assertTrue((run / "score.md").exists())
        saved = json.loads((run / "score.json").read_text(encoding="utf-8"))
        self.assertRegex(saved["git_commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(saved["vocab_sha256"], hashlib.sha256(ev.VOCAB_PATH.read_bytes()).hexdigest())

    def test_held_out_not_in_default_set(self):
        self.assertFalse(set(ev.HELD_OUT) & set(ev.TUNING))
        self.assertEqual(sorted(ev.TUNING + ev.HELD_OUT), [f"{i:02d}" for i in range(1, 13)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
