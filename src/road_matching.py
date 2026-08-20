import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.neighbors import BallTree

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, OSM_DATA_DIR, ACCIDENT_DATA_DIR, ROAD_FEATURES_OUTPUT_DIR

EARTH_RADIUS_KM = 6371.0088

def match_accidents_to_roads(max_distance_threshold_km=5.0, road_csv_path=None, station_csv_path=None):
    """
    Phase 8 & 9: Spatial Association between Area-Level Station Accidents and OSM Roads
    using Haversine BallTree distance matching, with explicit missing data flags.
    """
    ensure_directories()
    
    if road_csv_path is None:
        road_csv_path = OSM_DATA_DIR / "bengaluru_osm_roads_with_complexity.csv"
    else:
        road_csv_path = Path(road_csv_path)

    if station_csv_path is None:
        station_csv_path = ACCIDENT_DATA_DIR / "bengaluru_stations_with_coordinates.csv"
    else:
        station_csv_path = Path(station_csv_path)

    print(f"[Phase 8 & 9 - Road Matching] Loading master roads from: {road_csv_path}")
    print(f"[Phase 8 & 9 - Road Matching] Loading stations from: {station_csv_path}")

    df_roads = pd.read_csv(road_csv_path, low_memory=False)
    df_stations = pd.read_csv(station_csv_path)

    df_stations_valid = df_stations.dropna(subset=['Latitude', 'Longitude']).copy()
    print(f" Total Master Roads: {len(df_roads)}")
    print(f" Valid Station Coordinates: {len(df_stations_valid)}")

    # Convert coordinates to radians (lat, lon)
    road_coords_rad = np.radians(df_roads[['Road_Latitude', 'Road_Longitude']].values)
    station_coords_rad = np.radians(df_stations_valid[['Latitude', 'Longitude']].values)

    # Build BallTree on station coordinates
    print(" Building BallTree on station coordinates...")
    tree = BallTree(station_coords_rad, metric='haversine')

    # Query nearest station for each road segment
    distances_rad, indices = tree.query(road_coords_rad, k=1)
    distances_km = distances_rad.flatten() * EARTH_RADIUS_KM
    nearest_station_idx = indices.flatten()

    nearest_stations = df_stations_valid.iloc[nearest_station_idx].reset_index(drop=True)

    # Assign Association Attributes
    df_roads['Association_Type'] = 'AREA_LEVEL_ASSOCIATION'
    df_roads['Nearest_Station'] = nearest_stations['Station'].values
    df_roads['Nearest_Station_Distance_km'] = np.round(distances_km, 3)
    
    # Phase 9: Set Accident_Data_Available flag and Historical_Area_Accident_Risk
    within_coverage = distances_km <= max_distance_threshold_km
    df_roads['Accident_Data_Available'] = np.where(within_coverage, 1, 0)
    
    # Fill Historical_Area_Accident_Risk with station total accidents if within coverage, else NaN
    df_roads['Historical_Area_Accident_Risk'] = np.where(
        within_coverage,
        nearest_stations['Total_Accidents'].values,
        np.nan
    )
    
    df_roads['Historical_Area_Fatality_Rate'] = np.where(
        within_coverage,
        nearest_stations['Fatality_Rate'].values,
        np.nan
    )

    coverage_count = df_roads['Accident_Data_Available'].sum()
    print(f"\n[Phase 8 & 9] Matching Summary:")
    print(f" - Max Coverage Radius: {max_distance_threshold_km} km")
    print(f" - Roads with Area Accident Data: {coverage_count} ({coverage_count / len(df_roads)*100:.1f}%)")
    print(f" - Roads without Accident Data (Accident_Data_Available = 0): {len(df_roads) - coverage_count}")

    # Save output
    output_path = OSM_DATA_DIR / "bengaluru_roads_with_accident_risk.csv"
    output_features_dir = ROAD_FEATURES_OUTPUT_DIR / "roads_with_accident_risk.csv"

    df_roads.to_csv(output_path, index=False)
    df_roads.to_csv(output_features_dir, index=False)

    print("\n" + "=" * 60)
    print(" PHASE 8 & 9: ACCIDENT TO ROAD ASSOCIATION COMPLETE")
    print("=" * 60)
    print(f" Output File Saved to: {output_path}")
    print("\nSample Associated Roads:")
    print(df_roads[['road_id', 'name', 'highway', 'Nearest_Station', 'Nearest_Station_Distance_km', 'Accident_Data_Available', 'Historical_Area_Accident_Risk']].head(10))
    print("=" * 60 + "\n")

    return df_roads

if __name__ == "__main__":
    match_accidents_to_roads()
