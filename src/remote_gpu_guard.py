import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from src.config_loader import load_config

def verify_gpu_availability(force_halt=True):
    """
    Hardware Guard function to verify CUDA/NVIDIA GPU availability.
    
    If PyTorch or CUDA is NOT available and force_halt=True, prints explicit error diagnostic
    and terminates execution with status code 1.
    """
    config = load_config()
    
    print("=" * 70)
    print(" HARDWARE MONITOR & REMOTE GPU GUARD")
    print("=" * 70)
    
    if not TORCH_AVAILABLE:
        print("PyTorch Version: Not Installed (Local Lightweight Mode)")
        print("CUDA Available:  False")
        print("\n" + "!" * 70)
        print(" CRITICAL NOTICE: PYTORCH NOT INSTALLED LOCALLY / NO CUDA GPU")
        print("!" * 70)
        print("Project Guidelines Violation:")
        print(" - Local computer does NOT have a CUDA/NVIDIA GPU.")
        print(" - Heavy ML/YOLO model training on local CPU is STRICTLY PROHIBITED.")
        print(" - All heavy training must run remotely on Google Colab GPU.")
        print("\nAction Required:")
        print(" 1. Upload this project repository or open notebooks/Remote_Colab_YOLO11s_RDD2022.ipynb in Google Colab.")
        print(" 2. Set Colab Runtime to T4 GPU or higher (Runtime -> Change runtime type -> T4 GPU).")
        print(" 3. Execute training remotely inside Google Colab.")
        print("!" * 70 + "\n")
        
        if force_halt:
            print("Stopping execution immediately (preventing silent CPU training fallback).")
            sys.exit(1)
        return False, "None"

    cuda_available = torch.cuda.is_available()
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Available:  {cuda_available}")
    
    if cuda_available:
        gpu_count = torch.cuda.device_count()
        gpu_name = torch.cuda.get_device_name(0)
        print(f"GPU Device Count: {gpu_count}")
        print(f"Active GPU Name:  {gpu_name}")
        print("Status: Remote GPU Guard PASSED - Training permitted.")
        print("=" * 70 + "\n")
        return True, gpu_name
    else:
        print("\n" + "!" * 70)
        print(" CRITICAL ERROR: NO CUDA GPU DETECTED!")
        print("!" * 70)
        print("Project Guidelines Violation:")
        print(" - Local computer does NOT have a CUDA/NVIDIA GPU.")
        print(" - Heavy ML/YOLO model training on local CPU is STRICTLY PROHIBITED.")
        print(" - All heavy training must run remotely on Google Colab GPU.")
        print("\nAction Required:")
        print(" 1. Upload this project repository or open notebooks/Remote_Colab_YOLO11s_RDD2022.ipynb in Google Colab.")
        print(" 2. Set Colab Runtime to T4 GPU or higher (Runtime -> Change runtime type -> T4 GPU).")
        print(" 3. Execute training remotely inside Google Colab.")
        print("!" * 70 + "\n")
        
        if force_halt:
            print("Stopping execution immediately (preventing silent CPU training fallback).")
            sys.exit(1)
        return False, "None"

if __name__ == "__main__":
    verify_gpu_availability(force_halt=False)
