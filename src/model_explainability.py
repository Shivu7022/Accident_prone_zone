import os
import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def explain_road_risk(road_data):
    """
    Phase 20: Generate model interpretability and natural language contributing factors
    explaining a predicted Road Risk Score.
    """
    factors = []
    
    # 1. Historical Accident Risk Factor
    acc_avail = road_data.get('Accident_Data_Available', 0)
    hist_acc = road_data.get('Historical_Area_Accident_Risk', 0.0)
    if acc_avail == 1 and hist_acc > 500.0:
        factors.append(f"High Historical Area Accident Risk (Area Total Accidents: {int(hist_acc)})")
    elif acc_avail == 0:
        factors.append("No Historical Area Accident Data Available (Neutral Impact)")

    # 2. Road Complexity Factor
    complexity = road_data.get('road_complexity', 0.0)
    if complexity > 25.0:
        factors.append(f"High Road Network Complexity (Score: {complexity:.1f})")
    elif complexity > 10.0:
        factors.append(f"Moderate Road Network Complexity (Score: {complexity:.1f})")

    # 3. Road Damage Factor
    damage = road_data.get('road_damage_score', 0.0)
    if damage >= 50.0:
        factors.append(f"Severe Surface Road Damage Detected (Damage Score: {damage:.1f}/100)")
    elif damage >= 20.0:
        factors.append(f"Moderate Surface Cracks / Road Defects (Damage Score: {damage:.1f}/100)")

    # 4. Traffic & Congestion Factor
    congestion = road_data.get('congestion_level', 0.0)
    if congestion >= 0.6:
        factors.append(f"Heavy Traffic Congestion ({congestion*100:.0f}% Delay Ratio)")

    # 5. Travel Speed Factor
    speed = road_data.get('travel_speed_kmh', 50.0)
    maxspeed = road_data.get('maxspeed_kmh', 40.0)
    if speed > maxspeed + 15.0:
        factors.append(f"Excessive Travel Speed ({speed:.0f} km/h vs. Road Design Limit {maxspeed:.0f} km/h)")

    if not factors:
        factors.append("Standard road conditions with normal baseline risk factors.")

    return {
        "disclaimer": "Model-based contributing factors (not causal relationships).",
        "contributing_factors": factors
    }

if __name__ == "__main__":
    sample_road = {
        'Accident_Data_Available': 1,
        'Historical_Area_Accident_Risk': 1228.0,
        'road_complexity': 25.0,
        'road_damage_score': 55.0,
        'congestion_level': 0.70,
        'travel_speed_kmh': 75.0,
        'maxspeed_kmh': 50.0
    }
    exp = explain_road_risk(sample_road)
    print("SHAP / Natural Language Model Explanation Output:")
    print(json.dumps(exp, indent=2))
