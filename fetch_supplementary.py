"""
fetch_supplementary.py
======================
Pulls additional data and merges it into redcar_ssi_2015_panel.csv.

What this adds
--------------
1. RC LA mid-year population estimates (Nomis NM_31_1):

  rc_la_pop_total          total population, Redcar & Cleveland (ONS mid-year estimate)
  rc_la_pop_year           calendar year of the mid-year estimate
  rc_la_pop_data_quality   HIGH (ONS administrative)

  Note: NM_31_1 provides total population only at LA level via the Nomis API.
  Working-age (16-64) is not available as a single aggregate code via the API;
  that breakdown requires the full single-year-of-age table (manually summed).
  Population values are annual mid-year estimates, repeated across all quarters
  within that calendar year. 2019 data not yet published at time of data pull;
  the 2018 value is forward-filled for 2019 quarters.

Datasets investigated but not added programmatically
-----------------------------------------------------
UK House Price Index (Land Registry):
  LA-level HPI is available from Land Registry open data, but the S3 public
  bucket (prod.publicdata.landregistry.gov.uk) returned 403 Forbidden at time
  of data pull. The Land Registry UKHPI CSV browser endpoint also returned 403.
  Can be added manually: download from https://www.gov.uk/government/collections/
  uk-house-price-index-reports and save RC LA rows as _source_data/rc_hpi.csv.

Housing Benefit claimants (DWP):
  DWP Housing Benefit statistics are published on DWP Stat-Xplore and as
  annual releases on gov.uk. The Nomis dataset NM_127_1 is model-based
  unemployment estimates (APS), not Housing Benefit. HB data is not available
  programmatically via Nomis. Can be added manually from Stat-Xplore:
  Dataset: Housing Benefit, Geography: Redcar & Cleveland, Rows: Quarter,
  save as _source_data/hb_redcar_2015_2019.xlsx.

  Note: HB claimant counts fall from 2017 onward partly because Housing Benefit
  was absorbed into Universal Credit for working-age claimants. The decline
  does not fully reflect reduced housing benefit need.

PIP (Personal Independence Payment):
  Available from DWP Stat-Xplore (login required). Relevant for the health
  exit pathway alongside ESA.
  Dataset: PIP Cases with Entitlement, Geography: Redcar & Cleveland,
  Rows: Quarter, Date: 2015 Q4 to 2019 Q4.
  Save as _source_data/pip_redcar_2015_2019.xlsx.

Usage:
  cd /Users/adityamenon/Documents/PolicySim/policysim-mesa
  python3 research/redcar/fetch_supplementary.py

Cache:
  _nomis_cache/rc_population_raw.csv
"""

from pathlib import Path
import time

import numpy as np
import pandas as pd
import requests

# ── paths ──────────────────────────────────────────────────────────────────────
BASE       = Path(__file__).parent
CACHE_DIR  = BASE / "_nomis_cache"
PANEL_PATH = BASE / "redcar_ssi_2015_panel.csv"
NOMIS      = "https://www.nomisweb.co.uk/api/v01/dataset"

CACHE_DIR.mkdir(exist_ok=True)

RC_GEO = "E06000003"   # Redcar and Cleveland LA

# ── quarter index (shared with all other scripts) ──────────────────────────────
QUARTERS = {
    "2015Q4": ["October 2015",   "November 2015",  "December 2015"],
    "2016Q1": ["January 2016",   "February 2016",  "March 2016"],
    "2016Q2": ["April 2016",     "May 2016",       "June 2016"],
    "2016Q3": ["July 2016",      "August 2016",    "September 2016"],
    "2016Q4": ["October 2016",   "November 2016",  "December 2016"],
    "2017Q1": ["January 2017",   "February 2017",  "March 2017"],
    "2017Q2": ["April 2017",     "May 2017",       "June 2017"],
    "2017Q3": ["July 2017",      "August 2017",    "September 2017"],
    "2017Q4": ["October 2017",   "November 2017",  "December 2017"],
    "2018Q1": ["January 2018",   "February 2018",  "March 2018"],
    "2018Q2": ["April 2018",     "May 2018",       "June 2018"],
    "2018Q3": ["July 2018",      "August 2018",    "September 2018"],
    "2018Q4": ["October 2018",   "November 2018",  "December 2018"],
    "2019Q1": ["January 2019",   "February 2019",  "March 2019"],
    "2019Q2": ["April 2019",     "May 2019",       "June 2019"],
    "2019Q3": ["July 2019",      "August 2019",    "September 2019"],
    "2019Q4": ["October 2019",   "November 2019",  "December 2019"],
}

QUARTER_YEARS = {q: int(q[:4]) for q in QUARTERS}


# ── helper ─────────────────────────────────────────────────────────────────────

def get_csv(url: str, cache_file: Path) -> pd.DataFrame:
    """Fetch a URL returning CSV content. Uses local cache if present."""
    if cache_file.exists():
        print(f"    [cache] {cache_file.name}")
        return pd.read_csv(cache_file)
    print(f"    [fetch] {url[:100]}...")
    headers = {"User-Agent": "Mozilla/5.0 (policysim-mesa data pull)"}
    r = requests.get(url, headers=headers, timeout=120)
    r.raise_for_status()
    cache_file.write_bytes(r.content)
    time.sleep(1.2)
    df = pd.read_csv(cache_file)
    if df.empty:
        cache_file.unlink()
        raise ValueError(f"Empty response for {cache_file.name}")
    return df


