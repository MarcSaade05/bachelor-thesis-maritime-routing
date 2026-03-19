# Seasonal Optimal Maritime Routing Using Graph Neural Networks

This repository contains the code used in the Bachelor thesis **“Seasonal Optimal Maritime Routing Using Graph Neural Networks”**.  
It covers the full pipeline from raw AIS and Copernicus data to:

- monthly maritime graphs (January / July 2024),
- heuristic Dijkstra routing between ports,
- edge and node pseudo-label generation,
- GCN training and evaluation,
- production of the figures reported in the thesis.

---

## 1. Data sources

### 1.1 AIS vessel traffic (NOAA Marine Cadastre)

We use the 2024 AIS broadcast data for U.S. waters, provided as daily GeoParquet files:

- Project: `ais-vessel-traffic`
- Daily 2024 parquet files listing:  
  `https://github.com/ocm-marinecadastre/ais-vessel-traffic/blob/main/data/daily-2024-parquet-files.md`

For this thesis we download **14 days in January** and **14 days in July**, e.g.:

- `ais-2024-01-01.parquet`, …, `ais-2024-01-14.parquet`
- `ais-2024-07-01.parquet`, …, `ais-2024-07-14.parquet`

You can either download them manually from the links in the file above or script it using the listed Azure URLs.

### 1.2 Copernicus Marine Service: currents and SST

We use the **GLOBAL_ANALYSISFORECAST_PHY_001_024** product:

- Product page:  
  `https://data.marine.copernicus.eu/product/GLOBAL_ANALYSISFORECAST_PHY_001_024`

Download daily surface fields covering at least the latitude/longitude window:

- Latitude: 15°N–40°N  
- Longitude: -100°–-60°

For each of the two windows (Jan 1–14, Jul 1–14), we keep:

- currents: `currents_jan2024.nc`, `currents_jul2024.nc`
- temperature: `temperature_jan2024.nc`, `temperature_jul2024.nc`

---

## 2. Expected local directory layout

On the machine where you run the notebooks, the repository is assumed to live at:

```text
project_root/
  Data_preprocessing.ipynb
  GNN_model.ipynb
  GNN_training.ipynb
  GNN_training_jan.ipynb
  GNN_training_jul.ipynb
  build_zone_graph.ipynb
  build_zone_graph_executed.ipynb
  build_zone_graph_jul.ipynb
  build_zone_graph_jul_executed.ipynb
  extract_routes_by_ship.py
  extract_routes_by_ship_jul.py
  parse_AIS.py
  ...

  ais-2024-01-01.parquet
  ...
  ais-2024-01-14.parquet
  ais-2024-07-01.parquet
  ...
  ais-2024-07-14.parquet

  currents_jan2024.nc
  currents_jul2024.nc
  temperature_jan2024.nc
  temperature_jul2024.nc

  data/
    ports_focus_zone.csv
    (other small CSV metadata files, if any)
