import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, CLEANED_DATA_OUTPUT_DIR, ACCIDENT_DATA_DIR

def process_bengaluru_accidents(input_csv_path=None):
    """
    Phase 2: Load, clean, aggregate station/year-level accident data,
    and compute historical area-level risk indicators.
    """
    ensure_directories()
    
    if input_csv_path is None:
        # Fallback to existing merged dataset in dataset/
        input_csv_path = PROJECT_ROOT / "dataset" / "merged_dataset.csv"
    else:
        input_csv_path = Path(input_csv_path)

    print(f"[Phase 2 - Accident Prep] Loading accident data from: {input_csv_path}")
    if not input_csv_path.exists():
        raise FileNotFoundError(f"Accident dataset file not found at {input_csv_path}")

    df = pd.read_csv(input_csv_path)
    print(f"[Phase 2 - Accident Prep] Raw dataset shape: {df.shape}")

    # Standardize column names
    col_mapping = {
        'Zone': 'Zone',
        'Sub-division': 'Sub_Division',
        'Station': 'Station',
        'Year': 'Year',
        'Fatal_Accidents': 'Fatal_Accidents',
        'Killed': 'Killed',
        'Non_Fatal_Accidents': 'Non_Fatal_Accidents',
        'Injured': 'Injured',
        'Total_Accidents': 'Total_Accidents'
    }
    df = df.rename(columns=col_mapping)

    # Filter out aggregate / city-wide rows (e.g. 'Overall', 'Total', 'Karnataka')
    aggregate_mask = df['Station'].astype(str).str.contains('Overall|Total|Karnataka|Grand', case=False, na=False)
    df_clean = df[~aggregate_mask].copy()

    # Clean text columns
    df_clean['Station'] = df_clean['Station'].astype(str).str.strip()
    df_clean['Zone'] = df_clean['Zone'].astype(str).str.strip()
    df_clean['Sub_Division'] = df_clean['Sub_Division'].astype(str).str.strip()

    # Convert numeric fields
    numeric_cols = ['Fatal_Accidents', 'Killed', 'Non_Fatal_Accidents', 'Injured', 'Total_Accidents']
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)

    print(f"[Phase 2 - Accident Prep] Cleaned record count: {len(df_clean)} rows.")

    # Aggregate by Police Station
    station_grouped = df_clean.groupby('Station').agg(
        Zone=('Zone', 'first'),
        Sub_Division=('Sub_Division', 'first'),
        Years_Recorded=('Year', 'nunique'),
        Min_Year=('Year', 'min'),
        Max_Year=('Year', 'max'),
        Total_Accidents=('Total_Accidents', 'sum'),
        Fatal_Accidents=('Fatal_Accidents', 'sum'),
        Non_Fatal_Accidents=('Non_Fatal_Accidents', 'sum'),
        Total_Killed=('Killed', 'sum'),
        Total_Injured=('Injured', 'sum')
    ).reset_index()

    # Compute Historical Area-Level Accident Risk Indicators
    # Avoid division by zero with np.where
    total_acc = station_grouped['Total_Accidents']
    
    station_grouped['Fatality_Rate'] = np.where(total_acc > 0, station_grouped['Total_Killed'] / total_acc, 0.0)
    station_grouped['Injury_Rate'] = np.where(total_acc > 0, station_grouped['Total_Injured'] / total_acc, 0.0)
    station_grouped['Fatal_Accident_Ratio'] = np.where(total_acc > 0, station_grouped['Fatal_Accidents'] / total_acc, 0.0)
    
    # Calculate Average Annual Accidents
    station_grouped['Avg_Annual_Accidents'] = np.where(
        station_grouped['Years_Recorded'] > 0,
        station_grouped['Total_Accidents'] / station_grouped['Years_Recorded'],
        0.0
    )

    # Sort by total accidents descending
    station_grouped = station_grouped.sort_values(by='Total_Accidents', ascending=False).reset_index(drop=True)

    # Save outputs
    output_cleaned_path = CLEANED_DATA_OUTPUT_DIR / "cleaned_accidents_by_year.csv"
    output_agg_path = ACCIDENT_DATA_DIR / "bengaluru_accidents_aggregated.csv"
    output_agg_cleaned_path = CLEANED_DATA_OUTPUT_DIR / "bengaluru_accidents_aggregated.csv"

    df_clean.to_csv(output_cleaned_path, index=False)
    station_grouped.to_csv(output_agg_path, index=False)
    station_grouped.to_csv(output_agg_cleaned_path, index=False)

    print("\n" + "=" * 60)
    print(" PHASE 2: ACCIDENT DATA PROCESSING COMPLETE")
    print("=" * 60)
    print(f" Total Police Stations Processed: {len(station_grouped)}")
    print(f" Yearly Cleaned Data Saved to: {output_cleaned_path}")
    print(f" Aggregated Station Data Saved to: {output_agg_path}")
    print("\nTop 5 Stations by Total Accidents:")
    print(station_grouped[['Station', 'Zone', 'Total_Accidents', 'Fatal_Accidents', 'Avg_Annual_Accidents']].head())
    print("=" * 60 + "\n")

    return station_grouped

if __name__ == "__main__":
    process_bengaluru_accidents()
