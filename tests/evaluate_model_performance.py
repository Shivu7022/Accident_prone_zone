"""
Model Performance Evaluation Script
====================================
This script evaluates the performance of both detection models:
1. YOLO11s Road Damage Detector
2. YOLO11n Indian Traffic Sign Detector
3. ResNet18 Traffic Sign Classifier

Metrics Calculated:
- Precision
- Recall
- mAP@0.5 (mean Average Precision at IoU threshold 0.5)
- Inference time (ms/frame)

Usage:
    python evaluate_model_performance.py

Requirements:
    - Test dataset with ground truth annotations in YOLO format
    - Model files present in respective directories
"""

import time
import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import cv2
from PIL import Image
import torch
import torch.nn as nn
from torchvision import models, transforms
from ultralytics import YOLO


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Model Paths
ROAD_DAMAGE_MODEL_PATH = BASE_DIR / "backend" / "road_damage_api" / "models" / "YOLO11s_road_damage_640_best.pt"
TRAFFIC_SIGN_DETECTOR_PATH = BASE_DIR / "traffic_sign_api" / "models" / "indian_traffic_sign_yolo11n.pt"
TRAFFIC_SIGN_CLASSIFIER_PATH = BASE_DIR / "traffic_sign_api" / "resnet18_gtsrb_best.pth"
TRAFFIC_SIGN_CLASS_NAMES = BASE_DIR / "traffic_sign_api" / "class_names.json"

# Test Dataset Paths (to be configured by user)
ROAD_DAMAGE_TEST_DIR = BASE_DIR / "test_data" / "road_damage"  # Should contain images and labels
TRAFFIC_SIGN_TEST_DIR = BASE_DIR / "test_data" / "traffic_sign"  # Should contain images and labels

# Device Configuration
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Evaluation Parameters
CONFIDENCE_THRESHOLD = 0.25
IOU_THRESHOLD = 0.5
NUM_WARMUP_RUNS = 5
NUM_EVAL_RUNS = 50


# ============================================================
# METRIC CALCULATION FUNCTIONS
# ============================================================

