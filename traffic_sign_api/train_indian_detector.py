import os
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from huggingface_hub import snapshot_download
from ultralytics import YOLO


DATASET_ID = "Dataclusterlabspvtltd/Indian_Traffic_Sign_Image_Dataset"
IMAGE_GLOB = "images/images/*.jpg"
ANNOTATION_GLOB = "Annotations/Annotations/*.xml"
SEED = 42
VALIDATION_FRACTION = 0.2


def normalized_box(box, width, height):
    xmin = max(0.0, min(float(box.findtext("xmin", "0")), width))
    ymin = max(0.0, min(float(box.findtext("ymin", "0")), height))
    xmax = max(0.0, min(float(box.findtext("xmax", "0")), width))
    ymax = max(0.0, min(float(box.findtext("ymax", "0")), height))
    if xmax <= xmin or ymax <= ymin:
        return None

    return (
        (xmin + xmax) / (2 * width),
        (ymin + ymax) / (2 * height),
        (xmax - xmin) / width,
        (ymax - ymin) / height,
    )


def make_label_file(annotation_path, output_path):
    root = ET.parse(annotation_path).getroot()
    size = root.find("size")
    width = float(size.findtext("width"))
    height = float(size.findtext("height"))
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image dimensions in {annotation_path}")

    labels = []
    for object_node in root.findall("object"):
        if object_node.findtext("name", "").strip().lower() != "traffic_sign":
            raise ValueError(f"Unexpected class in {annotation_path}")
        box = object_node.find("bndbox")
        values = (
            normalized_box(box, width, height)
            if box is not None
            else None
        )
        if values:
            labels.append("0 " + " ".join(f"{value:.6f}" for value in values))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(labels), encoding="utf-8")


def link_or_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def main():
    training_home = Path(
        os.environ.get(
            "ROADSAVE_TRAINING_HOME",
            Path.home() / ".roadsafe_training",
        )
    ).expanduser()
    raw_dataset = training_home / "indian_sign_sample"
    yolo_dataset = training_home / "indian_sign_yolo"
    runs_dir = training_home / "runs"

    snapshot_download(
        repo_id=DATASET_ID,
        repo_type="dataset",
        local_dir=str(raw_dataset),
        allow_patterns=[IMAGE_GLOB, ANNOTATION_GLOB],
    )

    image_dir = raw_dataset / "images" / "images"
    annotation_dir = raw_dataset / "Annotations" / "Annotations"
    images = sorted(image_dir.glob("*.jpg"))
    annotations = {path.stem: path for path in annotation_dir.glob("*.xml")}
    missing_annotations = [
        path.name for path in images if path.stem not in annotations
    ]
    unmatched_annotations = set(annotations) - {path.stem for path in images}
    if missing_annotations or unmatched_annotations:
        raise ValueError(
            "Dataset image/annotation mismatch: "
            f"{len(missing_annotations)} images and "
            f"{len(unmatched_annotations)} annotations are unmatched."
        )
    if len(images) < 10:
        raise ValueError(
            "At least 10 paired images are required to train and validate."
        )

    random.Random(SEED).shuffle(images)
    validation_count = max(1, round(len(images) * VALIDATION_FRACTION))
    split_paths = {
        "train": images[validation_count:],
        "val": images[:validation_count],
    }

    for split, split_images in split_paths.items():
        for image_path in split_images:
            link_or_copy(
                image_path,
                yolo_dataset / "images" / split / image_path.name,
            )
            make_label_file(
                annotations[image_path.stem],
                yolo_dataset / "labels" / split / f"{image_path.stem}.txt",
            )

    data_yaml = yolo_dataset / "dataset.yaml"
    data_yaml.write_text(
        yaml.safe_dump(
            {
                "path": yolo_dataset.resolve().as_posix(),
                "train": "images/train",
                "val": "images/val",
                "names": {0: "traffic_sign"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    model = YOLO("yolo11n.pt")
    model.train(
        data=str(data_yaml),
        epochs=15,
        imgsz=640,
        batch=2,
        device="cpu",
        workers=0,
        seed=SEED,
        patience=5,
        cache=False,
        plots=False,
        project=str(runs_dir),
        name="indian_sign_detector",
        exist_ok=True,
    )

    best_weights = Path(model.trainer.best)
    detector_dir = Path(__file__).resolve().parent / "models"
    detector_dir.mkdir(parents=True, exist_ok=True)
    output_weights = detector_dir / "indian_traffic_sign_yolo11n.pt"
    shutil.copy2(best_weights, output_weights)

    metrics = model.val(
        data=str(data_yaml),
        split="val",
        imgsz=640,
        batch=2,
        device="cpu",
        plots=False,
    )
    print(f"Training images: {len(split_paths['train'])}")
    print(f"Validation images: {len(split_paths['val'])}")
    print(f"Validation mAP50: {metrics.box.map50:.4f}")
    print(f"Validation mAP50-95: {metrics.box.map:.4f}")
    print(f"Local detector weights: {output_weights}")
    print(
        "Research sample: academic use with attribution only; "
        "do not redistribute or use commercially."
    )


if __name__ == "__main__":
    main()
