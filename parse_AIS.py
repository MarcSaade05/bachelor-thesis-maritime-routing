import pandas as pd
import sys
import folium
from pathlib import Path


def _load_ais(path):
    """
    Load AIS data from either CSV or Parquet.
    This makes the helper script work with both the older CSV files
    and the new 2024 GeoParquet files you downloaded.
    """
    path = Path(path)
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
        
        # Map column names to expected format (2024 files use lowercase)
        column_mapping = {}
        if 'vessel_name' in df.columns and 'VesselName' not in df.columns:
            column_mapping['vessel_name'] = 'VesselName'
        if 'base_date_time' in df.columns and 'BaseDateTime' not in df.columns:
            column_mapping['base_date_time'] = 'BaseDateTime'
        if 'sog' in df.columns and 'SOG' not in df.columns:
            column_mapping['sog'] = 'SOG'
        if 'cog' in df.columns and 'COG' not in df.columns:
            column_mapping['cog'] = 'COG'
        
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # Extract LAT/LON from geometry column if it exists (GeoParquet format)
        if 'geometry' in df.columns and 'LAT' not in df.columns:
            try:
                import geopandas as gpd
                from shapely import wkb
                # Convert WKB geometry to shapely geometries
                df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(x) if isinstance(x, bytes) else x)
                gdf = gpd.GeoDataFrame(df, geometry='geometry')
                df['LAT'] = gdf.geometry.y
                df['LON'] = gdf.geometry.x
            except ImportError:
                # geopandas not installed - user needs to extract coordinates separately
                pass
            except Exception as e:
                # Other error - pass silently, user can extract manually
                pass
        
        return df
    else:
        # Fallback: assume CSV
        return pd.read_csv(path)


def list_vessels(data_file):
    """
    Return a sorted list of all unique vessel names in the dataset.
    Works with both CSV and Parquet files.
    """
    df = _load_ais(data_file)
    vessels = sorted(df["VesselName"].dropna().unique())
    return vessels


def extract_trajectory(data_file, vessel_name):
    """
    Extracts the trajectory of a vessel from an AIS-like CSV file.

    Parameters
    ----------
    data_file : str
        Path to the CSV or Parquet file.
    vessel_name : str
        Vessel name to extract.

    Returns
    -------
    pd.DataFrame
        DataFrame with ordered trajectory (by BaseDateTime).
    """
    # Load the dataset (CSV or Parquet)
    df = _load_ais(data_file)

    # Ensure BaseDateTime is parsed as datetime
    if not pd.api.types.is_datetime64_any_dtype(df["BaseDateTime"]):
        df["BaseDateTime"] = pd.to_datetime(df["BaseDateTime"])

    # Filter by vessel name (case-insensitive match)
    vessel_df = df[df["VesselName"].str.upper() == vessel_name.upper()].copy()

    if vessel_df.empty:
        raise ValueError(f"No trajectory found for vessel: {vessel_name}")

    # Sort by timestamp
    vessel_df.sort_values(by='BaseDateTime', inplace=True)

    # Reset index for convenience
    vessel_df.reset_index(drop=True, inplace=True)

    # Keep only the essentials for trajectory (you can extend as needed)
    trajectory = vessel_df[["BaseDateTime", "LAT", "LON", "SOG", "COG"]]

    return trajectory

def plot_trajectory_on_map(trajectory, map_file="trajectory_map.html"):
    """
    Plot trajectory points on an interactive map and save to HTML.
    """
    # Center map on the mean coordinates
    lat_center = trajectory["LAT"].mean()
    lon_center = trajectory["LON"].mean()

    m = folium.Map(location=[lat_center, lon_center], zoom_start=10)

    # Add polyline for trajectory
    coords = trajectory[["LAT", "LON"]].values.tolist()
    folium.PolyLine(coords, color="blue", weight=2.5, opacity=1).add_to(m)

    # Add start and end markers
    folium.Marker(coords[0], popup="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[-1], popup="End", icon=folium.Icon(color="red")).add_to(m)

    # Save map
    m.save(map_file)
    print(f"Map saved to {map_file}")

# Example usage (only runs when script is executed directly, not when imported):
if __name__ == "__main__":
    if len(sys.argv) > 1:
        ship_name = "PILOT BOAT SPRING PT"
        traj = extract_trajectory(sys.argv[1], ship_name)
        print("course for ship % :\n", ship_name, traj)
    else:
        print("Usage: python parse_AIS.py <data_file>")
