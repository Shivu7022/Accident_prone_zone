import os
import sys
import zipfile
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.remote_gpu_guard import verify_gpu_availability
from src.config_loader import load_config

def package_project_for_colab(output_zip="bengaluru_road_safety_project.zip"):
    """
    Bundle local project files into a zip archive to upload directly to Google Colab or Google Drive.
    """
    config = load_config()
    root_dir = Path(config['project_root'])
    zip_path = root_dir / output_zip
    
    print(f"[ColabCLI] Packaging project workspace into {zip_path}...")
    
    exclude_dirs = {".git", ".venv", "__pycache__", "experiments", "runs", ".idea", ".vscode"}
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in root_dir.rglob("*"):
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            if file_path.name == output_zip:
                continue
            if file_path.is_file():
                arcname = file_path.relative_to(root_dir)
                zipf.write(file_path, arcname)
                
    print(f"[ColabCLI] Workspace successfully packaged! Size: {zip_path.stat().st_size / (1024*1024):.2f} MB")
    print(f" Upload '{zip_path.name}' to Google Drive or Colab to run GPU training.")
    return str(zip_path)

def main():
    print("=" * 70)
    print(" BENGALURU ROAD SAFETY - COLAB CLI REMOTE PREPARATION UTILITY")
    print("=" * 70)
    
    # Run hardware check
    cuda_ok, gpu_name = verify_gpu_availability(force_halt=False)
    
    if not cuda_ok:
        print("[ColabCLI] Local machine has NO CUDA GPU.")
        print("[ColabCLI] Creating zip bundle for remote Google Colab GPU training...")
        package_project_for_colab()
    else:
        print(f"[ColabCLI] GPU detected ({gpu_name}). Local execution permitted.")

if __name__ == "__main__":
    main()
