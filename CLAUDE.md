# CLAUDE.md — Redcar SSI 2015 Research Context

This file captures full working context for the Redcar SSI closure panel dataset project. Read this at the start of any new session before doing anything.

---

## What this project is

A quarterly panel dataset covering the SSI Redcar steelworks closure (2 October 2015). The plant employed ~3,500 workers directly. The panel tracks labour market outcomes, benefit claimant counts, wages, housing prices, and population for Redcar & Cleveland LA and the North East region from 2015Q4 to 2019Q4.

**Panel file:** `redcar_ssi_2015_panel.csv`
**Dimensions:** 255 rows × 179 columns
**Structure:** 17 quarters × 15 rows per quarter (age band × gender combinations: all/16-24/25-49/50+ × all/male/female)
**GitHub repo:** https://github.com/adityamenonnn/redcar-research-final (public)
**Local repo for pushing:** `research/redcar/final_research/` (has its own `.git`)

---

## Key anchors (do not change these)

- **25% still-seeking at 2016Q1:** 540/2,070 SSI direct employees still on JSA at end of Feb 2016. Source: DWP SSI JSA Statistics March 2016.
- **93% off-benefits at 2016Q4:** 1,990/2,150 SSI+supply-chain claimants ended benefit claim by 31 Aug 2016 (DWP reference date is 2016Q3, placed at Q4 for model alignment). Source: DWP SSI Updated Statistics September 2016.
- **SSI workforce total:** 3,500 direct workers used for excess% calculations.
- **Closure date:** 2 October 2015.

---

## Scripts and what they do

Run in this order to reproduce the panel from scratch:

| Step | Script | What it does | Requires |
|------|--------|--------------|----------|
| 1 | `build_redcar_panel.py` | Base panel: ACC, APS, ASHE aggregate, BRES, Tees Valley | Nomis API (live) |
| 2 | `integrate_statxplore.py` | Real RC LA ACC by age and gender | `_source_data/acc4_age_gender_redcar_cleveland.xlsx` |
| 3 | `fetch_redcar_extra.py` | NE ACC by age, BEAO redundancy notifications, NE JSA duration | Nomis API (live) |
| 4 | `parse_ashe_age.py` | ASHE age-specific wage estimates (national ratios × NE median) | ONS ASHE Table 6 ZIPs (fetched + cached) |
| 5 | `integrate_esa.py` | ESA caseload by phase (assessment, WRAG, support) | `_source_data/esa_redcar_to_feb2018.xlsx` + `esa_redcar_from_may2018.xlsx` |
| 6 | `fetch_supplementary.py` | RC LA population estimates from Nomis NM_31_1 | Nomis API (live) |
| 7 | `integrate_hpi.py` | Land Registry UK HPI: avg price, index, YoY%, sales volume | `_source_data/ukhpi_rc_2015_2019.csv` |
| 8 | `estimate_statistical.py` | Statistical estimates: survival model, log-normal underemployment, Bayesian Dirichlet | Panel must exist |

```bash
cd /Users/adityamenon/Documents/PolicySim/policysim-mesa
python3 research/redcar/build_redcar_panel.py
python3 research/redcar/integrate_statxplore.py
python3 research/redcar/fetch_redcar_extra.py
python3 research/redcar/parse_ashe_age.py
python3 research/redcar/integrate_esa.py \
  --pre research/redcar/_source_data/esa_redcar_to_feb2018.xlsx \
  --post research/redcar/_source_data/esa_redcar_from_may2018.xlsx
python3 research/redcar/fetch_supplementary.py
python3 research/redcar/integrate_hpi.py
python3 research/redcar/estimate_statistical.py
```

---

## Data sources

### Nomis API (programmatic, cached)

| Series | What it is | Columns added |
|--------|-----------|---------------|
| NM_162_1 | Alternative Claimant Count | rc_la_*, ne_*, tv_ca_* claimant columns |
| NM_17_5 | Annual Population Survey (APS) | ne_unemployment_rate_%, ne_employment_rate_%, ne_activity_rate_%, age-specific variants |
| NM_30_1 | ASHE aggregate | ne_median_weekly_pay_gbp, ne_wage_p10/p25/p75/p90 |
| NM_189_1 | BRES sector employment | rc_la_manufacturing_jobs, rc_la_mining_util_jobs, rc_la_total_jobs |
| NM_4_1 | JSA by age and duration (NE region only — suppressed at LA) | ne_jsa_* duration columns |
| NM_31_1 | ONS mid-year population estimates | rc_la_pop_total, rc_la_pop_year |

