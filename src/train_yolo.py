import os
import sys
import shutil
import yaml
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.remote_gpu_guard import verify_gpu_availability
from src.config_loader import load_config
from src.rdd2022_prep import prepare_rdd2022_dataset
from src.experiment_tracker import ExperimentTracker
from src.drive_sync import sync_to_google_drive

def train_rdd2022_yolo11s():
    """
    Main Training Pipeline for RDD2022 4-Class YOLO11s Model on Remote Colab GPU.
    """
    print("\n" + "=" * 70)
    print(" BENGALURU ROAD SAFETY ML PROJECT - REMOTE GPU YOLO11s TRAINING")
    print("=" * 70)

    # Step 1: Verify Hardware Guard (CUDA GPU Assertion)
    gpu_ok, gpu_name = verify_gpu_availability(force_halt=True)

    # Step 2: Load Configuration
    config = load_config()
    train_cfg = config['training']

    # Step 3: Initialize Experiment Tracker (Versioned output directory)
    tracker = ExperimentTracker(experiment_name="rdd2022_yolo11s")
    exp_dir = Path(tracker.exp_dir)

    # Step 4: Ensure RDD2022 Dataset is Prepared
    data_yaml_path = Path(config['project_root']) / config['paths']['yolo_dataset_dir'] / "data.yaml"
    if not data_yaml_path.exists():
        print("[TrainPipeline] RDD2022 data.yaml not found. Running dataset preparation...")
        data_yaml_path = prepare_rdd2022_dataset()
    else:
        print(f"[TrainPipeline] Using existing dataset config: {data_yaml_path}")

    # Step 5: Load Ultralytics YOLO & Start Training
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[TrainPipeline] Error: ultralytics is not installed. Installing required dependencies...")
        os.system("pip install -q ultralytics")
        from ultralytics import YOLO

    model_name = train_cfg['model_name']
    print(f"\n[TrainPipeline] Initializing pretrained model: {model_name}")
    model = YOLO(model_name)

    print(f"[TrainPipeline] Starting YOLO11s Training for {train_cfg['epochs']} epochs on GPU ({gpu_name})...")

    # Run YOLO training
    results = model.train(
        data=str(data_yaml_path),
        epochs=train_cfg['epochs'],
        batch=train_cfg['batch_size'],
        imgsz=train_cfg['imgsz'],
        workers=train_cfg['workers'],
        device=0,  # GPU device 0
        optimizer=train_cfg['optimizer'],
        lr0=train_cfg['lr0'],
        lrf=train_cfg['lrf'],
        patience=train_cfg['patience'],
        save=True,
        save_period=train_cfg['save_period'],
        project=str(exp_dir.parent),
        name=exp_dir.name,
        exist_ok=True,
        seed=train_cfg['seed']
    )

    # Step 6: Verify and Save Weights (best.pt and last.pt)
    yolo_weights_dir = exp_dir / "weights"
    best_pt = yolo_weights_dir / "best.pt"
    last_pt = yolo_weights_dir / "last.pt"

    print("\n" + "=" * 70)
    print(" TRAINING COMPLETE - MODEL ARTIFACT CHECK")
    print("=" * 70)
    print(f" Best Model Checkpoint: {best_pt} (Exists: {best_pt.exists()})")
    print(f" Last Model Checkpoint: {last_pt} (Exists: {last_pt.exists()})")

    # Step 7: Sync Artifacts to Google Drive (if on Colab)
    sync_to_google_drive(exp_dir, drive_subfolder="experiments")

    print("\n" + "=" * 70)
    print(" REMOTE GPU TRAINING & GOOGLE DRIVE PERSISTENCE SUCCESSFUL!")
    print("=" * 70 + "\n")

    return str(best_pt), str(exp_dir)

if __name__ == "__main__":
    train_rdd2022_yolo11s()
