import os
import sys
import yaml
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def is_colab():
    """Detect if code is executing inside Google Colab environment."""
    try:
        import google.colab
        return True
    except ImportError:
        return False

# Base Directory Paths
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"

# Subdirectory Paths
ACCIDENT_DATA_DIR = DATA_DIR / "accident"
OSM_DATA_DIR = DATA_DIR / "osm"
RDD2022_DATA_DIR = DATA_DIR / "rdd2022"
POLIDRIVING_DATA_DIR = DATA_DIR / "polidriving"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

CLEANED_DATA_OUTPUT_DIR = OUTPUTS_DIR / "cleaned_data"
HOTSPOTS_OUTPUT_DIR = OUTPUTS_DIR / "hotspots"
ROAD_FEATURES_OUTPUT_DIR = OUTPUTS_DIR / "road_features"
PREDICTIONS_OUTPUT_DIR = OUTPUTS_DIR / "predictions"
EVALUATION_OUTPUT_DIR = OUTPUTS_DIR / "evaluation"

COLAB_DRIVE_ROOT = Path("/content/drive/MyDrive/Major_project") if is_colab() else PROJECT_ROOT

def ensure_directories():
    """Create all required project directories if they do not exist."""
    dirs = [
        DATA_DIR, MODELS_DIR, OUTPUTS_DIR, EXPERIMENTS_DIR,
        ACCIDENT_DATA_DIR, OSM_DATA_DIR, RDD2022_DATA_DIR, POLIDRIVING_DATA_DIR, EXTERNAL_DATA_DIR,
        MODELS_DIR / "road_damage", MODELS_DIR / "accident_risk", MODELS_DIR / "traffic", MODELS_DIR / "final_risk",
        CLEANED_DATA_OUTPUT_DIR, HOTSPOTS_OUTPUT_DIR, ROAD_FEATURES_OUTPUT_DIR,
        PREDICTIONS_OUTPUT_DIR, EVALUATION_OUTPUT_DIR
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return True

if __name__ == "__main__":
    ensure_directories()
    print("Project Directory Structure Initialized!")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Environment:  {'Google Colab (Remote GPU)' if is_colab() else 'Local Machine'}")
