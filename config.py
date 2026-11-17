"""Central configuration for the Bengaluru UHI & green-cover project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
for p in (DATA_RAW, DATA_INTERIM, DATA_PROCESSED, OUTPUTS):
    p.mkdir(parents=True, exist_ok=True)

# --- Spatial base -----------------------------------------------------------
# Download the ward boundaries from OpenCity (https://data.opencity.in/dataset)
# and save as data/raw/wards.geojson (or .shp -> point WARDS_FILE at it).
# IMPORTANT: use ONE fixed boundary version for the whole panel. Ward
# delimitations have changed (198 -> 243 wards, and the new Greater Bengaluru
# Authority corporations), so never mix versions across years.
WARDS_FILE = DATA_RAW / "wards.geojson"
WARD_ID_COL = "ward_id"        # created in 01 if missing
WARD_NAME_COL = "ward_name"    # rename to match your file's column
CRS_GEO = "EPSG:4326"
CRS_PROJ = "EPSG:32643"        # UTM 43N, metres (for distances / IDW)

# --- Time window ------------------------------------------------------------
START_YEAR = 2022
END_YEAR = 2026
LAST_COMPLETE_QUARTER = "2026Q3"   # today is mid Nov 2026, so Q4 is incomplete

# --- Google Earth Engine ----------------------------------------------------
GEE_PROJECT = "your-gee-cloud-project-id"   # <-- edit
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
CLOUDSCORE_COLLECTION = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
CLOUDSCORE_MIN = 0.6               # cs_cdf threshold; higher = stricter
L8_COLLECTION = "LANDSAT/LC08/C02/T1_L2"
L9_COLLECTION = "LANDSAT/LC09/C02/T1_L2"
DYNAMIC_WORLD = "GOOGLE/DYNAMICWORLD/V1"
CHIRPS = "UCSB-CHG/CHIRPS/DAILY"
SCALE_M = 30                       # reduction scale (Landsat native)
MIN_VALID_FRACTION = 0.5           # drop ward-quarters with too few valid pixels

# --- Air quality ------------------------------------------------------------
# bbox = lon_min, lat_min, lon_max, lat_max  (covers BBMP/GBA area)
BBOX = (77.40, 12.80, 77.82, 13.18)
OPENAQ_BASE = "https://api.openaq.org/v3"
# Put your key in the environment:  export OPENAQ_API_KEY=...
IDW_POWER = 2.0
MIN_DAYS_PER_QUARTER = 55          # ~60% of a quarter's days
