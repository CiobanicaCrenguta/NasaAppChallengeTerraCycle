# TerraCycle

A crop-rotation assistant for farmers, built for the NASA Space Apps Challenge. The farmer opens the app, asks a question in plain words, and gets one direct answer based on NASA Earth observations for their own land.

- `app/` is the phone app (Expo, React Native, TypeScript).
- `backend/` is the server (Python, FastAPI) and the data download script.
- `STATUS.md` holds the project status and the work plan (in Romanian).

## Run it

```
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

```
cd app
npm install --legacy-peer-deps
npx expo start
```

The app reads the server address from `EXPO_PUBLIC_API_URL` in `app/.env` (see `app/.env.example`). Without it, the app runs on sample data.

## Data

Every source is downloaded once per field by `backend/field_pull.py`, summed to weeks, and saved in `backend/data/baked/<field id>/`:

- `profile.json`: weekly series per year for each source, soil and relief numbers, and the status of each source.
- `zones.geojson`: Sentinel-2 10 m cells, each compared with the rest of the field.
- `relief.geojson`: NASADEM 30 m cells with slope and height.

```
cd backend
.venv\Scripts\earthengine authenticate --auth_mode=localhost   # once, for the Earth Engine sources
.venv\Scripts\python field_pull.py                              # everything
.venv\Scripts\python field_pull.py --only power,soil            # only the sources that need no account
```

Earth Engine sources run under the Google Cloud project `terracycle-514620`. A source that could not be downloaded is marked `pending` in `profile.json`, and the app then says it has no reading rather than guessing.

### Sources in use

"Scope" says what a number describes: the field itself, or the wider area around it. The app shows this label next to every number.

| Source | Version or collection | What we take | Period | Grid | Scope | Access |
|---|---|---|---|---|---|---|
| [NASA POWER](https://power.larc.nasa.gov/) | Daily API v2, AG community ([docs](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)) | `T2M_MAX`, `T2M_MIN`, `T2MDEW`, `WS2M`, `ALLSKY_SFC_SW_DWN`, `PRECTOTCORR`, `GWETROOT` | 2001–2020 for the baseline; to today for the live server | about 50 km | area | API, no account |
| [MODIS Terra Vegetation Indices](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1) | `MODIS/061/MOD13Q1` (Collection 6.1) | `NDVI` × 0.0001, kept where `SummaryQA` is 0 or 1 | 2001–2020 | 250 m, 16 days | area | Earth Engine |
| [SMAP L4 Global Soil Moisture](https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL4SMGP_008) | `NASA/SMAP/SPL4SMGP/008` (version 8) | `sm_rootzone` | 2015–2020 | about 9 km, 3 hours | area | Earth Engine |
| [GPM IMERG](https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_V07) | `NASA/GPM_L3/IMERG_V07` (version 07) | `precipitation`, summed to days, for heavy-rain days | 2001–2020 | about 10 km, 30 minutes | area | Earth Engine |
| [NASADEM](https://developers.google.com/earth-engine/datasets/catalog/NASA_NASADEM_HGT_001) | `NASA/NASADEM_HGT/001` (SRTM reprocessed by NASA) | `elevation`, and slope computed from it | February 2000 | 30 m | field | Earth Engine |
| [Harmonized Landsat Sentinel-2 (HLS)](https://developers.google.com/earth-engine/datasets/catalog/NASA_HLS_HLSL30_v002) | `NASA/HLS/HLSL30/v002` and [`NASA/HLS/HLSS30/v002`](https://developers.google.com/earth-engine/datasets/catalog/NASA_HLS_HLSS30_v002) (version 2.0) | NDVI from red and near-infrared, clouds removed with `Fmask` | 2013–today | 30 m | field | Earth Engine |
| [Copernicus Sentinel-2](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED) (ESA) | `COPERNICUS/S2_SR_HARMONIZED` (Level-2A surface reflectance) | NDVI from `B8` and `B4`, clouds removed with `SCL` | 2017–today | 10 m | field | Earth Engine |
| [ISRIC SoilGrids](https://www.isric.org/explore/soilgrids) | 2.0 ([API](https://rest.isric.org/soilgrids/v2.0/docs)) | sand, silt, clay, pH, organic carbon, 0–30 cm | static | 250 m | area | API, no account |

MODIS is used only for the 20-year history of the area: one MODIS square is 6.25 ha and none fits inside our fields. Sentinel-2 is used for the map inside the field. HLS is NASA's own reading of the field.

Optional, not downloaded yet: [FAO GAEZ v4](https://gaez.fao.org/), to drop crops that do not suit the area.

Not used: ECOSTRESS (passes too rare), GEDI (measures forests), ERA5 and NLDAS/GLDAS (POWER already covers weather), and the sources that cover only the United States (USDA, SSURGO, CDL, PRISM, NAIP, NLCD, OpenET and the rest).

### Limits

- POWER, SMAP, IMERG and SoilGrids are model estimates or coarse grids. They describe the area, not one field.
- Satellites show how green a field is. They do not show why. The app never names a cause as a fact.
- The thresholds in `field_pull.py` (heavy rain 20 mm, bare soil NDVI 0.25, steep 5°, weaker cell 10%) are our own choices and have not been checked by an agronomist.
- Field outlines are real. Field names, crops and crop history are sample values.
