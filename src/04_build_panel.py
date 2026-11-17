"""Step 4: Merge GEE + PM into a clean ward-quarter panel.

Output: data/processed/panel.csv   (one row per ward x quarter)

Cleaning rules (all in config.py):
  * drop ward-quarters where valid-pixel share < MIN_VALID_FRACTION for NDVI or LST
  * keep the panel unbalanced -- monsoon (Q3) cloud cover will remove many obs,
    and that missingness is NOT random, so report results with and without Q3
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C


def build(gee: pd.DataFrame, pm: pd.DataFrame | None) -> pd.DataFrame:
    df = gee.copy()
    before = len(df)
    ok = (df["ndvi_valid_frac"].fillna(0) >= C.MIN_VALID_FRACTION) & \
         (df["lst_valid_frac"].fillna(0) >= C.MIN_VALID_FRACTION)
    df = df[ok & df["ndvi_mean"].notna() & df["lst_c_mean"].notna()].copy()
    print(f"dropped {before - len(df)} of {before} ward-quarters for cloud/QC")

    if pm is not None:
        df = df.merge(pm, on=[C.WARD_ID_COL, "quarter"], how="left")

    p = pd.PeriodIndex(df["quarter"], freq="Q")
    df["year"], df["q"] = p.year, p.quarter
    df["t"] = (p.year - C.START_YEAR) * 4 + p.quarter      # numeric time index
    df["ndvi_10"] = df["ndvi_mean"] / 0.1                  # coefficient = effect of +0.1 NDVI
    return df.sort_values([C.WARD_ID_COL, "t"]).reset_index(drop=True)


def main():
    gee = pd.read_csv(C.DATA_INTERIM / "gee_ward_quarter.csv")
    pm_path = C.DATA_INTERIM / "pm_ward_quarter.csv"
    pm = pd.read_csv(pm_path) if pm_path.exists() else None
    panel = build(gee, pm)
    panel.to_csv(C.DATA_PROCESSED / "panel.csv", index=False)
    print("panel:", panel.shape, "| wards:", panel[C.WARD_ID_COL].nunique(),
          "| quarters:", panel["quarter"].nunique())


if __name__ == "__main__":
    main()
