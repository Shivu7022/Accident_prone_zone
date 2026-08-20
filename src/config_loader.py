import os
import sys
import yaml
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def is_colab():
    """Detect if code is currently running inside Google Colab environment."""
    try:
        import google.colab
        return True
    except ImportError:
        return False

def load_config(config_path="config.yaml"):
    """
    Load configuration from YAML file and adjust paths based on environment (Colab vs Local).
    """
    full_config_path = project_root / config_path
    
    if not full_config_path.exists():
        full_config_path = Path(config_path)

    with open(full_config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    config['is_colab'] = is_colab()
    config['project_root'] = str(project_root)
    
    if config['is_colab']:
        drive_root = Path(config['paths']['colab_drive_root'])
        config['resolved_drive_root'] = str(drive_root)
    else:
        config['resolved_drive_root'] = str(project_root)
        
    return config

if __name__ == "__main__":
    cfg = load_config()
    print("Configuration loaded successfully!")
    print(f"Environment: {'Google Colab (Remote GPU)' if cfg['is_colab'] else 'Local Machine'}")
    print(f"Project Root: {cfg['project_root']}")
    print(f"Target Classes: {cfg['rdd2022']['class_names']}")
