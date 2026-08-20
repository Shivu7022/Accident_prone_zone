import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from shapely import wkt
import geopandas as gpd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, OSM_DATA_DIR, ROAD_FEATURES_OUTPUT_DIR

def process_osm_road_network(urban_csv_path=None, rural_csv_path=None):
    """
    Phase 5: Load Urban & Rural Bengaluru OSM roads, clean geometry, 
    generate representative Lat/Lon coordinates, and create unique road_ids.
    """
    ensure_directories()
    
    dataset_dir = PROJECT_ROOT / "dataset"
    if urban_csv_path is None:
        urban_csv_path = dataset_dir / "bengaluru_urban_roads.csv"
    else:
        urban_csv_path = Path(urban_csv_path)

    if rural_csv_path is None:
        rural_csv_path = dataset_dir / "bengaluru_rural_roads.csv"
    else:
        rural_csv_path = Path(rural_csv_path)

    print(f"[Phase 5 - OSM Network] Loading Urban OSM roads from: {urban_csv_path}")
    print(f"[Phase 5 - OSM Network] Loading Rural OSM roads from: {rural_csv_path}")

    if not urban_csv_path.exists() or not rural_csv_path.exists():
        raise FileNotFoundError(f"OSM road dataset files not found at {urban_csv_path} or {rural_csv_path}")

    # Load Urban & Rural CSVs
    df_urban = pd.read_csv(urban_csv_path)
    df_urban['Area'] = 'Urban'
    
    df_rural = pd.read_csv(rural_csv_path)
    df_rural['Area'] = 'Rural'

    print(f" Urban raw records: {len(df_urban)}")
    print(f" Rural raw records: {len(df_rural)}")

    # Combine datasets
    df_combined = pd.concat([df_urban, df_rural], ignore_index=True)
    print(f" Combined raw records: {len(df_combined)}")

    # Clean duplicates and null geometries
    df_combined = df_combined.dropna(subset=['geometry']).copy()
    
    # Parse WKT geometry into Shapely geometries
    print(" Parsing WKT geometries...")
    def safe_wkt_parse(val):
        try:
            return wkt.loads(str(val))
        except Exception:
            return None

    df_combined['geom_parsed'] = df_combined['geometry'].apply(safe_wkt_parse)
    df_combined = df_combined.dropna(subset=['geom_parsed']).copy()

    # Convert to GeoDataFrame (EPSG:4326)
    gdf = gpd.GeoDataFrame(df_combined, geometry='geom_parsed', crs="EPSG:4326")

    # Generate representative points for Road_Latitude and Road_Longitude
    print(" Extracting representative points (Road_Latitude, Road_Longitude)...")
    rep_points = gdf.geometry.representative_point()
    gdf['Road_Longitude'] = rep_points.x
    gdf['Road_Latitude'] = rep_points.y

    # Generate unique road_id
    gdf['road_id'] = [f"BLR_OSM_{i+1:07d}" for i in range(len(gdf))]

    # Drop intermediate geometry column for CSV export while preserving main attributes
    df_output = pd.DataFrame(gdf.drop(columns=['geom_parsed']))

    # Save output
    output_path = OSM_DATA_DIR / "bengaluru_osm_master_roads.csv"
    output_cleaned_path = ROAD_FEATURES_OUTPUT_DIR / "osm_master_roads.csv"

    df_output.to_csv(output_path, index=False)
    df_output.to_csv(output_cleaned_path, index=False)

    print("\n" + "=" * 60)
    print(" PHASE 5: OSM MASTER ROAD NETWORK PROCESSING COMPLETE")
    print("=" * 60)
    print(f" Total Master Road Segments: {len(df_output)}")
    print(f" Urban Segments: {(df_output['Area'] == 'Urban').sum()}")
    print(f" Rural Segments: {(df_output['Area'] == 'Rural').sum()}")
    print(f" Master File Saved to: {output_path}")
    print("\nSample Master Roads:")
    print(df_output[['road_id', 'Area', 'highway', 'name', 'lanes', 'Road_Latitude', 'Road_Longitude']].head())
    print("=" * 60 + "\n")

    return df_output

if __name__ == "__main__":
    process_osm_road_network()
