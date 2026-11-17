"""Step 3: Quarterly station means -> IDW interpolation to ward centroids.

Input : data/raw/aq_stations.csv, data/raw/aq_daily.csv, ward boundaries
Output: data/interim/pm_ward_quarter.csv  (ward_id, quarter, pm25_idw, pm10_idw,
                                           n_stations_pm25, n_stations_pm10)

Choices worth stating in your write-up:
  * a station-quarter counts only with >= MIN_DAYS_PER_QUARTER daily readings
  * IDW power = config.IDW_POWER, distances in metres in UTM 43N, all valid
    stations used (the network is small, so no neighbourhood cut-off)
  * interpolation error is NOT in the regression -- treat PM results as
    suggestive and say so (or bootstrap over stations)
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C


def idw(xy_known, values, xy_target, power):
    d = np.sqrt(((xy_target[:, None, :] - xy_known[None, :, :]) ** 2).sum(-1))
    d = np.maximum(d, 1.0)                      # avoid divide-by-zero at a station
    w = 1.0 / d ** power
    return (w * values[None, :]).sum(1) / w.sum(1)


def quarterly_station_means(daily: pd.DataFrame) -> pd.DataFrame:
    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily["quarter"] = daily["date"].dt.to_period("Q").astype(str)
    g = (daily.groupby(["station_id", "parameter", "quarter"])["value"]
         .agg(mean="mean", n_days="count").reset_index())
    return g[g.n_days >= C.MIN_DAYS_PER_QUARTER]


def main():
    wards = gpd.read_file(C.WARDS_FILE)
    if C.WARD_ID_COL not in wards.columns:
        wards[C.WARD_ID_COL] = range(1, len(wards) + 1)
    wards = wards.to_crs(C.CRS_PROJ)
    cent = np.c_[wards.geometry.centroid.x, wards.geometry.centroid.y]

    stations = pd.read_csv(C.DATA_RAW / "aq_stations.csv").drop_duplicates("station_id")
    pts = gpd.GeoDataFrame(
        stations, geometry=gpd.points_from_xy(stations.lon, stations.lat),
        crs=C.CRS_GEO).to_crs(C.CRS_PROJ)
    stations["x"], stations["y"] = pts.geometry.x.values, pts.geometry.y.values

    qm = quarterly_station_means(pd.read_csv(C.DATA_RAW / "aq_daily.csv"))
    qm = qm.merge(stations[["station_id", "x", "y"]], on="station_id")

    out = []
    for (param, q), grp in qm.groupby(["parameter", "quarter"]):
        if len(grp) < 3:                        # need a few stations to interpolate
            continue
        est = idw(grp[["x", "y"]].to_numpy(), grp["mean"].to_numpy(), cent, C.IDW_POWER)
        out.append(pd.DataFrame({
            C.WARD_ID_COL: wards[C.WARD_ID_COL].values, "quarter": q,
            "parameter": param, "value": est, "n_stations": len(grp)}))
    long = pd.concat(out, ignore_index=True)
    wide = long.pivot_table(index=[C.WARD_ID_COL, "quarter"], columns="parameter",
                            values=["value", "n_stations"]).reset_index()
    wide.columns = [a if not b else f"{b}_{'idw' if a == 'value' else 'n_stations'}"
                    for a, b in wide.columns]
    wide.to_csv(C.DATA_INTERIM / "pm_ward_quarter.csv", index=False)
    print("saved", len(wide), "ward-quarters")


if __name__ == "__main__":
    main()
