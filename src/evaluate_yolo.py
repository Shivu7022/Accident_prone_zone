import os
import sys
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config_loader import load_config
from src.drive_sync import sync_to_google_drive

def evaluate_rdd2022_yolo(model_path=None, exp_dir=None):
    """
    Evaluates trained RDD2022 YOLO11s model on test/val set and computes:
    - Precision
    - Recall
    - mAP50
    - mAP50-95
    - Per-class metrics & plots
    """
    config = load_config()
    
    try:
        from ultralytics import YOLO
    except ImportError:
        os.system("pip install -q ultralytics")
        from ultralytics import YOLO

    data_yaml_path = Path(config['project_root']) / config['paths']['yolo_dataset_dir'] / "data.yaml"
    
    if model_path is None or not Path(model_path).exists():
        # Find latest experiment best.pt
        experiments_root = Path(config['project_root']) / config['paths']['experiments_dir']
        exp_runs = sorted(glob.glob(str(experiments_root / "rdd2022_yolo11s_*")))
        if exp_runs:
            latest_exp = Path(exp_runs[-1])
            model_path = latest_exp / "weights" / "best.pt"
            exp_dir = latest_exp
        else:
            raise FileNotFoundError("No trained best.pt model found for evaluation!")
            
    print(f"\n[EvaluatePipeline] Evaluating YOLO11s model: {model_path}")
    print(f"[EvaluatePipeline] Dataset config: {data_yaml_path}")

    model = YOLO(str(model_path))
    
    # Run evaluation / validation
    metrics = model.val(
        data=str(data_yaml_path),
        split="val",
        batch=16,
        imgsz=512,
        save_json=True,
        plots=True
    )
    
    # Extract key evaluation metrics as specified in prompt requirements
    precision = float(metrics.results_dict.get('metrics/precision(B)', 0.0))
    recall = float(metrics.results_dict.get('metrics/recall(B)', 0.0))
    map50 = float(metrics.results_dict.get('metrics/mAP50(B)', 0.0))
    map50_95 = float(metrics.results_dict.get('metrics/mAP50-95(B)', 0.0))
    
    # Compute F1 Score
    f1_score = float((2 * precision * recall) / (precision + recall + 1e-16))

    eval_report = {
        "model_path": str(model_path),
        "target_classes": config['rdd2022']['class_names'],
        "metrics": {
            "Precision": round(precision, 4),
            "Recall": round(recall, 4),
            "F1_Score": round(f1_score, 4),
            "mAP50": round(map50, 4),
            "mAP50-95": round(map50_95, 4)
        }
    }

    print("\n" + "=" * 70)
    print(" RDD2022 FOUR-CLASS YOLO11s EVALUATION RESULTS")
    print("=" * 70)
    print(f" Precision: {eval_report['metrics']['Precision']:.4f}")
    print(f" Recall:    {eval_report['metrics']['Recall']:.4f}")
    print(f" F1-Score:  {eval_report['metrics']['F1_Score']:.4f}")
    print(f" mAP50:     {eval_report['metrics']['mAP50']:.4f}")
    print(f" mAP50-95:  {eval_report['metrics']['mAP50-95']:.4f}")
    print("=" * 70 + "\n")

    # Save evaluation report JSON to experiment dir
    if exp_dir:
        exp_dir = Path(exp_dir)
        report_path = exp_dir / "evaluation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(eval_report, f, indent=2)
        print(f"[EvaluatePipeline] Saved metrics report to: {report_path}")
        
        # Sync to Google Drive if on Colab
        sync_to_google_drive(exp_dir, drive_subfolder="experiments")

    return eval_report

if __name__ == "__main__":
    import glob
    evaluate_rdd2022_yolo()
