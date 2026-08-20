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

def engineer_osm_features(input_csv_path=None):
    """
    Phase 6: Parse OSM road attributes into standardized numeric and boolean features,
    and generate feature availability flags.
    """
    ensure_directories()
    
    if input_csv_path is None:
        input_csv_path = OSM_DATA_DIR / "bengaluru_osm_master_roads.csv"
    else:
        input_csv_path = Path(input_csv_path)

    print(f"[Phase 6 - Feature Eng] Loading OSM master roads from: {input_csv_path}")
    df = pd.read_csv(input_csv_path, low_memory=False)

    print(f"[Phase 6 - Feature Eng] Raw OSM records count: {len(df)}")

    # 1. Parse Lanes (lanes_num & lanes_available)
    def parse_lanes(val):
        if pd.isna(val):
            return 1, 0  # default 1 lane, availability 0
        try:
            # Clean string inputs like '2', '2;3', '1'
            val_str = str(val).split(';')[0].strip()
            num = int(float(val_str))
            return max(1, num), 1
        except Exception:
            return 1, 0

    lanes_res = [parse_lanes(v) for v in df['lanes']]
    df['lanes_num'] = [r[0] for r in lanes_res]
    df['lanes_available'] = [r[1] for r in lanes_res]

    # 2. Parse Length (length_m)
    df['length_m'] = pd.to_numeric(df['length'], errors='coerce').fillna(50.0)

    # 3. Parse Width (width_m & width_available)
    def parse_width(val):
        if pd.isna(val):
            return 6.0, 0
        try:
            val_str = str(val).replace('m', '').split(';')[0].strip()
            w = float(val_str)
            return max(2.0, w), 1
        except Exception:
            return 6.0, 0

    width_res = [parse_width(v) for v in df.get('width', pd.Series([np.nan]*len(df)))]
    df['width_m'] = [r[0] for r in width_res]
    df['width_available'] = [r[1] for r in width_res]

    # 4. Parse Maxspeed (maxspeed_kmh & speed_available)
    def parse_speed(val):
        if pd.isna(val):
            return 40.0, 0
        try:
            val_str = str(val).replace('km/h', '').replace('mph', '').split(';')[0].strip()
            s = float(val_str)
            return max(10.0, min(120.0, s)), 1
        except Exception:
            return 40.0, 0

    speed_res = [parse_speed(v) for v in df.get('maxspeed', pd.Series([np.nan]*len(df)))]
    df['maxspeed_kmh'] = [r[0] for r in speed_res]
    df['speed_available'] = [r[1] for r in speed_res]

    # 5. Parse Boolean Flags (oneway, junction, bridge, tunnel)
    df['oneway_flag'] = np.where(df.get('oneway', pd.Series(['no']*len(df))).astype(str).str.lower().isin(['yes', 'true', '1']), 1, 0)
    df['junction_flag'] = np.where(df.get('junction', pd.Series([np.nan]*len(df))).notna(), 1, 0)
    df['bridge_flag'] = np.where(df.get('bridge', pd.Series(['no']*len(df))).astype(str).str.lower().isin(['yes', 'true', '1']), 1, 0)
    df['tunnel_flag'] = np.where(df.get('tunnel', pd.Series(['no']*len(df))).astype(str).str.lower().isin(['yes', 'true', '1']), 1, 0)

    # Save output
    output_path = OSM_DATA_DIR / "bengaluru_osm_featured_roads.csv"
    output_features_dir = ROAD_FEATURES_OUTPUT_DIR / "osm_featured_roads.csv"

    df.to_csv(output_path, index=False)
    df.to_csv(output_features_dir, index=False)

    print("\n" + "=" * 60)
    print(" PHASE 6: OSM FEATURE ENGINEERING COMPLETE")
    print("=" * 60)
    print(f" Total Featured Roads: {len(df)}")
    print(f" Output Saved to: {output_path}")
    print("\nSample Featured Attributes:")
    print(df[['road_id', 'highway', 'lanes_num', 'length_m', 'width_m', 'maxspeed_kmh', 'oneway_flag', 'junction_flag', 'bridge_flag', 'tunnel_flag']].head())
    print("=" * 60 + "\n")

    return df

if __name__ == "__main__":
    engineer_osm_features()
