import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, ACCIDENT_DATA_DIR, CLEANED_DATA_OUTPUT_DIR

# Verified Bengaluru Traffic Police Station Coordinates (WGS84 Lat/Lon)
VERIFIED_STATION_COORDINATES = {
    'Yalahanka': (13.1007, 77.5963),
    'K R Puram': (13.0075, 77.6959),
    'Kamakshipalya': (12.9806, 77.5255),
    'Int. Aiport': (13.1986, 77.7066),
    'Peenya': (13.0329, 77.5273),
    'Hebbal': (13.0359, 77.5970),
    'Micolayout': (12.9121, 77.6094),
    'Malleshwaram': (13.0031, 77.5684),
    'Whitefield': (12.9698, 77.7499),
    'Halasooru': (12.9753, 77.6253),
    'Indiranagar': (12.9784, 77.6408),
    'Electronic City': (12.8452, 77.6602),
    'Banashankari': (12.9255, 77.5468),
    'Jayanagar': (12.9250, 77.5938),
    'Rajajinagar': (12.9882, 77.5549),
    'Basavanagudi': (12.9416, 77.5746),
    'Shivajinagar': (12.9863, 77.6047),
    'Chickpet': (12.9675, 77.5750),
    'Chamarajpet': (12.9567, 77.5639),
    'High Ground': (12.9885, 77.5877),
    'Cubbon Park': (12.9740, 77.5935),
    'Commercial Street': (12.9818, 77.6095),
    'Frazer Town': (12.9972, 77.6143),
    'Pulikeshinagar': (12.9965, 77.6139),
    'R T Nagar': (13.0247, 77.5948),
    'Jalahalli': (13.0538, 77.5385),
    'Yeshwanthpur': (13.0285, 77.5458),
    'Yashawanthapura': (13.0285, 77.5458),
    'Vijayanagar': (12.9719, 77.5308),
    'Byatarayanapura': (13.0645, 77.5946),
    'Magadi Road': (12.9760, 77.5450),
    'K S Layout': (12.9079, 77.5661),
    'Kumaraswamy Layout': (12.9079, 77.5661),
    'Hulimavu': (12.8804, 77.6074),
    'Madiwala': (12.9226, 77.6174),
    'Adugodi': (12.9442, 77.6083),
    'HSR Layout': (12.9121, 77.6446),
    'Bellandur': (12.9258, 77.6766),
    'Mahadevapura': (12.9902, 77.6888),
    'Chikkajala': (13.1706, 77.6358),
    'Sadashivanagar': (13.0068, 77.5813),
    'Upparpet': (12.9779, 77.5724),
    'V V Puram': (12.9515, 77.5752),
    'Wilson Garden': (12.9482, 77.5971),
    'Ashoknagar': (12.9705, 77.6076),
    'KG Halli': (13.0135, 77.6212),
    'Banaswadi': (13.0142, 77.6519),
    'Kothanur': (13.0574, 77.6558),
    'Sampigehalli': (13.0845, 77.6205),
    'Bagalur': (13.1345, 77.6625)
}

def process_station_coordinates(aggregated_csv_path=None):
    """
    Phase 3: Attach verified geographic coordinates (Lat, Lon) to police stations.
    """
    ensure_directories()
    
    if aggregated_csv_path is None:
        aggregated_csv_path = ACCIDENT_DATA_DIR / "bengaluru_accidents_aggregated.csv"
    else:
        aggregated_csv_path = Path(aggregated_csv_path)

    print(f"[Phase 3 - Coordinates] Processing station coordinates from: {aggregated_csv_path}")
    if not aggregated_csv_path.exists():
        raise FileNotFoundError(f"Aggregated station file not found at {aggregated_csv_path}")

    df = pd.read_csv(aggregated_csv_path)
    
    lats = []
    lons = []
    statuses = []

    for _, row in df.iterrows():
        station_name = str(row['Station']).strip()
        if station_name in VERIFIED_STATION_COORDINATES:
            lat, lon = VERIFIED_STATION_COORDINATES[station_name]
            lats.append(lat)
            lons.append(lon)
            statuses.append('VERIFIED')
        else:
            # Check fuzzy / partial matching
            matched = False
            for k, (v_lat, v_lon) in VERIFIED_STATION_COORDINATES.items():
                if k.lower() in station_name.lower() or station_name.lower() in k.lower():
                    lats.append(v_lat)
                    lons.append(v_lon)
                    statuses.append('GEOCODED')
                    matched = True
                    break
            if not matched:
                lats.append(np.nan)
                lons.append(np.nan)
                statuses.append('UNRESOLVED')

    df['Latitude'] = lats
    df['Longitude'] = lons
    df['Geocoding_Status'] = statuses

    # Filter out unresolved for spatial downstream tasks, while saving complete file
    resolved_df = df.dropna(subset=['Latitude', 'Longitude']).copy()

    output_path = ACCIDENT_DATA_DIR / "bengaluru_stations_with_coordinates.csv"
    output_cleaned = CLEANED_DATA_OUTPUT_DIR / "station_coordinates.csv"

    df.to_csv(output_path, index=False)
    df.to_csv(output_cleaned, index=False)

    print("\n" + "=" * 60)
    print(" PHASE 3: STATION COORDINATE PROCESSING COMPLETE")
    print("=" * 60)
    print(f" Total Stations: {len(df)}")
    print(f" Verified/Geocoded Stations: {len(resolved_df)}")
    print(f" Unresolved Stations: {len(df) - len(resolved_df)}")
    print(f" Output File Saved to: {output_path}")
    print("\nSample Geocoded Stations:")
    print(df[['Station', 'Zone', 'Latitude', 'Longitude', 'Geocoding_Status', 'Total_Accidents']].head())
    print("=" * 60 + "\n")

    return df

if __name__ == "__main__":
    process_station_coordinates()
