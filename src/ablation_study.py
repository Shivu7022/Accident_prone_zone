import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, OSM_DATA_DIR, EVALUATION_OUTPUT_DIR
from src.master_feature_table import generate_master_feature_table

def run_ablation_study(input_csv_path=None):
    """
    Phase 18 & 19: Mandatory 6-Experiment Ablation Study evaluating feature contributions.
    """
    ensure_directories()
    
    if input_csv_path is None:
        input_csv_path = OSM_DATA_DIR / "road_master_features.csv"
        if not Path(input_csv_path).exists():
            print("[AblationStudy] Master feature table not found. Running Phase 16...")
            df = generate_master_feature_table()
        else:
            df = pd.read_csv(input_csv_path, low_memory=False)
    else:
        df = pd.read_csv(input_csv_path, low_memory=False)

    print("\n" + "=" * 70)
    print(" PHASE 18 & 19: 6-EXPERIMENT MANDATORY ABLATION STUDY")
    print("=" * 70)
    print(f" Total Samples in Feature Matrix: {len(df)}")

    # Preprocess missing values in accident features for model input
    df['Historical_Area_Accident_Risk_Filled'] = df['Historical_Area_Accident_Risk'].fillna(-1.0)

    # Define Feature Sets for 6 Experiments
    experiments_def = {
        "Exp 1: Accident Only": [
            'Historical_Area_Accident_Risk_Filled', 'Accident_Data_Available'
        ],
        "Exp 2: Accident + OSM": [
            'Historical_Area_Accident_Risk_Filled', 'Accident_Data_Available',
            'road_complexity', 'lanes_num', 'length_m', 'width_m', 'maxspeed_kmh',
            'junction_flag', 'oneway_flag', 'bridge_flag', 'tunnel_flag'
        ],
        "Exp 3: Accident + OSM + Damage": [
            'Historical_Area_Accident_Risk_Filled', 'Accident_Data_Available',
            'road_complexity', 'lanes_num', 'length_m', 'width_m', 'maxspeed_kmh',
            'junction_flag', 'oneway_flag', 'bridge_flag', 'tunnel_flag',
            'road_damage_score'
        ],
        "Exp 4: Accident + OSM + Damage + Traffic": [
            'Historical_Area_Accident_Risk_Filled', 'Accident_Data_Available',
            'road_complexity', 'lanes_num', 'length_m', 'width_m', 'maxspeed_kmh',
            'junction_flag', 'oneway_flag', 'bridge_flag', 'tunnel_flag',
            'road_damage_score', 'traffic_speed', 'congestion_level'
        ],
        "Exp 5: Accident + OSM + Damage + Traffic + Weather": [
            'Historical_Area_Accident_Risk_Filled', 'Accident_Data_Available',
            'road_complexity', 'lanes_num', 'length_m', 'width_m', 'maxspeed_kmh',
            'junction_flag', 'oneway_flag', 'bridge_flag', 'tunnel_flag',
            'road_damage_score', 'traffic_speed', 'congestion_level',
            'temperature', 'precipitation', 'visibility'
        ],
        "Exp 6: All Features + Travel Speed": [
            'Historical_Area_Accident_Risk_Filled', 'Accident_Data_Available',
            'road_complexity', 'lanes_num', 'length_m', 'width_m', 'maxspeed_kmh',
            'junction_flag', 'oneway_flag', 'bridge_flag', 'tunnel_flag',
            'road_damage_score', 'traffic_speed', 'congestion_level',
            'temperature', 'precipitation', 'visibility',
            'travel_speed_kmh'
        ]
    }

    # Sample subset if dataset is very large for fast local execution verification
    df_sample = df.sample(n=min(25000, len(df)), random_state=42)
    y = df_sample['risk_class'].values

    ablation_results = []

    for exp_name, feature_list in experiments_def.items():
        print(f"\n[AblationStudy] Running {exp_name} (Num Features: {len(feature_list)})...")
        X = df_sample[feature_list].fillna(0).values

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)

        # Train Random Forest model
        model = RandomForestClassifier(n_estimators=50, max_depth=12, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, average='weighted', zero_division=0))
        rec = float(recall_score(y_test, y_pred, average='weighted', zero_division=0))
        f1 = float(f1_score(y_test, y_pred, average='weighted', zero_division=0))

        result_row = {
            "Experiment": exp_name,
            "Num_Features": len(feature_list),
            "Accuracy": round(acc, 4),
            "Precision": round(prec, 4),
            "Recall": round(rec, 4),
            "F1_Score": round(f1, 4)
        }
        ablation_results.append(result_row)
        print(f" -> Acc: {acc:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f} | F1: {f1:.4f}")

    # Convert results to DataFrame & JSON
    df_ablation = pd.DataFrame(ablation_results)
    output_json = EVALUATION_OUTPUT_DIR / "ablation_study_results.json"
    output_csv = EVALUATION_OUTPUT_DIR / "ablation_study_results.csv"

    df_ablation.to_json(output_json, orient="records", indent=2)
    df_ablation.to_csv(output_csv, index=False)

    print("\n" + "=" * 70)
    print(" ABLATION STUDY COMPARATIVE SUMMARY TABLE")
    print("=" * 70)
    print(df_ablation.to_string(index=False))
    print(f"\n Results saved to: {output_json}")
    print("=" * 70 + "\n")

    return df_ablation

if __name__ == "__main__":
    run_ablation_study()
