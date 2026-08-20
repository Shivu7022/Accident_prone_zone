import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config_loader import load_config

class ExperimentTracker:
    """
    Manages experiment directory creation, versioning, metadata logging,
    and prevents overwriting previous experiment runs.
    """
    def __init__(self, experiment_name="rdd2022_yolo11s", base_dir=None):
        self.config = load_config()
        
        if base_dir is None:
            self.base_dir = Path(self.config['project_root']) / self.config['paths']['experiments_dir']
        else:
            self.base_dir = Path(base_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.exp_id = f"{experiment_name}_{timestamp}"
        self.exp_dir = self.base_dir / self.exp_id
        
        # Subdirectories
        self.weights_dir = self.exp_dir / "weights"
        self.plots_dir = self.exp_dir / "plots"
        self.logs_dir = self.exp_dir / "logs"
        
        self._setup_directories()

    def _setup_directories(self):
        """Create versioned experiment directory structure."""
        self.weights_dir.mkdir(parents=True, exist_ok=True)
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Write initial metadata
        meta = {
            "experiment_id": self.exp_id,
            "created_at": datetime.now().isoformat(),
            "config": self.config
        }
        with open(self.exp_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
            
        print(f"[ExperimentTracker] Created new experiment directory: {self.exp_dir}")

    def save_metrics(self, metrics_dict, filename="metrics.json"):
        """Save metrics report to experiment directory."""
        metrics_path = self.exp_dir / filename
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics_dict, f, indent=2)
        print(f"[ExperimentTracker] Saved metrics to: {metrics_path}")
        return str(metrics_path)

    def get_weights_path(self, weight_name="best.pt"):
        """Get target path for model weights."""
        return str(self.weights_dir / weight_name)

if __name__ == "__main__":
    tracker = ExperimentTracker("test_experiment")
    tracker.save_metrics({"status": "initialized", "test_metric": 0.95})