def calculate_iou(box1: List[float], box2: List[float]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    Boxes are in format [x1, y1, x2, y2].
    """
    x1_inter = max(box1[0], box2[0])
    y1_inter = max(box1[1], box2[1])
    x2_inter = min(box1[2], box2[2])
    y2_inter = min(box1[3], box2[3])

    if x2_inter <= x1_inter or y2_inter <= y1_inter:
        return 0.0

    inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])

    union_area = box1_area + box2_area - inter_area
    return inter_area / union_area if union_area > 0 else 0.0


def calculate_precision_recall(pred_boxes: List[Dict], gt_boxes: List[Dict], iou_threshold: float = 0.5) -> Tuple[float, float]:
    """
    Calculate precision and recall for a single image.
    """
    if len(gt_boxes) == 0:
        # No ground truth boxes
        if len(pred_boxes) == 0:
            return 1.0, 1.0  # Perfect match
        else:
            return 0.0, 1.0  # False positives only

    if len(pred_boxes) == 0:
        # No predictions but ground truth exists
        return 0.0, 0.0  # All false negatives

    # Match predictions to ground truth
    matched_gt = set()
    true_positives = 0

    for pred in pred_boxes:
        pred_box = pred['bounding_box']
        best_iou = 0.0
        best_gt_idx = -1

        for gt_idx, gt in enumerate(gt_boxes):
            if gt_idx in matched_gt:
                continue
            gt_box = gt['bounding_box']
            iou = calculate_iou(pred_box, gt_box)
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = gt_idx

        if best_iou >= iou_threshold:
            true_positives += 1
            matched_gt.add(best_gt_idx)

    false_positives = len(pred_boxes) - true_positives
    false_negatives = len(gt_boxes) - true_positives

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0

    return precision, recall


def calculate_ap(precision_recall_curve: List[Tuple[float, float]]) -> float:
    """
    Calculate Average Precision (AP) using the 11-point interpolation method.
    """
    if not precision_recall_curve:
        return 0.0

    # Sort by recall descending
    precision_recall_curve.sort(key=lambda x: x[1], reverse=True)

    # 11-point interpolation
    recall_levels = np.linspace(0, 1, 11)
    interpolated_precision = []

    for recall_level in recall_levels:
        max_precision = 0.0
        for precision, recall in precision_recall_curve:
            if recall >= recall_level:
                max_precision = max(max_precision, precision)
        interpolated_precision.append(max_precision)

    return np.mean(interpolated_precision)


# ============================================================
# MODEL EVALUATION CLASSES
# ============================================================

class RoadDamageEvaluator:
    """Evaluator for YOLO11s Road Damage Detector"""

    def __init__(self):
        self.model = None
        self.model_name = "YOLO11s Road Damage Detector"
        self.inference_times = []

    def load_model(self):
        if not ROAD_DAMAGE_MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found: {ROAD_DAMAGE_MODEL_PATH}")
        self.model = YOLO(str(ROAD_DAMAGE_MODEL_PATH))
        print(f"✓ Loaded {self.model_name}")

    def predict(self, image):
        """Run prediction on an image."""
        results = self.model.predict(source=image, conf=CONFIDENCE_THRESHOLD, imgsz=640, verbose=False)
        detections = []

        if results[0].boxes is not None:
            for box in results[0].boxes:
                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = box.xyxy[0].cpu().tolist()
                class_name = self.model.names.get(class_id, str(class_id))

                detections.append({
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "bounding_box": [x1, y1, x2, y2]
                })

        return detections

    def evaluate_on_dataset(self, test_dir: Path):
        """Evaluate model on test dataset."""
        if not test_dir.exists():
            print(f"⚠ Test directory not found: {test_dir}")
            print("  Creating placeholder evaluation with mock data...")

            # Return placeholder metrics
            return {
                "precision": 0.0,
                "recall": 0.0,
                "mAP@0.5": 0.0,
                "avg_inference_time_ms": 0.0,
                "num_images": 0,
                "note": "Test dataset not available - run with actual test data for real metrics"
            }

        print(f"\nEvaluating {self.model_name} on {test_dir}...")

        all_precisions = []
        all_recalls = []
        all_detections = []

        image_files = list(test_dir.glob("*.jpg")) + list(test_dir.glob("*.png"))

        for img_file in image_files:
            # Load image
            image = cv2.imread(str(img_file))
            if image is None:
                continue

            # Load ground truth (if available)
            label_file = test_dir / "labels" / f"{img_file.stem}.txt"
            gt_boxes = []
            if label_file.exists():
                with open(label_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            class_id = int(parts[0])
                            # Convert YOLO format to [x1, y1, x2, y2]
                            img_h, img_w = image.shape[:2]
                            x_center, y_center, width, height = map(float, parts[1:5])
                            x1 = (x_center - width / 2) * img_w
                            y1 = (y_center - height / 2) * img_h
                            x2 = (x_center + width / 2) * img_w
                            y2 = (y_center + height / 2) * img_h
                            gt_boxes.append({
                                "class_id": class_id,
                                "bounding_box": [x1, y1, x2, y2]
                            })

            # Run prediction
            pred_boxes = self.predict(image)

            # Calculate metrics
            precision, recall = calculate_precision_recall(pred_boxes, gt_boxes, IOU_THRESHOLD)
            all_precisions.append(precision)
            all_recalls.append(recall)
            all_detections.extend(pred_boxes)

        avg_precision = np.mean(all_precisions) if all_precisions else 0.0
        avg_recall = np.mean(all_recalls) if all_recalls else 0.0
        mAP = calculate_ap(list(zip(all_precisions, all_recalls)))

        return {
            "precision": avg_precision,
            "recall": avg_recall,
            "mAP@0.5": mAP,
            "num_images": len(image_files)
        }

    def measure_inference_speed(self, test_image_path: Path = None):
        """Measure average inference time per frame."""
        print(f"\nMeasuring inference speed for {self.model_name}...")

        # Create a dummy image if no test image provided
        if test_image_path is None or not test_image_path.exists():
            dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        else:
            dummy_image = cv2.imread(str(test_image_path))
            if dummy_image is None:
                dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

        # Warmup runs
        for _ in range(NUM_WARMUP_RUNS):
            self.predict(dummy_image)

        # Timed runs
        times = []
        for _ in range(NUM_EVAL_RUNS):
            start_time = time.perf_counter()
            self.predict(dummy_image)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # Convert to ms

        avg_time = np.mean(times)
        std_time = np.std(times)

        return {
            "avg_inference_time_ms": avg_time,
            "std_inference_time_ms": std_time,
            "num_runs": NUM_EVAL_RUNS
        }


class TrafficSignDetectorEvaluator:
    """Evaluator for YOLO11n Indian Traffic Sign Detector"""

    def __init__(self):
        self.model = None
        self.model_name = "YOLO11n Traffic Sign Detector"
        self.inference_times = []

    def load_model(self):
        if not TRAFFIC_SIGN_DETECTOR_PATH.exists():
            raise FileNotFoundError(f"Model not found: {TRAFFIC_SIGN_DETECTOR_PATH}")
        self.model = YOLO(str(TRAFFIC_SIGN_DETECTOR_PATH))
        print(f"✓ Loaded {self.model_name}")

    def predict(self, image):
        """Run prediction on an image."""
        results = self.model.predict(source=image, conf=CONFIDENCE_THRESHOLD, imgsz=640, device="cpu", verbose=False)
        detections = []

        if results[0].boxes is not None:
            for box in results[0].boxes:
                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = box.xyxy[0].cpu().tolist()
                class_name = self.model.names.get(class_id, "traffic_sign")

                detections.append({
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "bounding_box": [x1, y1, x2, y2]
                })

        return detections

    def evaluate_on_dataset(self, test_dir: Path):
        """Evaluate model on test dataset."""
        if not test_dir.exists():
            print(f"⚠ Test directory not found: {test_dir}")
            print("  Creating placeholder evaluation with mock data...")

            return {
                "precision": 0.0,
                "recall": 0.0,
                "mAP@0.5": 0.0,
                "avg_inference_time_ms": 0.0,
                "num_images": 0,
                "note": "Test dataset not available - run with actual test data for real metrics"
            }

        print(f"\nEvaluating {self.model_name} on {test_dir}...")

        all_precisions = []
        all_recalls = []

        image_files = list(test_dir.glob("*.jpg")) + list(test_dir.glob("*.png"))

        for img_file in image_files:
            image = cv2.imread(str(img_file))
            if image is None:
                continue

            label_file = test_dir / "labels" / f"{img_file.stem}.txt"
            gt_boxes = []
            if label_file.exists():
                with open(label_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            class_id = int(parts[0])
                            img_h, img_w = image.shape[:2]
                            x_center, y_center, width, height = map(float, parts[1:5])
                            x1 = (x_center - width / 2) * img_w
                            y1 = (y_center - height / 2) * img_h
                            x2 = (x_center + width / 2) * img_w
                            y2 = (y_center + height / 2) * img_h
                            gt_boxes.append({
                                "class_id": class_id,
                                "bounding_box": [x1, y1, x2, y2]
                            })

            pred_boxes = self.predict(image)
            precision, recall = calculate_precision_recall(pred_boxes, gt_boxes, IOU_THRESHOLD)
            all_precisions.append(precision)
            all_recalls.append(recall)

        avg_precision = np.mean(all_precisions) if all_precisions else 0.0
        avg_recall = np.mean(all_recalls) if all_recalls else 0.0
        mAP = calculate_ap(list(zip(all_precisions, all_recalls)))

        return {
            "precision": avg_precision,
            "recall": avg_recall,
            "mAP@0.5": mAP,
            "num_images": len(image_files)
        }

    def measure_inference_speed(self, test_image_path: Path = None):
        """Measure average inference time per frame."""
        print(f"\nMeasuring inference speed for {self.model_name}...")

        if test_image_path is None or not test_image_path.exists():
            dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        else:
            dummy_image = cv2.imread(str(test_image_path))
            if dummy_image is None:
                dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

        for _ in range(NUM_WARMUP_RUNS):
            self.predict(dummy_image)

        times = []
        for _ in range(NUM_EVAL_RUNS):
            start_time = time.perf_counter()
            self.predict(dummy_image)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)

        avg_time = np.mean(times)
        std_time = np.std(times)

        return {
            "avg_inference_time_ms": avg_time,
            "std_inference_time_ms": std_time,
            "num_runs": NUM_EVAL_RUNS
        }


class TrafficSignClassifierEvaluator:
    """Evaluator for ResNet18 Traffic Sign Classifier"""

    def __init__(self):
        self.model = None
        self.transform = None
        self.class_names = {}
        self.model_name = "ResNet18 Traffic Sign Classifier"

    def load_model(self):
        if not TRAFFIC_SIGN_CLASSIFIER_PATH.exists():
            raise FileNotFoundError(f"Model not found: {TRAFFIC_SIGN_CLASSIFIER_PATH}")

        # Load class names
        if TRAFFIC_SIGN_CLASS_NAMES.exists():
            with open(TRAFFIC_SIGN_CLASS_NAMES, 'r') as f:
                raw_classes = json.load(f)
            if isinstance(raw_classes, dict):
                self.class_names = {int(k): v for k, v in raw_classes.items()}
            else:
                self.class_names = {i: v for i, v in enumerate(raw_classes)}

        # Load model
        self.model = models.resnet18(weights=None)
        self.model.fc = nn.Linear(self.model.fc.in_features, 43)
        checkpoint = torch.load(TRAFFIC_SIGN_CLASSIFIER_PATH, map_location=DEVICE, weights_only=False)

        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
        else:
            self.model.load_state_dict(checkpoint)

        self.model.to(DEVICE)
        self.model.eval()

        # Define transform
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        print(f"✓ Loaded {self.model_name}")

    def predict(self, image):
        """Run prediction on an image."""
        if isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        image_tensor = self.transform(image).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            outputs = self.model(image_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, dim=1)

        class_id = int(predicted.item())
        return {
            "class_id": class_id,
            "class_name": self.class_names.get(class_id, str(class_id)),
            "confidence": float(confidence.item())
        }

    def evaluate_on_dataset(self, test_dir: Path):
        """Evaluate classifier on test dataset."""
        if not test_dir.exists():
            print(f"⚠ Test directory not found: {test_dir}")
            print("  Creating placeholder evaluation with mock data...")

            return {
                "accuracy": 0.0,
                "avg_inference_time_ms": 0.0,
                "num_images": 0,
                "note": "Test dataset not available - run with actual test data for real metrics"
            }

        print(f"\nEvaluating {self.model_name} on {test_dir}...")

        correct = 0
        total = 0

        image_files = list(test_dir.glob("*.jpg")) + list(test_dir.glob("*.png"))

        for img_file in image_files:
            # Assume class is encoded in folder name or filename
            # This is a simplified approach - actual implementation depends on dataset structure
            image = cv2.imread(str(img_file))
            if image is None:
                continue

            # Get ground truth class from filename (assuming format: classid_imagename.jpg)
            try:
                gt_class = int(img_file.stem.split('_')[0])
            except (ValueError, IndexError):
                continue

            prediction = self.predict(image)
            pred_class = prediction["class_id"]

            if pred_class == gt_class:
                correct += 1
            total += 1

        accuracy = correct / total if total > 0 else 0.0

        return {
            "accuracy": accuracy,
            "num_images": total
        }

    def measure_inference_speed(self, test_image_path: Path = None):
        """Measure average inference time per frame."""
        print(f"\nMeasuring inference speed for {self.model_name}...")

        if test_image_path is None or not test_image_path.exists():
            dummy_image = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
        else:
            dummy_image = Image.open(test_image_path).convert("RGB")

        for _ in range(NUM_WARMUP_RUNS):
            self.predict(dummy_image)

        times = []
        for _ in range(NUM_EVAL_RUNS):
            start_time = time.perf_counter()
            self.predict(dummy_image)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)

        avg_time = np.mean(times)
        std_time = np.std(times)

        return {
            "avg_inference_time_ms": avg_time,
            "std_inference_time_ms": std_time,
            "num_runs": NUM_EVAL_RUNS
        }


# ============================================================
# MAIN EVALUATION FUNCTION
# ============================================================

def main():
    print("=" * 70)
    print("MODEL PERFORMANCE EVALUATION")
    print("=" * 70)
    print(f"Device: {DEVICE}")
    print(f"Confidence Threshold: {CONFIDENCE_THRESHOLD}")
    print(f"IoU Threshold: {IOU_THRESHOLD}")
    print(f"Evaluation Runs: {NUM_EVAL_RUNS}")
    print("=" * 70)

    results = {}

    # Evaluate Road Damage Detector
    try:
        print("\n[1/3] Evaluating Road Damage Detector")
        print("-" * 70)
        road_evaluator = RoadDamageEvaluator()
        road_evaluator.load_model()

        detection_metrics = road_evaluator.evaluate_on_dataset(ROAD_DAMAGE_TEST_DIR)
        speed_metrics = road_evaluator.measure_inference_speed()

        results["road_damage_detector"] = {
            **detection_metrics,
            **speed_metrics,
            "model_name": road_evaluator.model_name
        }

        print(f"\nResults for {road_evaluator.model_name}:")
        print(f"  Precision: {detection_metrics['precision']:.4f}")
        print(f"  Recall: {detection_metrics['recall']:.4f}")
        print(f"  mAP@0.5: {detection_metrics['mAP@0.5']:.4f}")
        print(f"  Avg Inference Time: {speed_metrics['avg_inference_time_ms']:.2f} ms/frame")
        if 'note' in detection_metrics:
            print(f"  Note: {detection_metrics['note']}")

    except Exception as e:
        print(f"✗ Error evaluating road damage detector: {e}")
        results["road_damage_detector"] = {"error": str(e)}

    # Evaluate Traffic Sign Detector
    try:
        print("\n[2/3] Evaluating Traffic Sign Detector")
        print("-" * 70)
        sign_detector_evaluator = TrafficSignDetectorEvaluator()
        sign_detector_evaluator.load_model()

        detection_metrics = sign_detector_evaluator.evaluate_on_dataset(TRAFFIC_SIGN_TEST_DIR)
        speed_metrics = sign_detector_evaluator.measure_inference_speed()

        results["traffic_sign_detector"] = {
            **detection_metrics,
            **speed_metrics,
            "model_name": sign_detector_evaluator.model_name
        }

        print(f"\nResults for {sign_detector_evaluator.model_name}:")
        print(f"  Precision: {detection_metrics['precision']:.4f}")
        print(f"  Recall: {detection_metrics['recall']:.4f}")
        print(f"  mAP@0.5: {detection_metrics['mAP@0.5']:.4f}")
        print(f"  Avg Inference Time: {speed_metrics['avg_inference_time_ms']:.2f} ms/frame")
        if 'note' in detection_metrics:
            print(f"  Note: {detection_metrics['note']}")

    except Exception as e:
        print(f"✗ Error evaluating traffic sign detector: {e}")
        results["traffic_sign_detector"] = {"error": str(e)}

    # Evaluate Traffic Sign Classifier
    try:
        print("\n[3/3] Evaluating Traffic Sign Classifier")
        print("-" * 70)
        sign_classifier_evaluator = TrafficSignClassifierEvaluator()
        sign_classifier_evaluator.load_model()

        detection_metrics = sign_classifier_evaluator.evaluate_on_dataset(TRAFFIC_SIGN_TEST_DIR)
        speed_metrics = sign_classifier_evaluator.measure_inference_speed()

        results["traffic_sign_classifier"] = {
            **detection_metrics,
            **speed_metrics,
            "model_name": sign_classifier_evaluator.model_name
        }

        print(f"\nResults for {sign_classifier_evaluator.model_name}:")
        print(f"  Accuracy: {detection_metrics['accuracy']:.4f}")
        print(f"  Avg Inference Time: {speed_metrics['avg_inference_time_ms']:.2f} ms/frame")
        if 'note' in detection_metrics:
            print(f"  Note: {detection_metrics['note']}")

    except Exception as e:
        print(f"✗ Error evaluating traffic sign classifier: {e}")
        results["traffic_sign_classifier"] = {"error": str(e)}

    # Save results to JSON
    results_file = BASE_DIR / "tests" / "model_performance_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    print(f"Results saved to: {results_file}")
    print("=" * 70)

    # Print Table VI format
    print("\nTABLE VI: Model Performance Comparison")
    print("=" * 70)
    print(f"{'Model':<35} {'Precision':<12} {'Recall':<12} {'mAP@0.5':<12} {'ms/frame':<12}")
    print("-" * 70)

    for model_key in ["road_damage_detector", "traffic_sign_detector"]:
        if model_key in results and "error" not in results[model_key]:
            model_data = results[model_key]
            print(f"{model_data['model_name']:<35} "
                  f"{model_data['precision']:<12.4f} "
                  f"{model_data['recall']:<12.4f} "
                  f"{model_data['mAP@0.5']:<12.4f} "
                  f"{model_data['avg_inference_time_ms']:<12.2f}")

    print("=" * 70)

    return results


if __name__ == "__main__":
    main()
