# Bengaluru Urban Heat Island & Green Cover Analysis (2022–2026)

How much hotter does a Bengaluru ward get when it loses green cover? This project builds a
ward-by-quarter panel of satellite vegetation (NDVI), land surface temperature (LST) and
interpolated PM2.5/PM10, then estimates the temperature penalty of green cover loss with
fixed-effects regressions and interactive choropleth maps.

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1 | `src/01_gee_extract.py` | `data/interim/gee_ward_quarter.csv` (NDVI, LST, built share, rainfall per ward-quarter) |
| 2 | `src/02_openaq_ingest.py` | `data/raw/aq_stations.csv`, `data/raw/aq_daily.csv` |
| 3 | `src/03_interpolate_pm.py` | `data/interim/pm_ward_quarter.csv` (IDW to ward centroids) |
| 4 | `src/04_build_panel.py` | `data/processed/panel.csv` |
| 5 | `src/05_fixed_effects.py` | `outputs/regression_results.txt`, `outputs/coef_table.csv` |
| 6 | `src/06_maps.py` | `outputs/uhi_maps.html` |

Steps 2–3 are optional for the temperature result; the panel builds without PM data.

## Setup (you need to do these once)

1. **Python env**: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
2. **Ward boundaries**: download from https://data.opencity.in/dataset, save as
   `data/raw/wards.geojson` (or edit `WARDS_FILE` in `config.py`). Set `WARD_NAME_COL`
   to your file's name column. Use ONE boundary version for the whole panel.
3. **Google Earth Engine**: register at https://earthengine.google.com (free for
   non-commercial/research use) and create a Cloud project. Put its ID in `GEE_PROJECT`
   in `config.py`, then run `earthengine authenticate`.
4. **OpenAQ key** (step 2 only): create a free account at https://explore.openaq.org, then
   `export OPENAQ_API_KEY=your_key`.

Run steps in order: `python src/01_gee_extract.py`, and so on.

## Method notes

- **NDVI**: Sentinel-2 SR Harmonized, masked with Cloud Score+, quarterly median composite.
- **LST**: Landsat 8 + 9 Collection 2 Level 2, band `ST_B10` converted to °C
  (`DN × 0.00341802 + 149.0 − 273.15`), QA_PIXEL cloud/shadow masked, quarterly median.
- **Controls**: Dynamic World mean built probability (urbanisation), CHIRPS rainfall.
- **Reduction scale**: 30 m, ward mean. Ward-quarters with under 50% valid pixels are dropped.
- **Regression**: PanelOLS with ward and quarter fixed effects, SEs clustered by ward.
  NDVI is scaled by 0.1, so the coefficient is °C per +0.1 NDVI.

## Limitations to state in your write-up

- **Monsoon gaps**: Q3 (Jun–Sep) has heavy cloud cover, so valid observations drop and the
  missingness is non-random. Model M5 excludes Q3 as a check.
- **Satellite overpass time**: Landsat passes at roughly 10:30 am, so LST reflects late-morning
  surface heat, not daily mean or nighttime UHI (and surface temperature is not air temperature).
- **Identification**: fixed effects remove time-invariant ward traits and city-wide shocks, but
  not ward-specific shocks that move NDVI and LST together (e.g. construction that also
  changes surface materials). The built-share control helps; consider ward-specific trends or
  an event-study design as an extension.
- **Spatial correlation**: neighbouring wards are correlated; ward-clustered SEs do not fully
  address this. Conley spatial HAC errors are a natural extension.
- **PM interpolation**: the CPCB/OpenAQ network is sparse, and the set of reporting stations
  changes over time. Interpolated PM carries error that the regression ignores, so treat PM
  results as suggestive.
- **Time window**: the panel runs through 2026Q3; 2026Q4 is incomplete as of November 2026.
- **Ward boundaries**: delimitations have changed (198 → 243 wards, plus new Greater Bengaluru
  Authority corporations). Check which version your OpenCity file reflects.

## Ideas for the master's application

Add an event-study around large known projects, a lagged-NDVI specification, heterogeneity by
ward density, and a short policy note converting the coefficient into a cooling value of tree
cover (e.g. avoided cooling demand).