Nomis base URL: `https://www.nomisweb.co.uk/api/v01/dataset`
RC LA geography code: `E06000003`
NE region code: `E12000001`

### Nomis API quirks to remember

- **NM_31_1 date_name comes back as int64, not string.** Use `pd.to_numeric(raw["date_name"], errors="coerce").astype("Int64")` — do NOT use `.str[:4]`.
- **NM_127_1 is NOT Housing Benefit.** It is model-based unemployment estimates (APS-based). HB is not on Nomis at all.
- **NM_31_1 age=0 = all ages (total population).** age=11 returns a narrow single-year band, not working-age. Working-age aggregate is not available via API.
- **BRES (NM_189_1) columns can come back as object dtype.** Force numeric with `pd.to_numeric(..., errors="coerce")` to avoid NaN on merge.
- **JSA duration (NM_4_1) is suppressed at LA level** — only NE regional level is available.

### ONS (programmatic, cached)

- **ASHE Table 6** (age group, gross weekly pay): fetched as annual ZIP files, extracted and parsed by `parse_ashe_age.py`. Cached in `_ashe_cache/`. National age-band ratios (band median / all-workers median) scaled against NE aggregate median to estimate NE age-specific wages. Data quality flag: `HIGH_SCALED`.
- **BEAO timeseries** (national redundancy notifications, GB 000s): fetched by `fetch_redcar_extra.py`. Cached in `_nomis_cache/beao_monthly.csv`.

### DWP Stat-Xplore (manual downloads — login required)

Stat-Xplore URL: https://stat-xplore.dwp.gov.uk

| File | Dataset | Status |
|------|---------|--------|
| `_source_data/acc4_age_gender_redcar_cleveland.xlsx` | ACC4 by age and gender, RC LA, Oct 2015-Dec 2019 | Integrated |
| `_source_data/esa_redcar_to_feb2018.xlsx` | ESA Caseload to Feb 2018, RC LA | Integrated |
| `_source_data/esa_redcar_from_may2018.xlsx` | ESA Caseload from May 2018, RC LA | Integrated |
| `_source_data/hb_redcar_2015_2019.xlsx` | Housing Benefit caseload, RC LA, 2015Q4-2019Q4 | NOT YET DOWNLOADED — rc_hb_* columns are all NaN |
| `_source_data/pip_redcar_2015_2019.xlsx` | PIP Cases with Entitlement, RC LA, 2015Q4-2019Q4 | NOT YET DOWNLOADED — not yet in panel |

### Land Registry UK HPI (manual download)

Downloaded from: https://landregistry.data.gov.uk/app/ukhpi/browse
Filter: Area = Redcar and Cleveland, Date = Oct 2015 to Dec 2019
Saved as: `_source_data/ukhpi_rc_2015_2019.csv`

**Note:** The Land Registry S3 public bucket (`prod.publicdata.landregistry.gov.uk`) returns 403 Forbidden — do not try to fetch it programmatically via S3.

---

## Column groups summary

| Prefix | What it covers | Count (approx) |
|--------|---------------|----------------|
| (no prefix) | Identifiers, row dimensions, outcome vars, SSI priors | ~30 |
| rc_la_* | RC LA claimant count + sector employment + population | ~15 |
| ne_* | NE claimant count, APS rates, wages, JSA duration | ~25 |
| tv_ca_* | Tees Valley CA claimant count | 3 |
| acc_* | RC LA ACC by age and gender (Stat-Xplore real data) | ~18 |
| ne_acc_* | NE ACC by age band (Nomis) | 8 |
| rc_vs_ne_* | RC vs NE age composition indices | 3 |
| ne_jsa_* | NE JSA by duration band | 8 |
| beao_* | National redundancy notifications | 2 |
| ashe_age_* | Age-specific wage estimates (HIGH_SCALED) | ~24 |
| esa_* | ESA caseload by phase (Stat-Xplore) | 8 |
| rc_hpi_* | Land Registry house price index, RC LA | 6 |
| rc_hb_* | Housing Benefit placeholder (all NaN) | 3 |
| stat_* | Statistical model outputs (survival, log-normal, Dirichlet) | ~30 |

