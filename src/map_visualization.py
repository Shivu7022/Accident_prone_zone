import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, OSM_DATA_DIR, ACCIDENT_DATA_DIR, PREDICTIONS_OUTPUT_DIR

def generate_bengaluru_risk_map(sample_size=1000):
    """
    Phase 22: Generate interactive Folium risk map for Bengaluru.
    """
    ensure_directories()
    
    try:
        import folium
    except ImportError:
        os.system("pip install -q folium")
        import folium

    roads_csv = OSM_DATA_DIR / "road_master_features.csv"
    hotspots_csv = ACCIDENT_DATA_DIR / "accident_hotspots.csv"

    print(f"[Phase 22 - Risk Map] Loading roads from: {roads_csv}")
    df_roads = pd.read_csv(roads_csv, low_memory=False)

    print(f"[Phase 22 - Risk Map] Creating Folium map centered on Bengaluru (12.9716, 77.5946)...")
    m = folium.Map(location=[12.9716, 77.5946], zoom_start=11, tiles="cartodbpositron")

    # 1. Add Accident Hotspots Markers if available
    if Path(hotspots_csv).exists():
        df_hotspots = pd.read_csv(hotspots_csv)
        print(f" Adding {len(df_hotspots)} accident hotspot markers...")
        for _, row in df_hotspots.iterrows():
            lat = row.get('Latitude')
            lon = row.get('Longitude')
            if pd.notna(lat) and pd.notna(lon):
                station = row.get('Station', 'Station')
                acc = int(row.get('Total_Accidents', 0))
                risk_lvl = row.get('Risk_Level', 'MEDIUM')
                
                color = 'darkred' if risk_lvl == 'VERY HIGH' else ('red' if risk_lvl == 'HIGH' else 'orange')
                popup_text = f"<b>Police Station:</b> {station}<br><b>Total Accidents:</b> {acc}<br><b>Area Risk Level:</b> {risk_lvl}"
                
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=8,
                    color=color,
                    fill=True,
                    fill_opacity=0.7,
                    popup=folium.Popup(popup_text, max_width=300)
                ).add_to(m)

    # 2. Sample Road Segments for Performance
    df_sample = df_roads.sample(n=min(sample_size, len(df_roads)), random_state=42)
    print(f" Adding {len(df_sample)} sampled road segment risk markers...")

    for _, row in df_sample.iterrows():
        lat = row.get('Road_Latitude')
        lon = row.get('Road_Longitude')
        if pd.notna(lat) and pd.notna(lon):
            road_id = row.get('road_id', 'N/A')
            name = str(row.get('name', 'Unnamed Road'))
            score = float(row.get('risk_score', 25.0))
            complexity = float(row.get('road_complexity', 15.0))
            damage = float(row.get('road_damage_score', 0.0))
            
            if score >= 81.0:
                color = 'darkred'
                level = 'VERY HIGH'
            elif score >= 61.0:
                color = 'red'
                level = 'HIGH'
            elif score >= 31.0:
                color = 'orange'
                level = 'MODERATE'
            else:
                color = 'green'
                level = 'LOW'

            popup_html = f"""
            <div style="font-family: Arial, sans-serif; width: 220px;">
                <h4 style="margin-bottom: 5px;">{name}</h4>
                <b>Road ID:</b> {road_id}<br>
                <b>Risk Score:</b> <span style="color: {color}; font-weight: bold;">{score:.1f} / 100</span> ({level})<br>
                <b>Complexity Score:</b> {complexity:.1f}<br>
                <b>Road Damage Score:</b> {damage:.1f}<br>
            </div>
            """
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=250)
            ).add_to(m)

    output_html = PREDICTIONS_OUTPUT_DIR / "bengaluru_risk_map.html"
    m.save(str(output_html))

    print("\n" + "=" * 60)
    print(" PHASE 22: BENGALURU INTERACTIVE RISK MAP GENERATION COMPLETE")
    print("=" * 60)
    print(f" Interactive Map HTML Saved to: {output_html}")
    print("=" * 60 + "\n")

    return str(output_html)

if __name__ == "__main__":
    generate_bengaluru_risk_map()
