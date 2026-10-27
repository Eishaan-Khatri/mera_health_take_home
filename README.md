# Lab report extraction: starter kit

Read the brief first. This file only covers what's in the kit and how to run it.

## Contents

- `extract.py`: the baseline extractor.
- `reports/`: 12 sample documents (`.pdf` and `.jpg`).
- `gold/`: labels for 8 of the 12, named after the report they belong to.
- `schema.json`: the output shape.

## Run it

Use Python 3.10 or newer and install Poppler, which provides `pdftoppm`:

- macOS: `brew install poppler`
- Ubuntu/Debian: `sudo apt-get install poppler-utils`

The supplied Gemini setup is one starting point. You can use free credits or adapt the starter to an accessible provider or a local open model; paid access is not required. If you change the model/provider to get started, measure the baseline with that setup before changing its extraction behavior, and document the substitution.

There are no Python package dependencies for the supplied setup. From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pdftoppm -v
python -c 'import getpass, os, subprocess, sys; env = os.environ.copy(); env["GEMINI_API_KEY"] = getpass.getpass("Gemini API key: "); sys.exit(subprocess.call([sys.executable, "extract.py", "reports/report_01.pdf"], env=env))'
```

The last command securely prompts for your key and runs one extraction as a setup smoke test. It makes an API call, which may incur charges depending on your account, and should print JSON containing a `tests` array. It does not save the key or put it in shell history. For repeated calls, set `GEMINI_API_KEY` through your usual local secret/environment setup; do not commit it.

The default model is `gemini-3.8-flash`. Google's [pricing page](https://ai.google.dev/gemini-api/docs/pricing) currently lists free-tier input and output for this model (checked 8 October 2026). You can start with a free-tier project and an API key from [Google AI Studio](https://aistudio.google.com/apikey). Check your project's [active rate limits](https://ai.google.dev/gemini-api/docs/rate-limits): quotas apply per project, and access and limits may change. A key on a paid project can incur charges. If access or quota is insufficient, use another model or provider and document your setup.

The baseline calls the Gemini REST API. You're free to change model (`GEMINI_MODEL`) or provider; record the exact choice with your measurements. Whatever you change, this must keep working and keep printing schema-valid JSON to stdout, because it's how we'll run your version on reports you haven't seen:

```bash
python extract.py <path-to-report>
```

If your version needs different setup (other packages, other environment variables), say so at the top of your README.

For setup errors: a missing `pdftoppm` means Poppler is not on `PATH`; HTTP 401/403 means check key/project access, 404 means check model availability, and 429 means check quota. For a connection/TLS error, check network access before retrying. Never disable TLS verification. Keep access troubleshooting within the timebox; document constraints and any alternative you use.

## Decision log

| # | When | Change | Why | Verified how |
|---|---|---|---|---|
| 1 | After the baseline run (`a78d9b5`), **before any extractor change** | **Eval name matching** (`872bbd7`): `Full Name (ABBR)` falls back to the abbreviation only when neither the whole name nor the full name is recognised; `Urine X` pairs only with a bare label `X`, never `Serum X`; `N/A`/`NA`/`-`/`none` as a unit means no unit. | The baseline prompt says "use the standard medical name", so it renames tests (MCV → `Mean Corpuscular Volume (MCV)`). The eval scored each rename as a dropped row **plus** an invented row, so the score measured naming, not extraction. A doctor cares whether the value is right, not what the row is called. I had predicted the renaming in `PLAN.md`. Fixing the eval before touching the extractor means the same eval scores the baseline and every fix, so comparisons stay fair. | 10 new tests: abbreviation only when the full name is unknown (`Pus Cells (WBC)` stays urine, never blood WBC); `Urine Albumin` never pairs with `Serum Albumin`; `N/A` unit; report_06's real errors still count. The existing RBC blood/urine swap test still passes. Breaking each rule makes at least one test fail. Saved baseline outputs re-scored with **no API calls**. |

### Baseline score before and after the eval fix

Same saved outputs (`runs/baseline`, `gemini-3.1-flash-lite`, 8 tuning reports, 3 repeats). All three repeats are byte-identical, so the numbers have no spread.

| Metric | Before (`runs/baseline/score_before_name_fix.md`) | After (`runs/baseline/score.md`) |
|---|---|---|
| Correct-row rate (pooled) | 62.3% | **71.7%** |
| Correct-row rate (mean of reports) | 62.3% | 76.2% |
| Critical errors | 20 | **10** |
| – wrong value | 2 | 7 |
| – invented range | 3 | 3 |
| – invented row | 15 | 0 |
| Dropped rows | 39 | 24 |
| Needs review | 8 | 3 |
| Critical errors on abnormal rows | 1 | 2 |

What moved and why:
- **13 renamed rows now score correct**: MCV, MCH and MCHC in reports 01 and 05; ALP, AST and ALT in 02; FBS and PPBS in 03; ESR in 06; LDL-C in 08.
- **Real errors were hidden and are now counted**: wrong values went up from 2 to 7. In report_06, `Albumin` Negative → `0.0`, `Leucocytes` `2-3` → `2.5`, `Erythrocytes` and `Squamous Epithelial Cells` `1-2` → `1.5`, and `CRP` `< 0.5` → `0.5` were previously split into a dropped row plus an invented row. `Sugar` `Present (+)` → `1.0` and `Ketones` Negative → `0.0` were already counted and still are.
- **Unchanged**: the 3 invented ranges (report_03) and the 24 dropped rows on report_11 page 2. These are extraction failures, not naming.

## Notes for the write-up

- **Diagnosis ranking (by harm):** 1. text/interval/`<` values forced into numbers, 2. invented reference ranges, 3. pages after the first silently dropped. **Caveat for #3:** the output looks complete, so a doctor would assume the page-2 tests were never done. Being silent puts it close to the top, even though it's a missing row rather than a wrong number.
