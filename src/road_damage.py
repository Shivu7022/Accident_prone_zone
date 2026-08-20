import os
import sys
import json
import numpy as np
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, MODELS_DIR, EVALUATION_OUTPUT_DIR, RDD2022_DATA_DIR, COLAB_DRIVE_ROOT

CLASS_WEIGHTS = {
    0: 20.0,  # D00 Longitudinal Crack
    1: 25.0,  # D10 Transverse Crack
    2: 30.0,  # D20 Alligator Crack
    3: 40.0   # D40 Pothole / Separation
}

CLASS_NAMES = {
    0: "D00_Longitudinal_Crack",
    1: "D10_Transverse_Crack",
    2: "D20_Alligator_Crack",
    3: "D40_Pothole_Rutting_Separation"
}

def train_road_damage_yolo11s(epochs=80, imgsz=800, batch=8, patience=15):
    """
    Phase 11: Remote GPU Training of YOLO11s 4-Class Road Damage Model.
    """
    from src.remote_gpu_guard import verify_gpu_availability
    from src.rdd2022_prep import prepare_rdd2022_4class

    print("\n" + "=" * 70)
    print(" PHASE 11: ROAD DAMAGE MODEL TRAINING (YOLO11s)")
    print("=" * 70)

    gpu_ok, gpu_name = verify_gpu_availability(force_halt=True)

    data_yaml_path = RDD2022_DATA_DIR / "RDD2022_4CLASS" / "data.yaml"
    if not data_yaml_path.exists():
        print("[RoadDamage] RDD2022 data.yaml not found. Running Phase 10 preparation...")
        data_yaml_path = prepare_rdd2022_4class()

    try:
        from ultralytics import YOLO
    except ImportError:
        os.system("pip install -q ultralytics")
        from ultralytics import YOLO

    target_models_dir = MODELS_DIR / "road_damage"
    target_models_dir.mkdir(parents=True, exist_ok=True)

    print(f"[RoadDamage] Loading pretrained yolo11s.pt on GPU ({gpu_name})...")
    model = YOLO("yolo11s.pt")

    results = model.train(
        data=str(data_yaml_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        patience=patience,
        device=0,
        save=True,
        project=str(target_models_dir),
        name="yolo11s_rdd2022_4class",
        exist_ok=True
    )

    best_pt = target_models_dir / "yolo11s_rdd2022_4class" / "weights" / "best.pt"
    last_pt = target_models_dir / "yolo11s_rdd2022_4class" / "weights" / "last.pt"

    print("\n" + "=" * 70)
    print(" PHASE 11 TRAINING COMPLETE")
    print("=" * 70)
    print(f" Best Model: {best_pt}")
    print(f" Last Model: {last_pt}")

    drive_backup_dir = COLAB_DRIVE_ROOT / "Road_Damage_Model"
    drive_backup_dir.mkdir(parents=True, exist_ok=True)
    if best_pt.exists():
        import shutil
        shutil.copy2(best_pt, drive_backup_dir / "best_road_damage_4class.pt")
        print(f" Drive Backup: {drive_backup_dir / 'best_road_damage_4class.pt'}")

    return str(best_pt)

def evaluate_road_damage_model(model_path=None):
    """
    Phase 12: Evaluate Precision, Recall, mAP50, mAP50-95, and F1 score for Road Damage Model.
    """
    print("\n" + "=" * 70)
    print(" PHASE 12: ROAD DAMAGE MODEL EVALUATION")
    print("=" * 70)

    try:
        from ultralytics import YOLO
    except ImportError:
        os.system("pip install -q ultralytics")
        from ultralytics import YOLO

    data_yaml_path = RDD2022_DATA_DIR / "RDD2022_4CLASS" / "data.yaml"
    
    if model_path is None or not Path(model_path).exists():
        model_path = MODELS_DIR / "road_damage" / "yolo11s_rdd2022_4class" / "weights" / "best.pt"

    if not Path(model_path).exists():
        raise FileNotFoundError(f"Trained YOLO11s model weights not found at {model_path}")

    model = YOLO(str(model_path))
    metrics = model.val(data=str(data_yaml_path), split="val", imgsz=800, batch=8)

    precision = float(metrics.results_dict.get('metrics/precision(B)', 0.0))
    recall = float(metrics.results_dict.get('metrics/recall(B)', 0.0))
    map50 = float(metrics.results_dict.get('metrics/mAP50(B)', 0.0))
    map50_95 = float(metrics.results_dict.get('metrics/mAP50-95(B)', 0.0))
    f1_score = float((2 * precision * recall) / (precision + recall + 1e-16))

    eval_results = {
        "model": "YOLO11s_RDD2022_4Class",
        "model_path": str(model_path),
        "metrics": {
            "Precision": round(precision, 4),
            "Recall": round(recall, 4),
            "F1_Score": round(f1_score, 4),
            "mAP50": round(map50, 4),
            "mAP50-95": round(map50_95, 4)
        }
    }

    report_path = EVALUATION_OUTPUT_DIR / "road_damage_evaluation.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    print("\n" + "=" * 70)
    print(" ROAD DAMAGE EVALUATION RESULTS")
    print("=" * 70)
    print(f" Precision: {precision:.4f}")
    print(f" Recall:    {recall:.4f}")
    print(f" F1-Score:  {f1_score:.4f}")
    print(f" mAP50:     {map50:.4f}")
    print(f" mAP50-95:  {map50_95:.4f}")
    print(f" Saved Evaluation JSON to: {report_path}")
    print("=" * 70 + "\n")

    return eval_results

def calculate_road_damage_score(detections):
    """
    Phase 13: Compute Prototype Road Damage Score (0-100) and Severity Level.
    """
    if not detections:
        return {
            "Road_Damage_Score": 0.0,
            "Damage_Severity": "LOW",
            "Detections_Count": 0,
            "Details": []
        }

    total_score = 0.0
    details = []

    for det in detections:
        class_id = int(det.get('class_id', 0))
        confidence = float(det.get('confidence', 0.5))
        weight = CLASS_WEIGHTS.get(class_id, 20.0)
        
        contrib = weight * confidence
        total_score += contrib
        
        details.append({
            "class_id": class_id,
            "class_name": CLASS_NAMES.get(class_id, "Unknown"),
            "confidence": round(confidence, 4),
            "weight": weight,
            "contribution": round(contrib, 2)
        })

    final_score = min(100.0, round(total_score, 2))

    if final_score >= 75.0:
        severity = "VERY HIGH"
    elif final_score >= 50.0:
        severity = "HIGH"
    elif final_score >= 20.0:
        severity = "MODERATE"
    else:
        severity = "LOW"

    return {
        "Road_Damage_Score": final_score,
        "Damage_Severity": severity,
        "Detections_Count": len(detections),
        "Details": details
    }

if __name__ == "__main__":
    sample_dets = [
        {"class_id": 3, "confidence": 0.85},
        {"class_id": 2, "confidence": 0.70}
    ]
    res = calculate_road_damage_score(sample_dets)
    print("Sample Road Damage Score Computation:")
    print(json.dumps(res, indent=2))
