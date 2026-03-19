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

We use the 2024 AIS broadcast data for U.S. waters, provided as daily GeoParquet files.

- Project: `ais-vessel-traffic`  
- Daily 2024 parquet file list:  
  https://github.com/ocm-marinecadastre/ais-vessel-traffic/blob/main/data/daily-2024-parquet-files.md

For this thesis we download **14 days in January** and **14 days in July**, for example:

- `ais-2024-01-01.parquet`, …, `ais-2024-01-14.parquet`
- `ais-2024-07-01.parquet`, …, `ais-2024-07-14.parquet`

You can either download them manually from the links in the file above or script it using the listed Azure URLs.

### 1.2 Copernicus Marine Service: currents and SST

We use the **GLOBAL_ANALYSISFORECAST_PHY_001_024** global ocean physics product:

- Product page:  
  https://data.marine.copernicus.eu/product/GLOBAL_ANALYSISFORECAST_PHY_001_024

Download daily surface fields covering at least:

- Latitude: 15°N–40°N  
- Longitude: -100°–-60°

For each of the two study windows (Jan 1–14 and Jul 1–14), we keep:

- currents: `currents_jan2024.nc`, `currents_jul2024.nc`
- temperature: `temperature_jan2024.nc`, `temperature_jul2024.nc`

### 1.3 Port list (hand-crafted)

The list of reference ports inside the focus zone is stored in:

- `data/ports_focus_zone.csv`

This file was created specifically for this thesis and contains port identifiers, names, and geographic coordinates used to define port-to-port routing scenarios.

---

## 2. Repository contents (file-by-file)

This section explains what each notebook and script does and how it fits in the overall workflow.

### 2.1 `parse_AIS.py`

Utility script used to parse and lightly clean AIS input files before more specialised preprocessing.  
It centralises common parsing logic (column names, datetime conversions, etc.) used by other scripts.

---

### 2.2 `extract_routes_by_ship.py` (January)  
### 2.3 `extract_routes_by_ship_jul.py` (July)

**Goal:** convert raw daily AIS parquet batches into **trajectory-consistent per-vessel files**.

Main steps:

1. Read the January (or July) parquet files from disk.
2. Select the relevant AIS columns (MMSI, timestamp, latitude, longitude, and possibly others).
3. Group messages by MMSI so that each output file corresponds to a single vessel.
4. Within each MMSI group:
   - sort records chronologically,
   - drop clearly invalid or incomplete entries,
   - optionally apply simple filters (minimum number of points, etc.).
5. Save the cleaned, ordered trajectory for each vessel (e.g. as a parquet/CSV file) for downstream graph construction.

These scripts guarantee that the subsequent graph-building notebooks always see **ordered AIS tracks per vessel**, which is essential to construct physically meaningful transitions.

---

### 2.4 `Data_preprocessing.ipynb`

**Goal:** exploratory analysis and quality checks on the AIS data.

This notebook:

- inspects basic schema (columns, dtypes, missing values),
- computes distributions of speed, course, vessel types, etc.,
- plots example trajectories for individual ships,
- builds the histogram of time gaps between consecutive AIS messages (used in the thesis to justify the approximate one-minute sampling assumption).

It is recommended to run this notebook first when working with new AIS batches to ensure the raw data looks reasonable.

---

### 2.5 `build_zone_graph.ipynb` (January)  
### 2.6 `build_zone_graph_jul.ipynb` (July)

**Goal:** build the focus-zone maritime graphs (January and July) from the cleaned per-vessel trajectories.

These notebooks:

1. Define the geographic focus zone:
   - Latitude: 15°–40°N
   - Longitude: -100°–-60°.
2. Define the grid:
   - `LAT_STEP = 0.01`, `LON_STEP = 0.01` (≈ 1 km cells).
3. Load the per-MMSI trajectory files produced by `extract_routes_by_ship*.py`.
4. Snap each AIS point to its grid cell and build a **directed transition** whenever a vessel moves from one cell to a different cell between two consecutive timestamps.
5. Aggregate, for each edge `(i,j)`:
   - transition count `count_ij`,
   - total sailed distance `total_dist_km_ij`.
