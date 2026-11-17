"""Step 6: Interactive choropleth maps (single HTML with toggleable layers).

Output: outputs/uhi_maps.html
Layers: mean LST, mean NDVI, change in NDVI and LST (last year vs first year
available), mean PM2.5 (if present). Hover a ward for its values.
"""
import sys
from pathlib import Path

import branca.colormap as cm
import folium
import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C


def ward_summary(panel: pd.DataFrame) -> pd.DataFrame:
    g = panel.groupby(C.WARD_ID_COL)
    s = g[["ndvi_mean", "lst_c_mean"]].mean()
    if "pm25_idw" in panel.columns:
        s["pm25"] = g["pm25_idw"].mean()
    yr = panel.groupby([C.WARD_ID_COL, "year"])[["ndvi_mean", "lst_c_mean"]].mean().reset_index()
    first, last = yr["year"].min(), yr["year"].max()
    a = yr[yr.year == first].set_index(C.WARD_ID_COL)
    b = yr[yr.year == last].set_index(C.WARD_ID_COL)
    s["d_ndvi"] = (b["ndvi_mean"] - a["ndvi_mean"])
    s["d_lst"] = (b["lst_c_mean"] - a["lst_c_mean"])
    s.attrs["span"] = f"{first}-{last}"
    return s.reset_index()


def add_layer(m, gdf, col, label, palette, diverging=False):
    vals = gdf[col].dropna()
    if vals.empty:
        return
    if diverging:
        lim = max(abs(vals.quantile(0.02)), abs(vals.quantile(0.98)))
        cmap = cm.LinearColormap(palette, vmin=-lim, vmax=lim)
    else:
        cmap = cm.LinearColormap(palette, vmin=vals.quantile(0.02), vmax=vals.quantile(0.98))
    cmap.caption = label
    folium.GeoJson(
        gdf, name=label, show=(col == "lst_c_mean"),
        style_function=lambda f, c=col, cmap=cmap: {
            "fillColor": cmap(f["properties"][c]) if f["properties"][c] is not None else "#cccccc",
            "color": "#444", "weight": 0.4, "fillOpacity": 0.75},
        tooltip=folium.GeoJsonTooltip(
            fields=[C.WARD_NAME_COL if C.WARD_NAME_COL in gdf.columns else C.WARD_ID_COL, col],
            aliases=["Ward", label], localize=True),
    ).add_to(m)
    cmap.add_to(m)


def main():
    panel = pd.read_csv(C.DATA_PROCESSED / "panel.csv")
    wards = gpd.read_file(C.WARDS_FILE).to_crs(C.CRS_GEO)
    if C.WARD_ID_COL not in wards.columns:
        wards[C.WARD_ID_COL] = range(1, len(wards) + 1)
    s = ward_summary(panel)
    gdf = wards.merge(s, on=C.WARD_ID_COL, how="left")
    span = s.attrs.get("span", "")

    m = folium.Map(location=[12.97, 77.59], zoom_start=11, tiles="cartodbpositron")
    add_layer(m, gdf, "lst_c_mean", "Mean LST (deg C)", ["#ffffb2", "#fd8d3c", "#bd0026"])
    add_layer(m, gdf, "ndvi_mean", "Mean NDVI", ["#f7fcb9", "#78c679", "#006837"])
    add_layer(m, gdf, "d_ndvi", f"Change in NDVI ({span})", ["#b2182b", "#f7f7f7", "#2166ac"], True)
    add_layer(m, gdf, "d_lst", f"Change in LST ({span}, deg C)", ["#2166ac", "#f7f7f7", "#b2182b"], True)
    if "pm25" in gdf.columns:
        add_layer(m, gdf, "pm25", "Mean PM2.5 (IDW, ug/m3)", ["#ffffcc", "#fd8d3c", "#800026"])
    folium.LayerControl(collapsed=False).add_to(m)
    out = C.OUTPUTS / "uhi_maps.html"
    m.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
