# PLAN

## 1. How we're breaking this down

1. **API access first.** Smoke-test one call, note latency and the free-tier quota.
2. **Audit labels.** Compare every gold row to the report image. `gold/` stays untouched; documented fixes go in `labels/`. Hand-label the unlabelled reports (04, 07, 10, 12) **before** seeing any model output. report_12 looks like a prescription, so its expected output is an empty list.
3. **Build `eval.py` before touching `extract.py`.** Pair rows by normalised test name plus a synonym table, never by value. Severity: cosmetic (ignored) < missing row / null (bad, but visible) < wrong value, wrong unit scale, invented row or invented range (critical: misleads a doctor). Fix normalisation rules before scoring the baseline. Check every output against `schema.json`; a crash or silent `[]` counts as a failure. Test the eval by breaking labels on purpose. Tune on the 8 gold reports only; the 4 hand-labelled ones are held out as a stand-in for the unseen 6.
4. **Baseline.** Freeze a copy of the untouched extractor that only adds token-usage logging. Run 3 repeats; record recall, value accuracy, critical errors, cost/report and latency.
5. **Diagnose.** From baseline output, pick the three failure categories that matter most, each tied to a specific report and row and traced to a root cause.
6. **Improve one change at a time** and measure each (ablations). Compare runs per row (fixed vs broken), not only the headline number. Fixes must be general, not tuned to a sample.
7. **Report at least one thing that didn't help**, with numbers.
8. **Write up.** README (≤ 2 pages: eval, diagnosis, before/after with cost and latency, RAG / fine-tuning / agent answers, decision log), prompts with rationale, committed run outputs, transcripts.
9. **Out of scope unless the evidence demands it:** RAG, agents, frameworks, big rewrites.

## 2. What we expect to find

*Hypotheses from reading the code and reports. Not yet tested; some may be wrong.*

- `pdftoppm -f 1 -l 1` sends only page 1, so report_11 (2 pages) will lose rows.
- 60 DPI may cause misread digits, especially on scans and photos.
- "value must be a number" + `float()` will corrupt qualitative/interval values (`Negative`, `2-3`, `< 0.5`) and may fail on Indian formatting like `2,29,000`.
- "fill in the standard reference range" will invent ranges where none are printed (e.g. report_03).
- "Be thorough" may make the model invent tests from the prescription (report_12).
- "Use the standard medical name" may rename or merge printed rows.
- Two-column layouts (06, 10), units printed inside the range cell, and the handwriting/occlusion on report_07 may cause misplaced fields or invented rows.
- The model may "correct" printed values that are internally inconsistent (e.g. bilirubin totals in 02, 11) instead of transcribing them.
