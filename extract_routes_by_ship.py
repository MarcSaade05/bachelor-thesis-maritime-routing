"""
Extract full routes per ship (MMSI) from daily AIS Parquet files.

Reads all daily parquets in a date range, adds LAT/LON from geometry,
groups by MMSI, and saves one Parquet per ship to data/processed/by_ship/
so you can load a single ship's full route across days.

Usage:
  python extract_routes_by_ship.py

Edit BASE_DIR, DATE_START, DATE_END at the top of this file, then run.
"""

from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# --- Config: edit these ---
BASE_DIR = Path("/users/eleves-b/2023/marc.saade/bachelor-thesis/thesis")
# Put daily parquets in data/raw/ or leave them in BASE_DIR (script looks in both)
RAW_DIR = BASE_DIR  # Les parquet sont directement dans thesis/
OUT_DIR = BASE_DIR / "data" / "processed" / "by_ship"

# Date range (inclusive): only days that exist as ais-YYYY-MM-DD.parquet
DATE_START = datetime(2024, 1, 1)
DATE_END   = datetime(2024, 1, 14) # e.g. one week; use 31 for full January


def _add_lat_lon(df: pd.DataFrame) -> pd.DataFrame:
    """Add LAT/LON columns from geometry (WKB). Uses geopandas if available."""
    if "LAT" in df.columns and "LON" in df.columns:
        return df
    if "geometry" not in df.columns:
        return df
    try:
        import geopandas as gpd
        from shapely import wkb
        geom = df["geometry"].apply(lambda x: wkb.loads(x) if isinstance(x, bytes) else x)
        gdf = gpd.GeoDataFrame(df, geometry=geom)
        df = df.copy()
        df["LAT"] = gdf.geometry.y
        df["LON"] = gdf.geometry.x
    except Exception as e:
        raise RuntimeError("Need geopandas and shapely to extract LAT/LON from geometry. Install: conda install -c conda-forge geopandas") from e
    return df


def _daily_parquet_path(d: datetime) -> Path:
    """Path for a daily parquet file (e.g. ais-2024-01-01.parquet)."""
    name = f"ais-{d.year:04d}-{d.month:02d}-{d.day:02d}.parquet"
    for folder in (RAW_DIR, BASE_DIR):
        p = folder / name
        if p.exists():
            return p
    return BASE_DIR / name


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all daily files in range
    date = DATE_START
    paths = []
    while date <= DATE_END:
        p = _daily_parquet_path(date)
        if p.exists():
            paths.append(p)
        date += timedelta(days=1)

    if not paths:
        print("No daily parquet files found in date range. Check BASE_DIR/RAW_DIR and DATE_START/DATE_END.")
        return

    print(f"Found {len(paths)} daily file(s). Loading and adding LAT/LON...")
    chunks = []
    for p in paths:
        df = pd.read_parquet(p)
        df = _add_lat_lon(df)
        chunks.append(df)

    full = pd.concat(chunks, ignore_index=True)
    full = full.sort_values(["mmsi", "base_date_time"]).reset_index(drop=True)
    print(f"Total rows: {len(full):,}. Unique ships (MMSI): {full['mmsi'].nunique():,}.")

    # Save one parquet per ship
    for mmsi, grp in full.groupby("mmsi"):
        out_path = OUT_DIR / f"MMSI_{mmsi}.parquet"
        grp.to_parquet(out_path, index=False)

    print(f"Saved {full['mmsi'].nunique():,} ship files to {OUT_DIR}")


if __name__ == "__main__":
    main()
