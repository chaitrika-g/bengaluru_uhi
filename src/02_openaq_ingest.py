"""Step 2: Pull daily PM2.5 / PM10 from OpenAQ v3 for stations in the Bengaluru bbox.

Needs a free API key:  https://explore.openaq.org  ->  export OPENAQ_API_KEY=...
Output:
  data/raw/aq_stations.csv        station id, name, lat, lon, parameters
  data/raw/aq_daily.csv           station_id, parameter, date, value (ug/m3)

CPCB fallback: if OpenAQ coverage is thin for your window, download station-level
daily data from the CPCB CCR portal (https://airquality.cpcb.gov.in/ccr/) and
save it in the same long format as aq_daily.csv -- steps 3+ only read that file.

NOTE: verify endpoint/field names against https://docs.openaq.org if a call fails;
the API is versioned and response shapes can change.
"""
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C

PARAMS = {"pm25": "pm25", "pm10": "pm10"}


def session():
    key = os.environ.get("OPENAQ_API_KEY")
    if not key:
        raise SystemExit("Set OPENAQ_API_KEY in your environment first.")
    s = requests.Session()
    s.headers.update({"X-API-Key": key})
    return s


def get(s, path, params=None, retries=5):
    for i in range(retries):
        r = s.get(f"{C.OPENAQ_BASE}{path}", params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(2 ** i)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate-limited too long on {path}")


def paged(s, path, params):
    page = 1
    while True:
        p = dict(params, limit=1000, page=page)
        js = get(s, path, p)
        res = js.get("results", [])
        yield from res
        if len(res) < 1000:
            break
        page += 1
        time.sleep(0.3)


def list_stations(s):
    bbox = ",".join(map(str, C.BBOX))
    rows = []
    for loc in paged(s, "/locations", {"bbox": bbox}):
        for sen in loc.get("sensors", []):
            pname = sen.get("parameter", {}).get("name")
            if pname in PARAMS:
                rows.append({
                    "station_id": loc["id"], "station_name": loc.get("name"),
                    "lat": loc["coordinates"]["latitude"],
                    "lon": loc["coordinates"]["longitude"],
                    "sensor_id": sen["id"], "parameter": PARAMS[pname],
                })
    return pd.DataFrame(rows)


def sensor_daily(s, sensor_id, start, end):
    out = []
    for r in paged(s, f"/sensors/{sensor_id}/days",
                   {"datetime_from": start, "datetime_to": end}):
        out.append({
            "date": r["period"]["datetimeFrom"]["utc"][:10],
            "value": r["value"],
        })
    return out


def main():
    s = session()
    st = list_stations(s)
    st.to_csv(C.DATA_RAW / "aq_stations.csv", index=False)
    print(f"{st.station_id.nunique()} stations, {len(st)} sensors")

    start = f"{C.START_YEAR}-01-01T00:00:00Z"
    end = pd.Timestamp.today().strftime("%Y-%m-%dT00:00:00Z")
    rows = []
    for _, r in st.iterrows():
        for d in sensor_daily(s, r.sensor_id, start, end):
            rows.append({"station_id": r.station_id, "parameter": r.parameter, **d})
        print("done sensor", r.sensor_id, r.parameter)
        time.sleep(0.3)
    df = pd.DataFrame(rows)
    df = df[df.value.between(0, 1500)]          # drop negatives / absurd spikes
    df.to_csv(C.DATA_RAW / "aq_daily.csv", index=False)
    print("saved", len(df), "station-days")


if __name__ == "__main__":
    main()
