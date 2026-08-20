import os
import sys
import shutil
import glob
import yaml
from pathlib import Path
from tqdm import tqdm

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, RDD2022_DATA_DIR

def prepare_rdd2022_4class(raw_dir=None, output_dir=None):
    """
    Phase 10: RDD2022 Four-Class Dataset Preparation (D00, D10, D20, D40).
    """
    ensure_directories()
    
    if raw_dir is None:
        raw_dir = PROJECT_ROOT / "dataset" / "RDD2022-India.v1i.darknet"
    else:
        raw_dir = Path(raw_dir)

    if output_dir is None:
        output_dir = RDD2022_DATA_DIR / "RDD2022_4CLASS"
    else:
        output_dir = Path(output_dir)

    print(f"[Phase 10 - RDD2022 Prep] Preparing 4-Class Dataset from: {raw_dir}")
    print(f"[Phase 10 - RDD2022 Prep] Output Directory: {output_dir}")

    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw RDD2022 dataset directory not found at: {raw_dir}")

    allowed_classes = {0, 1, 2, 3}
    class_names = [
        "D00_Longitudinal_Crack",
        "D10_Transverse_Crack",
        "D20_Alligator_Crack",
        "D40_Pothole_Rutting_Separation"
    ]

    splits = {"train": "train", "valid": "val", "test": "test"}
    
    for split_src, split_dst in splits.items():
        src_split_dir = raw_dir / split_src
        dst_img_dir = output_dir / "images" / split_dst
        dst_lbl_dir = output_dir / "labels" / split_dst

        dst_img_dir.mkdir(parents=True, exist_ok=True)
        dst_lbl_dir.mkdir(parents=True, exist_ok=True)

        if not src_split_dir.exists():
            continue

        jpg_files = glob.glob(str(src_split_dir / "*.jpg"))
        print(f" Processing '{split_src}' -> '{split_dst}' ({len(jpg_files)} images)...")

        for img_path in tqdm(jpg_files, desc=f"Split {split_src}"):
            img_path = Path(img_path)
            txt_path = img_path.with_suffix(".txt")

            dst_img_path = dst_img_dir / img_path.name
            dst_txt_path = dst_lbl_dir / txt_path.name

            shutil.copy2(img_path, dst_img_path)

            if txt_path.exists():
                filtered_lines = []
                with open(txt_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if not parts:
                            continue
                        cid = int(parts[0])
                        if cid in allowed_classes:
                            filtered_lines.append(f"{cid} " + " ".join(parts[1:]))

                with open(dst_txt_path, "w", encoding="utf-8") as f:
                    if filtered_lines:
                        f.write("\n".join(filtered_lines) + "\n")
            else:
                dst_txt_path.touch()

    # Generate data.yaml
    data_yaml_path = output_dir / "data.yaml"
    data_yaml_content = {
        "path": str(output_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 4,
        "names": class_names
    }

    with open(data_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml_content, f, default_flow_style=False)

    print("\n" + "=" * 60)
    print(" PHASE 10: RDD2022 FOUR-CLASS PREPARATION COMPLETE")
    print("=" * 60)
    print(f" Data Config Generated: {data_yaml_path}")
    print(f" Number of Classes: 4")
    print(f" Class Names: {class_names}")
    print("=" * 60 + "\n")

    return str(data_yaml_path)

if __name__ == "__main__":
    prepare_rdd2022_4class()