# ── 1. Population estimates (NM_31_1) ─────────────────────────────────────────

def fetch_rc_population() -> pd.DataFrame:
    """
    Nomis NM_31_1: ONS mid-year total population estimates for RC LA.
    sex=7 (persons), age=0 (all ages). Returns annual values, one per quarter.

    Date coverage: NM_31_1 lags by ~18 months. 2019 mid-year estimate may not
    be published yet; if missing, 2018 value is forward-filled for 2019 quarters.
    """
    print("\n[1] RC LA population estimates (NM_31_1) ...")
    url = (f"{NOMIS}/NM_31_1.data.csv"
           f"?geography={RC_GEO}"
           f"&date=2015,2016,2017,2018,2019"
           f"&sex=7"
           f"&age=0"
           f"&measures=20100"
           f"&select=date_name,obs_value")
    cache = CACHE_DIR / "rc_population_raw.csv"
    raw = get_csv(url, cache)

    # Nomis returns columns as uppercase DATE_NAME, OBS_VALUE
    # date_name comes back as integer year (e.g. 2015) — use pd.to_numeric directly
    raw.columns = [c.lower() for c in raw.columns]
    raw["year"] = pd.to_numeric(raw["date_name"], errors="coerce").astype("Int64")
    raw["population"] = pd.to_numeric(raw["obs_value"], errors="coerce")

    year_to_pop = dict(zip(raw["year"], raw["population"]))
    print(f"  Available years: {sorted(year_to_pop.keys())}")

    # Build quarterly lookup: repeat annual estimate for all quarters in that year.
    # Forward-fill 2019 from 2018 if 2019 not yet published.
    if 2019 not in year_to_pop:
        year_to_pop[2019] = year_to_pop.get(2018, np.nan)
        print("  2019 not yet published — forward-filling from 2018")

    records = []
    for q, year in QUARTER_YEARS.items():
        records.append({
            "quarter":               q,
            "rc_la_pop_total":       int(year_to_pop[year]) if year in year_to_pop and not pd.isna(year_to_pop[year]) else np.nan,
            "rc_la_pop_year":        year,
            "rc_la_pop_data_quality": "HIGH",
        })

    df = pd.DataFrame(records)
    sample = df[df["quarter"] == "2016Q1"].iloc[0]
    print(f"  OK — 2016Q1 total population: {sample['rc_la_pop_total']:,.0f}")
    return df


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    print("fetch_supplementary.py")
    print("=" * 50)

    pop_q = fetch_rc_population()

    print(f"\nLoading panel ({PANEL_PATH.name}) ...")
    panel = pd.read_csv(PANEL_PATH)
    print(f"  {len(panel)} rows x {len(panel.columns)} columns")

    # Drop any columns from a previous run
    new_cols = [c for c in pop_q.columns if c != "quarter"]
    existing = [c for c in new_cols if c in panel.columns]
    if existing:
        panel = panel.drop(columns=existing)
        print(f"  Dropped {len(existing)} existing columns for clean re-run")

    panel = panel.merge(pop_q, on="quarter", how="left")
    print(f"  After merge: {len(panel)} rows x {len(panel.columns)} columns")
    print(f"  New columns: {new_cols}")

    panel.to_csv(PANEL_PATH, index=False)
    print(f"\nSaved: {PANEL_PATH}")

    print("\n--- Population by quarter ---")
    print(pop_q[["quarter", "rc_la_pop_total", "rc_la_pop_year"]].to_string(index=False))

    print("""
-----------------------------------------------------------------------
Data not added programmatically (manual download required)
-----------------------------------------------------------------------

UK House Price Index (RC LA):
  Land Registry S3 public bucket returned 403 at time of data pull.
  Download manually from:
  https://www.gov.uk/government/collections/uk-house-price-index-reports
  Filter to Area_Code=E06000003 and save as _source_data/rc_hpi.csv.

Housing Benefit claimants (DWP Stat-Xplore):
  1. Go to https://stat-xplore.dwp.gov.uk and log in
  2. Open: Housing Benefit -> HB caseload (tenure type)
  3. Rows: Quarter, Columns: Geography
  4. Filter geography: Redcar and Cleveland, Date: 2015 Q4 to 2019 Q4
  5. Save as: research/redcar/_source_data/hb_redcar_2015_2019.xlsx

PIP (Personal Independence Payment) claimants (DWP Stat-Xplore):
  1. Open: Personal Independence Payment -> PIP Cases with Entitlement
  2. Rows: Quarter, Columns: Geography
  3. Filter geography: Redcar and Cleveland, Date: 2015 Q4 to 2019 Q4
  4. Save as: research/redcar/_source_data/pip_redcar_2015_2019.xlsx
-----------------------------------------------------------------------
""")


if __name__ == "__main__":
    main()
