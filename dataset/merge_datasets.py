import pandas as pd
import numpy as np
import os

def merge_all_datasets():
    # Define file paths
    base_dir = r"c:\Users\HP\Documents\Major_dataset"
    
    path_ds1 = os.path.join(base_dir, "dataset1.csv")
    path_ds2 = os.path.join(base_dir, "dataset2.csv")
    path_ds3 = os.path.join(base_dir, "dataset3.csv")
    path_ds4 = os.path.join(base_dir, "dataset4.csv")
    path_ds5 = os.path.join(base_dir, "dataset5.csv")
    
    # Load datasets
    print("Loading datasets...")
    ds1 = pd.read_csv(path_ds1)
    ds2 = pd.read_csv(path_ds2)
    ds3 = pd.read_csv(path_ds3)
    ds4 = pd.read_csv(path_ds4)
    ds5 = pd.read_csv(path_ds5)
    
    # Standard mappings for station names
    station_mapping = {
        'B.Pura': 'Bytarayanapura',
        'Chamarajapet': 'Chamarajpet',
        'Chikjala': 'Chikkajala',
        'Devanahalli': 'Int. Aiport',
        'F.Town': 'Pulikeshinagar',
        'HuliMavu': 'Hulimavu',
        'K.R.Pura': 'K R Puram',
        'K.Swamy Lyt.': 'K S Layout',
        'Malleswaram': 'Malleshwaram',
        'Mico layout': 'Micolayout',
        'RT Nagar': 'R T Nagar',
        'Ulsoor': 'Halasooru',
        'White Field': 'Whitefield',
        'Y.Pura': 'Yashawanthapura',
        'Yelahanka': 'Yalahanka',
    }
    
    # 1. Process dataset2 (2024)
    print("Processing 2024 dataset (dataset2.csv)...")
    ds2_clean = ds2.copy()
    ds2_clean['Station'] = ds2_clean['Station'].astype(str).str.strip()
    # Remove total / grand rows
    ds2_clean = ds2_clean[~ds2_clean['Station'].str.contains('total|grand', case=False, na=False)]
    ds2_clean = ds2_clean.dropna(subset=['Station'])
    ds2_clean['Zone'] = ds2_clean['Zone'].astype(str).str.strip()
    ds2_clean['Sub-division'] = ds2_clean['Sub-division'].astype(str).str.strip()
    
    # Build standard Station-to-Info lookup
    station_info = {}
    for _, row in ds2_clean.iterrows():
        station_info[row['Station']] = {
            'Zone': row['Zone'],
            'Sub-division': row['Sub-division']
        }
        
    records_2024 = []
    for _, row in ds2_clean.iterrows():
        records_2024.append({
            'Zone': row['Zone'],
            'Sub-division': row['Sub-division'],
            'Station': row['Station'],
            'Year': 2024,
            'Fatal_Accidents': pd.to_numeric(row['2024-Fatal crashes']),
            'Killed': np.nan,  # dataset2 doesn't have Killed
            'Non_Fatal_Accidents': pd.to_numeric(row['2024-Non Fatal']),
            'Injured': np.nan,  # dataset2 doesn't have Injured
            'Total_Accidents': pd.to_numeric(row['2024-Total crashes'])
        })
    df_2024 = pd.DataFrame(records_2024)
    
    # 2. Process dataset4 (2023)
    print("Processing 2023 dataset (dataset4.csv)...")
    ds4_clean = ds4.copy()
    ds4_clean['Station'] = ds4_clean['Station'].astype(str).str.strip()
    ds4_clean = ds4_clean[~ds4_clean['Station'].str.contains('total|grand', case=False, na=False)]
    ds4_clean = ds4_clean.dropna(subset=['Station'])
    
    records_2023 = []
    for _, row in ds4_clean.iterrows():
        station = row['Station']
        station = station_mapping.get(station, station)
        info = station_info.get(station, {'Zone': row['Zone'].strip() if pd.notna(row['Zone']) else 'Unknown', 
                                          'Sub-division': row['Sub-division'].strip() if pd.notna(row['Sub-division']) else 'Unknown'})
        records_2023.append({
            'Zone': info['Zone'],
            'Sub-division': info['Sub-division'],
            'Station': station,
            'Year': 2023,
            'Fatal_Accidents': pd.to_numeric(row['2023 - Fatal Cases']),
            'Killed': pd.to_numeric(row['2023 - Killed People']),
            'Non_Fatal_Accidents': pd.to_numeric(row['2023 - Non-Fatal']),
            'Injured': pd.to_numeric(row['2023 - Injured People']),
            'Total_Accidents': pd.to_numeric(row['2023 - Total Cases'])
        })
    df_2023 = pd.DataFrame(records_2023)
    
    # 3. Process dataset3 (2021 & 2022)
    print("Processing 2021-2022 dataset (dataset3.csv)...")
    ds3_clean = ds3.copy()
    ds3_clean['Station'] = ds3_clean['Station'].astype(str).str.strip()
    ds3_clean = ds3_clean[~ds3_clean['Station'].str.contains('total|grand', case=False, na=False)]
    ds3_clean = ds3_clean.dropna(subset=['Station'])
    
    records_2021_2022 = []
    for _, row in ds3_clean.iterrows():
        station = row['Station']
        station = station_mapping.get(station, station)
        info = station_info.get(station)
        if not info:
            raise ValueError(f"Station '{station}' from dataset3 not found in 2024 info lookup.")
        
        # 2021
        records_2021_2022.append({
            'Zone': info['Zone'],
            'Sub-division': info['Sub-division'],
            'Station': station,
            'Year': 2021,
            'Fatal_Accidents': pd.to_numeric(row['2021 - Fatal']),
            'Killed': pd.to_numeric(row['2021 - Killed']),
            'Non_Fatal_Accidents': pd.to_numeric(row['2021 - Non-Fatal']),
            'Injured': pd.to_numeric(row['2021 - Injured']),
            'Total_Accidents': pd.to_numeric(row['2021 - Total Cases'])
        })
        # 2022
        records_2021_2022.append({
            'Zone': info['Zone'],
            'Sub-division': info['Sub-division'],
            'Station': station,
            'Year': 2022,
            'Fatal_Accidents': pd.to_numeric(row['2022 - Fatal']),
            'Killed': pd.to_numeric(row['2022 - Killed']),
            'Non_Fatal_Accidents': pd.to_numeric(row['2022 - Non-Fatal']),
            'Injured': pd.to_numeric(row['2022 - Injured']),
            'Total_Accidents': pd.to_numeric(row['2022 - Total Cases'])
        })
    df_2021_2022 = pd.DataFrame(records_2021_2022)
    
    # 4. Process dataset5 (2018, 2019, 2020)
    print("Processing 2018-2020 dataset (dataset5.csv)...")
    ds5_clean = ds5.copy()
    ds5_clean['Station'] = ds5_clean['Station'].astype(str).str.strip()
    ds5_clean = ds5_clean[~ds5_clean['Station'].str.contains('total|grand', case=False, na=False)]
    ds5_clean = ds5_clean.dropna(subset=['Station'])
    
    records_2018_2020 = []
    for _, row in ds5_clean.iterrows():
        station = row['Station']
        station = station_mapping.get(station, station)
        info = station_info.get(station)
        if not info:
            raise ValueError(f"Station '{station}' from dataset5 not found in 2024 info lookup.")
        
        # 2018
        records_2018_2020.append({
            'Zone': info['Zone'],
            'Sub-division': info['Sub-division'],
            'Station': station,
            'Year': 2018,
            'Fatal_Accidents': pd.to_numeric(row['2018 - Fatal']),
            'Killed': pd.to_numeric(row['2018 - Killed']),
            'Non_Fatal_Accidents': pd.to_numeric(row['2018 - Non-Fatal']),
            'Injured': pd.to_numeric(row['2018 - Injured']),
            'Total_Accidents': pd.to_numeric(row['2018 - Total Cases'])
        })
        # 2019
        records_2018_2020.append({
            'Zone': info['Zone'],
            'Sub-division': info['Sub-division'],
            'Station': station,
            'Year': 2019,
            'Fatal_Accidents': pd.to_numeric(row['2019 - Fatal']),
            'Killed': pd.to_numeric(row['2019 - Killed']),
            'Non_Fatal_Accidents': pd.to_numeric(row['2019 - Non-Fatal']),
            'Injured': pd.to_numeric(row['2019 - Injured']),
            'Total_Accidents': pd.to_numeric(row['2019 - Total Cases'])
        })
        # 2020 (note the trailing spaces in column headers '2020 - Fatal ' and '2020 - Total Cases ')
        records_2018_2020.append({
            'Zone': info['Zone'],
            'Sub-division': info['Sub-division'],
            'Station': station,
            'Year': 2020,
            'Fatal_Accidents': pd.to_numeric(row['2020 - Fatal ']),
            'Killed': pd.to_numeric(row['2020 - Killed']),
            'Non_Fatal_Accidents': pd.to_numeric(row['2020 - Non-Fatal']),
            'Injured': pd.to_numeric(row['2020 - Injured']),
            'Total_Accidents': pd.to_numeric(row['2020 - Total Cases '])
        })
    df_2018_2020 = pd.DataFrame(records_2018_2020)
    
    # 5. Process dataset1 (2007-2015)
    print("Processing city-wide 2007-2015 dataset (dataset1.csv)...")
    ds1_clean = ds1.copy()
    ds1_clean['Year'] = pd.to_numeric(ds1_clean['Year'])
    ds1_clean['Fatal Road Accidents'] = ds1_clean['Fatal Road Accidents'].astype(str).str.replace(',', '').astype(int)
    ds1_clean['Killed'] = ds1_clean['Killed'].astype(str).str.replace(',', '').astype(int)
    ds1_clean['Non-Fatal Road Accidents'] = ds1_clean['Non-Fatal Road Accidents'].astype(str).str.replace(',', '').astype(int)
    ds1_clean['Total'] = ds1_clean['Total'].astype(str).str.replace(',', '').astype(int)
    
    records_2007_2015 = []
    for _, row in ds1_clean.iterrows():
        records_2007_2015.append({
            'Zone': 'Overall',
            'Sub-division': 'Overall',
            'Station': 'Overall',
            'Year': int(row['Year']),
            'Fatal_Accidents': int(row['Fatal Road Accidents']),
            'Killed': int(row['Killed']),
            'Non_Fatal_Accidents': int(row['Non-Fatal Road Accidents']),
            'Injured': np.nan,
            'Total_Accidents': int(row['Total'])
        })
    df_2007_2015 = pd.DataFrame(records_2007_2015)
    
    # Combine all
    print("Merging all processed dataframes...")
    merged_df = pd.concat([
        df_2007_2015,
        df_2018_2020,
        df_2021_2022,
        df_2023,
        df_2024
    ], ignore_index=True)
    
    # Sort logically
    # Setup sort order: Overall rows first, then sort by Zone, Sub-division, Station, Year
    merged_df['sort_zone'] = np.where(merged_df['Zone'] == 'Overall', '0_Overall', merged_df['Zone'])
    merged_df = merged_df.sort_values(by=['Year', 'sort_zone', 'Sub-division', 'Station']).drop(columns=['sort_zone'])
    merged_df = merged_df.reset_index(drop=True)
    
    # Save output
    output_path = os.path.join(base_dir, "merged_dataset.csv")
    merged_df.to_csv(output_path, index=False)
    print(f"Merging complete! Output saved to: {output_path}")
    print("Merged dataset shape:", merged_df.shape)
    print("Columns:", merged_df.columns.tolist())

if __name__ == "__main__":
    merge_all_datasets()
