"""
Extract per-ship AIS tracks for JULY 2024, but ONLY in the focus zone.

- Lit les daily parquets dans data/raw/2024-07
- Ajoute LAT/LON si nécessaire
- Garde uniquement les points dans la bbox focus (15–40N, -100 à -60W)
- Pour chaque MMSI, écrit un Parquet dans data/processed/by_ship_jul
  (les fichiers sont mis à jour jour par jour, pas besoin de tout garder en mémoire)
"""

from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# --- Config ---
BASE_DIR = Path("/users/eleves-b/2023/marc.saade/bachelor-thesis/thesis")

# Daily parquets de juillet
RAW_DIR = BASE_DIR / "data" / "raw" / "2024-07"

# Par fichiers par navire pour JUILLET (FOCUS ZONE uniquement)
OUT_DIR = BASE_DIR / "data" / "processed" / "by_ship_jul"

# Date range (inclusive) pour JUILLET
DATE_START = datetime(2024, 7, 1)
DATE_END   = datetime(2024, 7, 14)

# Même bbox que pour le graphe
FOCUS_LAT = (15.0, 40.0)
FOCUS_LON = (-100.0, -60.0)


def _add_lat_lon(df: pd.DataFrame) -> pd.DataFrame:
    """Add LAT/LON columns from geometry (WKB). Uses geopandas if needed."""
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
        raise RuntimeError(
            "Need geopandas and shapely to extract LAT/LON from geometry. "
            "Install: conda install -c conda-forge geopandas"
        ) from e
    return df


def _daily_parquet_path(d: datetime) -> Path:
    """Path for a daily parquet file (e.g. ais-2024-07-01.parquet)."""
    name = f"ais-{d.year:04d}-{d.month:02d}-{d.day:02d}.parquet"
    p = RAW_DIR / name
    if p.exists():
        return p
    return p  # on renvoie quand même le chemin, même si inexistant


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    date = DATE_START
    paths = []
    while date <= DATE_END:
        p = _daily_parquet_path(date)
        if p.exists():
            paths.append(p)
        date += timedelta(days=1)

    if not paths:
        print("No daily parquet files found in date range. Check RAW_DIR and dates.")
        return

    print(f"Found {len(paths)} daily file(s). Processing day by day in focus zone...")

    n_rows_total = 0
    mmsi_seen = set()

    for p in paths:
        print(f"\n=== Processing {p.name} ===")
        df = pd.read_parquet(p)

        # Garder seulement les colonnes utiles pour ce projet
        cols_keep = [c for c in df.columns if c in {"mmsi", "base_date_time", "LAT", "LON", "geometry"}]
        df = df[cols_keep]

        df = _add_lat_lon(df)

        # Filtre spatial: focus zone uniquement (on ne garde pas tout le monde)
        mask = (
            (df["LAT"] >= FOCUS_LAT[0]) & (df["LAT"] <= FOCUS_LAT[1]) &
            (df["LON"] >= FOCUS_LON[0]) & (df["LON"] <= FOCUS_LON[1])
        )
        df = df[mask].copy()

        if df.empty:
            print("  No points in focus zone for this day.")
            continue

        # Trier par temps
        df = df.sort_values(["mmsi", "base_date_time"])

        n_rows_total += len(df)
        print(f"  Kept {len(df):,} rows in focus zone, {df['mmsi'].nunique():,} ships")

        # Mettre à jour les fichiers par navire, un MMSI à la fois (pour limiter la RAM)
        for mmsi, grp in df.groupby("mmsi"):
            out_path = OUT_DIR / f"MMSI_{mmsi}.parquet"
            if out_path.exists():
                # Lire l'existant, concaténer, réécrire
                old = pd.read_parquet(out_path)
                new_df = pd.concat([old, grp], ignore_index=True)
                new_df = new_df.sort_values("base_date_time").reset_index(drop=True)
                new_df.to_parquet(out_path, index=False)
            else:
                grp.to_parquet(out_path, index=False)
            mmsi_seen.add(mmsi)

    print(f"\nTotal rows kept in focus zone (toutes dates): {n_rows_total:,}")
    print(f"Total distinct MMSI with points in focus zone: {len(mmsi_seen):,}")
    print(f"Ship files written/updated in {OUT_DIR}")


if __name__ == "__main__":
    main()