6. Remove edges with unrealistic average distance (e.g. > 200 km), which usually correspond to long gaps or data artefacts.
7. Restrict the resulting graph to the **largest weakly connected component** to ensure that routing and learning operate on a single coherent network.
8. Save the final graphs (e.g. `graph_focus_zone.pkl`, `graph_focus_zone_jul.pkl`) for later use.
9. Produce diagnostic figures (scatter of all nodes, focus-zone visualisation) used in the thesis.

These two notebooks are the bridge between raw AIS trajectories and the graph objects used by the routing and GNN experiments.

---

### 2.7 `build_zone_graph_executed.ipynb`  
### 2.8 `build_zone_graph_jul_executed.ipynb`

Executed versions of the graph-building notebooks, kept as reproducibility logs.  
They contain the actual outputs and printed summaries from a complete run.

---

### 2.9 `GNN_model.ipynb`

**Goal:** exploration of the graph structure and preliminary modelling ideas.

This notebook is used to explore the overall points in our dataset and visualize the whole zone around the US, not only the focus zone.

It plays a diagnostic/experimental role rather than being part of the strict reproduction pipeline.

---

### 2.10 `GNN_training.ipynb`

Early baseline GNN training notebook used to prototype the training loop, loss functions, and evaluation.  
The final thesis results are based on `GNN_training_jan.ipynb` and `GNN_training_jul.ipynb`, but this file remains as an intermediate step in model development.

---

### 2.11 `GNN_training_jan.ipynb` (January experiments)

**Goal:** implement the full January experiment from focus-zone graph to final metrics and figures.

Main stages:

1. **Graph and feature loading**
   - Load the January focus-zone graph (`graph_focus_zone.pkl`).
   - Load averaged currents and temperature (`currents_jan2024.nc`, `temperature_jan2024.nc`).
   - Interpolate environmental fields to node locations.
   - Build node feature vectors (lat, lon, u\_cur, v\_cur, SST, log(1+deg\_in), log(1+deg\_out)).

2. **Heuristic routing baseline**
   - Define edge cost  
     \( w_{ij} = \frac{\texttt{avg\_dist\_km}_{ij}}{1 + \alpha \log(1 + \texttt{count}_{ij})} \).
   - Load `ports_focus_zone.csv` and snap port coordinates to nearest graph nodes.
   - Compute Dijkstra routes for each port pair and log distance and cost (used in the thesis tables and figures).

3. **Pseudo-label generation**
   - Label edges on any Dijkstra path as positives for the edge classification task.
   - Identify “interesting” nodes (ports + branching nodes) and label those on at least one path as positive for the node classification task.
   - Sample negative edges to control class imbalance.

4. **Dataset construction (PyTorch Geometric)**
   - Convert to a `Data` object with `x`, `edge_index`, `edge_label_index`, `edge_label`, and node labels.
   - Create train/validation/test splits with a 70%/15%/15% ratio.

5. **Model training and evaluation**
   - Train edge-level GCN (2-layer GCN encoder + MLP edge decoder) and report AUC + threshold metrics.
   - Train node-level GCN (2-layer GCN + linear node classifier) and report AUC + metrics.
   - Implement GPU training with CPU fallback when memory is limited.

6. **Figure generation**
   -Dijkstra route plots for Miami–New York.
   - edge and node probability maps used in Section 5 of the thesis.

---

### 2.12 `GNN_training_jul.ipynb` (July experiments)

Same structure as `GNN_training_jan.ipynb`, but applied to the July focus-zone graph and July Copernicus fields.  
Using the same architecture and training protocol makes the January vs July comparison fair.

---

## 3. How to reproduce the main results

1. **Download data**

   - AIS 2024 daily parquets for the chosen January and July dates  
     (see Section 1.1 and NOAA `ais-vessel-traffic` GitHub listing).
   - Copernicus currents and SST netCDF files for the same periods  
     (see Section 1.2).
   - Place them in a directory where the notebooks can find them, or update path variables accordingly.
