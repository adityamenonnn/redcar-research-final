"""
integrate_hpi.py
================
Parses the Land Registry UK HPI download for Redcar & Cleveland and merges
quarterly house price data into redcar_ssi_2015_panel.csv.

How to get the data
-------------------
The CSV was downloaded from the Land Registry linked data browser:
  https://landregistry.data.gov.uk/app/ukhpi/browse
  Area: Redcar and Cleveland
  Date range: October 2015 to December 2019
  Save as: research/redcar/_source_data/ukhpi_rc_2015_2019.csv

Alternatively pass the path via --csv argument.

What this adds
--------------
Monthly Land Registry data aggregated to quarterly means/sums.

  rc_hpi_avg_price_q_mean    mean average price (all property types), RC LA
  rc_hpi_index_q_mean        mean HPI index (base Jan 2015=100), RC LA
  rc_hpi_pct_yoy_q_mean      mean year-on-year % change, RC LA
  rc_hpi_sales_vol_q_sum     sum of monthly sales volumes within the quarter
  rc_hpi_data_quality         HIGH (Land Registry administrative data)

Usage:
  cd /Users/adityamenon/Documents/PolicySim/policysim-mesa
  python3 research/redcar/integrate_hpi.py
  # or with explicit path:
  python3 research/redcar/integrate_hpi.py --csv /path/to/ukhpi.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

BASE      = Path(__file__).parent
PANEL_IN  = BASE / "redcar_ssi_2015_panel.csv"
PANEL_OUT = BASE / "redcar_ssi_2015_panel.csv"

DEFAULT_CSV = BASE / "_source_data" / "ukhpi_rc_2015_2019.csv"

MONTH_TO_Q = {
    1: "Q1", 2: "Q1", 3: "Q1",
    4: "Q2", 5: "Q2", 6: "Q2",
    7: "Q3", 8: "Q3", 9: "Q3",
    10: "Q4", 11: "Q4", 12: "Q4",
}

# Panel quarters we care about
PANEL_QUARTERS = [
    "2015Q4", "2016Q1", "2016Q2", "2016Q3", "2016Q4",
    "2017Q1", "2017Q2", "2017Q3", "2017Q4",
    "2018Q1", "2018Q2", "2018Q3", "2018Q4",
    "2019Q1", "2019Q2", "2019Q3", "2019Q4",
]


def parse_hpi(csv_path: Path) -> pd.DataFrame:
    raw = pd.read_csv(csv_path)
    print(f"  Raw shape: {raw.shape}")

    # Period column is "YYYY-MM" or "YYYY-MM-DD" format
    period_col = "Period"
    raw["_period"] = pd.to_datetime(raw[period_col], errors="coerce")
    raw["_year"]  = raw["_period"].dt.year
    raw["_month"] = raw["_period"].dt.month
    raw["quarter"] = raw["_year"].astype(str) + raw["_month"].map(MONTH_TO_Q)

    col_map = {
        "Average price All property types":             "rc_hpi_avg_price",
        "House price index All property types":         "rc_hpi_index",
        "Percentage change (yearly) All property types": "rc_hpi_pct_yoy",
        "Sales volume All property types":              "rc_hpi_sales_vol",
    }

    missing = [c for c in col_map if c not in raw.columns]
    if missing:
        raise ValueError(f"Expected columns not found: {missing}\nAvailable: {raw.columns.tolist()}")

    for src, dst in col_map.items():
        raw[dst] = pd.to_numeric(raw[src], errors="coerce")

    raw = raw[raw["quarter"].isin(PANEL_QUARTERS)].copy()
    print(f"  Rows in panel date range: {len(raw)}")

    agg = (raw.groupby("quarter")
               .agg(
                   rc_hpi_avg_price_q_mean=("rc_hpi_avg_price", "mean"),
                   rc_hpi_index_q_mean    =("rc_hpi_index",     "mean"),
                   rc_hpi_pct_yoy_q_mean  =("rc_hpi_pct_yoy",  "mean"),
                   rc_hpi_sales_vol_q_sum =("rc_hpi_sales_vol", "sum"),
               )
               .reset_index())

    agg["rc_hpi_avg_price_q_mean"] = agg["rc_hpi_avg_price_q_mean"].round(0)
    agg["rc_hpi_index_q_mean"]     = agg["rc_hpi_index_q_mean"].round(1)
    agg["rc_hpi_pct_yoy_q_mean"]   = agg["rc_hpi_pct_yoy_q_mean"].round(2)
    agg["rc_hpi_sales_vol_q_sum"]  = agg["rc_hpi_sales_vol_q_sum"].astype("Int64")
    agg["rc_hpi_data_quality"]     = "HIGH"

    print(f"  Quarters produced: {sorted(agg.quarter.tolist())}")
    return agg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(DEFAULT_CSV),
                        help="Path to Land Registry HPI CSV for RC LA")
    args = parser.parse_args()
    csv_path = Path(args.csv)

    print("integrate_hpi.py")
    print("=" * 50)

    if not csv_path.exists():
        print(f"\nMissing file: {csv_path}")
        print("\nDownload from:")
        print("  https://landregistry.data.gov.uk/app/ukhpi/browse")
        print("  Area: Redcar and Cleveland, Oct 2015 to Dec 2019")
        print(f"  Save as: {DEFAULT_CSV}")
        return

    print(f"\nParsing: {csv_path.name}")
    hpi_q = parse_hpi(csv_path)

    print(hpi_q[["quarter", "rc_hpi_avg_price_q_mean",
                 "rc_hpi_index_q_mean", "rc_hpi_pct_yoy_q_mean",
                 "rc_hpi_sales_vol_q_sum"]].to_string(index=False))

    print(f"\nLoading panel ({PANEL_IN.name}) ...")
    panel = pd.read_csv(PANEL_IN)
    print(f"  {len(panel)} rows x {len(panel.columns)} columns")

    hpi_cols = [c for c in hpi_q.columns if c != "quarter"]
    existing = [c for c in hpi_cols if c in panel.columns]
    if existing:
        panel = panel.drop(columns=existing)
        print(f"  Dropped {len(existing)} existing rc_hpi_ columns for clean re-run")

    panel = panel.merge(hpi_q, on="quarter", how="left")
    print(f"  After merge: {len(panel)} rows x {len(panel.columns)} columns")
    print(f"  New columns: {hpi_cols}")

    panel.to_csv(PANEL_OUT, index=False)
    print(f"\nSaved: {PANEL_OUT}")


if __name__ == "__main__":
    main()
