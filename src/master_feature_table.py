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

def generate_master_feature_table(input_csv_path=None):
    """
    Phase 16: Consolidate all road segment attributes, accident risk, complexity score,
    simulated/live damage, traffic, weather, and travel speed into a single dataset.
    """
    ensure_directories()
    
    if input_csv_path is None:
        input_csv_path = OSM_DATA_DIR / "bengaluru_roads_with_accident_risk.csv"
    else:
        input_csv_path = Path(input_csv_path)

    print(f"[Phase 16 - Master Table] Loading associated roads from: {input_csv_path}")
    df = pd.read_csv(input_csv_path, low_memory=False)

    print(f"[Phase 16 - Master Table] Total roads: {len(df)}")

    # Add default/simulated baseline features for full ML feature matrix
    np.random.seed(42)
    
    # Road damage score simulation (until GPU inference on full dataset)
    if 'road_damage_score' not in df.columns:
        df['road_damage_score'] = np.random.choice([0.0, 15.0, 35.0, 65.0], size=len(df), p=[0.70, 0.15, 0.10, 0.05])

    # Dynamic Traffic & Weather baseline fields
    if 'traffic_speed' not in df.columns:
        df['traffic_speed'] = np.random.uniform(15.0, 50.0, size=len(df)).round(1)
        df['congestion_level'] = np.round(1.0 - (df['traffic_speed'] / 60.0), 2)
        df['traffic_condition'] = np.where(df['congestion_level'] > 0.6, 'HEAVY', 'MODERATE')

    if 'temperature' not in df.columns:
        df['temperature'] = 26.5
        df['precipitation'] = 0.0
        df['visibility'] = 10.0
        df['weather_condition'] = 'CLEAR'

    # Travel Speed (User parameter feature)
    if 'travel_speed_kmh' not in df.columns:
        df['travel_speed_kmh'] = 50.0

    # Prototype Synthetic Target Risk Class for Training/Ablation setup
    # Risk Score combining available indicators defensibly
    hist_risk = df['Historical_Area_Accident_Risk'].fillna(100.0)
    norm_hist = np.clip(hist_risk / 1500.0 * 30.0, 0, 30)
    norm_comp = np.clip(df['road_complexity'] / 100.0 * 25.0, 0, 25)
    norm_dmg = np.clip(df['road_damage_score'] / 100.0 * 25.0, 0, 25)
    norm_cong = np.clip(df['congestion_level'] * 20.0, 0, 20)

    calculated_risk = norm_hist + norm_comp + norm_dmg + norm_cong
    df['risk_score'] = np.clip(calculated_risk, 0.0, 100.0).round(2)

    def assign_risk_label(s):
        if s >= 81.0:
            return 3  # Very High
        elif s >= 61.0:
            return 2  # High
        elif s >= 31.0:
            return 1  # Moderate
        else:
            return 0  # Low

    df['risk_class'] = df['risk_score'].apply(assign_risk_label)

    # Save output
    output_path = OSM_DATA_DIR / "road_master_features.csv"
    output_features_dir = ROAD_FEATURES_OUTPUT_DIR / "road_master_features.csv"

    df.to_csv(output_path, index=False)
    df.to_csv(output_features_dir, index=False)

    print("\n" + "=" * 60)
    print(" PHASE 16: MASTER ROAD FEATURE TABLE GENERATION COMPLETE")
    print("=" * 60)
    print(f" Total Master Road Features: {len(df)} rows, {df.shape[1]} columns")
    print(f" Output Saved to: {output_path}")
    print("\nSample Master Feature Matrix:")
    print(df[['road_id', 'name', 'road_complexity', 'Accident_Data_Available', 'Historical_Area_Accident_Risk', 'road_damage_score', 'traffic_speed', 'risk_score', 'risk_class']].head())
    print("=" * 60 + "\n")

    return df

if __name__ == "__main__":
    generate_master_feature_table()
