"""Step 1: Extract ward-quarter NDVI, LST, built-up share and rainfall from GEE.

Output: data/interim/gee_ward_quarter.csv

Per ward and calendar quarter we compute:
  ndvi_mean      Sentinel-2 SR, cloud-masked with Cloud Score+, median composite
  lst_c_mean     Landsat 8+9 Collection 2 Level 2 ST_B10 (deg C), median composite
  built_share    Dynamic World mean 'built' probability (urbanisation control)
  rain_mm        CHIRPS quarterly total precipitation (weather control)
  *_valid_frac   share of ward pixels with valid data (QC)

Run once:  earthengine authenticate
"""
import sys
import ee
import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import config as C


def load_wards() -> gpd.GeoDataFrame:
    g = gpd.read_file(C.WARDS_FILE).to_crs(C.CRS_GEO)
    if C.WARD_ID_COL not in g.columns:
        g[C.WARD_ID_COL] = range(1, len(g) + 1)
    g = g[g.geometry.notna()].copy()
    g["geometry"] = g.geometry.buffer(0)      # repair invalid polygons
    # simplify (~10 m) so the geometry payload stays under GEE request limits
    g["geometry"] = (
        g.to_crs(C.CRS_PROJ).geometry.simplify(10).to_crs(C.CRS_GEO)
    )
    return g


def to_fc(g: gpd.GeoDataFrame) -> ee.FeatureCollection:
    feats = [
        ee.Feature(ee.Geometry(row.geometry.__geo_interface__),
                   {C.WARD_ID_COL: row[C.WARD_ID_COL]})
        for _, row in g.iterrows()
    ]
    return ee.FeatureCollection(feats)


# ---- masking / composites ---------------------------------------------------
def s2_ndvi(start, end, region):
    s2 = (ee.ImageCollection(C.S2_COLLECTION)
          .filterDate(start, end).filterBounds(region))
    cs = ee.ImageCollection(C.CLOUDSCORE_COLLECTION)
    s2 = s2.linkCollection(cs, ["cs_cdf"])
    s2 = s2.map(lambda im: im.updateMask(im.select("cs_cdf").gte(C.CLOUDSCORE_MIN)))
    ndvi = s2.map(lambda im: im.normalizedDifference(["B8", "B4"]).rename("ndvi"))
    return ndvi.median().rename("ndvi")


def _l_mask_scale(im):
    qa = im.select("QA_PIXEL")
    # bits: 1 dilated cloud, 2 cirrus, 3 cloud, 4 cloud shadow
    bad = (qa.bitwiseAnd(1 << 1).neq(0)
           .Or(qa.bitwiseAnd(1 << 2).neq(0))
           .Or(qa.bitwiseAnd(1 << 3).neq(0))
           .Or(qa.bitwiseAnd(1 << 4).neq(0)))
    lst = (im.select("ST_B10").multiply(0.00341802).add(149.0)
           .subtract(273.15).rename("lst_c"))
    return lst.updateMask(bad.Not())


def landsat_lst(start, end, region):
    col = (ee.ImageCollection(C.L8_COLLECTION)
           .merge(ee.ImageCollection(C.L9_COLLECTION))
           .filterDate(start, end).filterBounds(region)
           .map(_l_mask_scale))
    return col.median().rename("lst_c")


def built_share(start, end, region):
    dw = (ee.ImageCollection(C.DYNAMIC_WORLD)
          .filterDate(start, end).filterBounds(region).select("built"))
    return dw.mean().rename("built_share")


def rain(start, end, region):
    r = (ee.ImageCollection(C.CHIRPS)
         .filterDate(start, end).filterBounds(region).sum())
    return r.rename("rain_mm")


def quarters():
    for y in range(C.START_YEAR, C.END_YEAR + 1):
        for q in range(1, 5):
            label = f"{y}Q{q}"
            if label > C.LAST_COMPLETE_QUARTER:
                return
            m0 = 3 * (q - 1) + 1
            start = f"{y}-{m0:02d}-01"
            end = (f"{y + 1}-01-01" if q == 4 else f"{y}-{m0 + 3:02d}-01")
            yield label, start, end


def main():
    ee.Initialize(project=C.GEE_PROJECT)
    wards = load_wards()
    fc = to_fc(wards)
    region = fc.geometry().bounds()

    mean = ee.Reducer.mean()
    frames = []
    for label, start, end in quarters():
        ndvi = s2_ndvi(start, end, region)
        lst = landsat_lst(start, end, region)
        stack = (ndvi.addBands(lst).addBands(built_share(start, end, region))
                 .addBands(rain(start, end, region)))
        # validity fraction = mean of the unmasked indicator
        valid = (ndvi.mask().rename("ndvi_valid_frac")
                 .addBands(lst.mask().rename("lst_valid_frac")))
        out = stack.addBands(valid).reduceRegions(
            collection=fc, reducer=mean, scale=C.SCALE_M, tileScale=4)
        feats = out.getInfo()["features"]
        df = pd.DataFrame([f["properties"] for f in feats])
        df["quarter"] = label
        frames.append(df)
        print(f"{label}: {len(df)} wards")

    res = pd.concat(frames, ignore_index=True)
    res = res.rename(columns={
        "ndvi": "ndvi_mean", "lst_c": "lst_c_mean"})
    res.to_csv(C.DATA_INTERIM / "gee_ward_quarter.csv", index=False)
    print("saved", C.DATA_INTERIM / "gee_ward_quarter.csv")


if __name__ == "__main__":
    main()
