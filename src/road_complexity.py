import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, OSM_DATA_DIR, ROAD_FEATURES_OUTPUT_DIR
from src.feature_engineering import engineer_osm_features

def compute_road_complexity(input_csv_path=None):
    """
    Phase 7: Compute prototype Road Complexity Score (0-100) based on OSM features.
    
    Formula:
    Road_Complexity = 30 * Junction + 10 * OneWay + 30 * min(Lanes, 8) / 8 + 10 * Bridge + 10 * Tunnel
    """
    ensure_directories()
    
    if input_csv_path is None:
        input_csv_path = OSM_DATA_DIR / "bengaluru_osm_featured_roads.csv"
        if not Path(input_csv_path).exists():
            print("[Phase 7 - Complexity] Featured roads CSV not found. Running Phase 6 Feature Engineering...")
            df = engineer_osm_features()
        else:
            df = pd.read_csv(input_csv_path, low_memory=False)
    else:
        df = pd.read_csv(input_csv_path, low_memory=False)

    print(f"[Phase 7 - Complexity] Computing complexity score for {len(df)} road segments...")

    # Calculate complexity components
    junction = df['junction_flag']
    oneway = df['oneway_flag']
    lanes_clipped = np.clip(df['lanes_num'], 1, 8) / 8.0
    bridge = df['bridge_flag']
    tunnel = df['tunnel_flag']

    raw_complexity = (
        30.0 * junction +
        10.0 * oneway +
        30.0 * lanes_clipped +
        10.0 * bridge +
        10.0 * tunnel
    )

    df['road_complexity'] = np.clip(raw_complexity, 0.0, 100.0).round(2)

    # Save output
    output_path = OSM_DATA_DIR / "bengaluru_osm_roads_with_complexity.csv"
    output_features_dir = ROAD_FEATURES_OUTPUT_DIR / "osm_roads_with_complexity.csv"

    df.to_csv(output_path, index=False)
    df.to_csv(output_features_dir, index=False)

    print("\n" + "=" * 60)
    print(" PHASE 7: ROAD COMPLEXITY SCORE COMPUTATION COMPLETE")
    print("=" * 60)
    print(f" Total Processed Roads: {len(df)}")
    print(f" Mean Complexity Score: {df['road_complexity'].mean():.2f}")
    print(f" Max Complexity Score:  {df['road_complexity'].max():.2f}")
    print(f" Min Complexity Score:  {df['road_complexity'].min():.2f}")
    print(f" File Saved to: {output_path}")
    print("\nSample Road Complexity Scores:")
    print(df[['road_id', 'name', 'highway', 'lanes_num', 'oneway_flag', 'junction_flag', 'road_complexity']].head(10))
    print("=" * 60 + "\n")

    return df

if __name__ == "__main__":
    compute_road_complexity()