**Total:** 255 rows × 179 columns

---

## Statistical methods (estimate_statistical.py)

**Method 1 — Exponential survival (still-seeking):**
Calibrated to DWP anchors: 25% at 2016Q1, ~3% at 2016Q4. Analytically solved lambda = 0.265/month. Bootstrap n=10,000.

**Method 2 — Aggregate log-normal underemployment:**
P(new wage < 90% of SSI pre-wage) using NE aggregate wage distribution. Wide CI reflects genuine NE wage dispersion.

**Method 2b — Age-specific log-normal underemployment:**
Same as Method 2 but uses ashe_age_*_median_est and ashe_age_*_sigma per age band. Age wage ratios: 16-24=0.840, 25-49=1.109, 50+=1.049.

**Method 3 — Bayesian Dirichlet-Multinomial outcome split:**
Prior: retrain 25%, share_similar 40%, exit 35% (kappa=20). RC LA ACC evidence weighted at 0.3. Posterior: retrain ~12%, share_similar ~33%, exit ~55%. Exit pulled up because older workforce + depressed local labour market.

---

## ESA parsing notes

ESA data in Stat-Xplore comes in two layouts depending on how the table is configured:

1. **Row-based:** Quarter in first column, phases as column headers. Parsed by the main path in `parse_esa_xlsx()`.
2. **Transposed:** Quarter spanning columns (wafer format), phases as sub-column headers in rows 10/11. Detected by checking `raw.iloc[10, 0] == "Quarter"` and `"phase" in raw.iloc[11, 0]`. Parsed by `_parse_transposed()`.

DWP split ESA into two datasets at the UC transition boundary (Feb 2018 / May 2018). Both files are needed. The post file takes precedence for any overlapping quarters.

---

## Known gaps / TODO

- **Housing Benefit (rc_hb_*):** All NaN. Download from Stat-Xplore and write integration script.
- **PIP:** Not in panel. Download from Stat-Xplore and write integration script.
- **Working-age population (rc_la_pop_working_age):** All NaN. Requires summing NM_31_1 single-year-of-age rows — not done.
- **Vacancy data:** Not available on Nomis for 2015-2019 at sub-national level. All relevant series end before 2012.
- **UC migration adjustment:** No formal adjustment applied. Rows from 2017Q1 onward carry a caveat in the `notes` column. ACC counts from 2017+ undercount relative to pre-UC baseline.

---

## How to update the GitHub repo

The GitHub repo lives inside `final_research/` which has its own `.git` pointing to `https://github.com/adityamenonnn/redcar-research-final`.

```bash
# After making changes to the main redcar/ files, sync and push:
cp redcar_ssi_2015_panel.csv final_research/
cp PANEL_COLUMN_REFERENCE.md final_research/
cp BIBLIOGRAPHY.md final_research/
cp <any_new_script>.py final_research/
cp _source_data/<new_file> final_research/_source_data/

cd final_research
git add <files>
git commit -m "description"
git push origin master
```

Do NOT use `git add -A` — it will pick up `.DS_Store`.

---

## Key decisions made during data collection

- **RC_GEO = E06000003** (Redcar and Cleveland LA ONS code)
- **BASELINE_QUARTERS = ["2019Q1", "2019Q2", "2019Q3", "2019Q4"]** — 2019 is the post-shock stable year used as baseline for excess calculations throughout
- **SSI_WORKERS = 3,500** — total affected direct workforce used as denominator for excess% columns
- **ESA baseline:** 2019 mean = ~6,350 claimants. Excess peaked at 2016Q1 (+650 = 18.6% of 3,500 workforce)
- **HPI index context:** RC LA index values of 73-78 (base Jan 2015=100, England) mean RC is structurally cheaper than England average — not a crash from 100
- **Population stability confirmed:** 2015=135,370 → 2019=136,699, flat — no significant net migration effect during closure period
