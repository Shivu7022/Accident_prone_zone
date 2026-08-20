import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.cluster import DBSCAN

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, ACCIDENT_DATA_DIR, HOTSPOTS_OUTPUT_DIR

EARTH_RADIUS_KM = 6371.0088

def detect_accident_hotspots(eps_km=2.0, min_samples=2, input_csv_path=None):
    """
    Phase 4: Run Haversine BallTree DBSCAN to identify historical accident clusters
    at station/area level.
    """
    ensure_directories()
    
    if input_csv_path is None:
        input_csv_path = ACCIDENT_DATA_DIR / "bengaluru_stations_with_coordinates.csv"
    else:
        input_csv_path = Path(input_csv_path)

    print(f"[Phase 4 - DBSCAN Hotspots] Loading station coordinates from: {input_csv_path}")
    df = pd.read_csv(input_csv_path)
    
    # Filter to stations with valid coordinates
    df_valid = df.dropna(subset=['Latitude', 'Longitude']).copy()
    print(f"[Phase 4 - DBSCAN Hotspots] Valid geocoded stations for clustering: {len(df_valid)}")

    if len(df_valid) == 0:
        raise ValueError("No valid station coordinates available for DBSCAN clustering.")

    # Convert coordinates to radians for haversine metric
    coords_rad = np.radians(df_valid[['Latitude', 'Longitude']].values)
    kms_per_radian = EARTH_RADIUS_KM
    epsilon_rad = eps_km / kms_per_radian

    db = DBSCAN(eps=epsilon_rad, min_samples=min_samples, metric='haversine')
    df_valid['Cluster_ID'] = db.fit_predict(coords_rad)

    n_clusters = len(set(df_valid['Cluster_ID'])) - (1 if -1 in df_valid['Cluster_ID'] else 0)
    n_noise = list(df_valid['Cluster_ID']).count(-1)

    print(f"[Phase 4 - DBSCAN Hotspots] DBSCAN Clustering Results:")
    print(f" - Config: eps = {eps_km} km, min_samples = {min_samples}")
    print(f" - Clusters Found: {n_clusters}")
    print(f" - Noise Points (Unclustered Stations): {n_noise}")

    # Compute Hotspot Risk Metrics per Cluster
    cluster_stats = df_valid.groupby('Cluster_ID').agg(
        Cluster_Accidents=('Total_Accidents', 'sum'),
        Cluster_Fatalities=('Total_Killed', 'sum'),
        Station_Count=('Station', 'count')
    ).reset_index()

    # Define prototype Risk_Level
    # Note: These are area-level historical prototype thresholds
    def assign_risk_level(row):
        tot = row['Cluster_Accidents']
        if tot >= 3000:
            return 'VERY HIGH'
        elif tot >= 1500:
            return 'HIGH'
        elif tot >= 500:
            return 'MEDIUM'
        else:
            return 'LOW'

    cluster_stats['Hotspot_Risk'] = cluster_stats['Cluster_Accidents'] * 0.7 + cluster_stats['Cluster_Fatalities'] * 0.3
    cluster_stats['Risk_Level'] = cluster_stats.apply(assign_risk_level, axis=1)

    # Merge back to station dataframe
    df_result = pd.merge(df_valid, cluster_stats[['Cluster_ID', 'Hotspot_Risk', 'Risk_Level']], on='Cluster_ID', how='left')

    # Save outputs
    output_path = ACCIDENT_DATA_DIR / "accident_hotspots.csv"
    output_hotspots_dir = HOTSPOTS_OUTPUT_DIR / "accident_hotspots.csv"

    df_result.to_csv(output_path, index=False)
    df_result.to_csv(output_hotspots_dir, index=False)

    print("\n" + "=" * 60)
    print(" PHASE 4: DBSCAN ACCIDENT HOTSPOT ANALYSIS COMPLETE")
    print("=" * 60)
    print(f" Output File Saved to: {output_path}")
    print("\nCluster Risk Breakdown:")
    print(cluster_stats)
    print("=" * 60 + "\n")

    return df_result, cluster_stats

if __name__ == "__main__":
    detect_accident_hotspots()
