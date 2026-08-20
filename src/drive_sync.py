import os
import sys
import shutil
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config_loader import load_config

def sync_to_google_drive(local_exp_dir, drive_subfolder="experiments"):
    """
    Sync an experiment directory or file to persistent Google Drive storage if running on Colab.
    """
    config = load_config()
    
    if not config['is_colab']:
        print("[DriveSync] Not running inside Google Colab environment. Drive sync skipped (Local Mode).")
        return False, str(local_exp_dir)

    drive_root = Path(config['paths']['colab_drive_root'])
    if not drive_root.exists():
        print(f"[DriveSync] Warning: Google Drive root path not found at {drive_root}.")
        print("[DriveSync] Please ensure Google Drive is mounted: `from google.colab import drive; drive.mount('/content/drive')`")
        return False, str(local_exp_dir)

    target_drive_dir = drive_root / drive_subfolder / Path(local_exp_dir).name
    target_drive_dir.mkdir(parents=True, exist_ok=True)

    print(f"[DriveSync] Syncing experiment artifacts to Google Drive...")
    print(f" Source: {local_exp_dir}")
    print(f" Destination: {target_drive_dir}")

    # Copy files and directories recursively
    local_path = Path(local_exp_dir)
    if local_path.is_dir():
        for item in local_path.rglob("*"):
            rel_path = item.relative_to(local_path)
            dest_path = target_drive_dir / rel_path
            if item.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                shutil.copy2(item, dest_path)
    else:
        shutil.copy2(local_path, target_drive_dir / local_path.name)

    print(f"[DriveSync] Google Drive Persistence Sync COMPLETED successfully!")
    return True, str(target_drive_dir)

if __name__ == "__main__":
    cfg = load_config()
    print(f"Drive Sync module initialized. Colab active: {cfg['is_colab']}")
