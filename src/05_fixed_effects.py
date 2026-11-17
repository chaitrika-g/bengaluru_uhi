"""Step 5: Fixed-effects regressions of surface temperature on green cover.

Output: outputs/regression_results.txt, outputs/coef_table.csv

Models (dependent variable: LST in deg C), SEs clustered by ward:
  M1 pooled OLS            LST ~ NDVI
  M2 ward FE               absorbs time-invariant ward traits (elevation, lakes...)
  M3 ward FE + quarter FE  also absorbs city-wide seasonality / weather shocks
  M4 M3 + built share + rainfall
  M5 M4 excluding Q3 (monsoon) as a robustness check
  M6 PM2.5 as dependent variable (suggestive only: interpolated regressor/outcome)

Reading the coefficient: NDVI is scaled so the coefficient is the change in LST
for a +0.1 NDVI change; a 0.1 NDVI DROP therefore raises LST by -coef.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C

try:
    from linearmodels.panel import PanelOLS, compare
except ImportError:
    raise SystemExit("pip install linearmodels")


def fit(df, y, xs, entity=True, time=True):
    d = df.dropna(subset=[y] + xs).set_index([C.WARD_ID_COL, "t"])
    mod = PanelOLS(d[y], d[xs], entity_effects=entity, time_effects=time,
                   drop_absorbed=True)
    return mod.fit(cov_type="clustered", cluster_entity=True)


def main():
    df = pd.read_csv(C.DATA_PROCESSED / "panel.csv")
    base = ["ndvi_10"]
    ctrl = base + ["built_share", "rain_mm"]

    res = {
        "M1 pooled": fit(df, "lst_c_mean", base, entity=False, time=False),
        "M2 ward FE": fit(df, "lst_c_mean", base, time=False),
        "M3 ward+qtr FE": fit(df, "lst_c_mean", base),
        "M4 +controls": fit(df, "lst_c_mean", ctrl),
        "M5 no Q3": fit(df[df["q"] != 3], "lst_c_mean", ctrl),
    }
    if "pm25_idw" in df.columns and df["pm25_idw"].notna().any():
        res["M6 PM2.5"] = fit(df, "pm25_idw", ctrl)

    txt = str(compare(res, precision="std_errors"))
    (C.OUTPUTS / "regression_results.txt").write_text(txt)
    print(txt)

    rows = []
    for name, r in res.items():
        b = r.params["ndvi_10"]
        lo, hi = r.conf_int().loc["ndvi_10"]
        rows.append({"model": name, "coef_per_0.1_ndvi": b, "se": r.std_errors["ndvi_10"],
                     "ci_low": lo, "ci_high": hi, "p": r.pvalues["ndvi_10"],
                     "nobs": r.nobs, "r2_within": r.rsquared_within})
    pd.DataFrame(rows).to_csv(C.OUTPUTS / "coef_table.csv", index=False)

    m = res["M4 +controls"].params["ndvi_10"]
    print(f"\nHeadline (M4): a 0.1 DROP in NDVI changes LST by {-m:+.2f} deg C")


if __name__ == "__main__":
    main()
