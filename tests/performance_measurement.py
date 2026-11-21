"""
Performance Measurement Script
================================
This script measures performance metrics for the detection pipeline:
1. Frame Delay - Time from frame capture to detection result
2. CPU Usage - CPU utilization during inference
3. Latency Cost - End-to-end latency of detection pipeline
4. Memory Usage - Memory consumption during inference

Metrics measured for:
- Road Damage Detection (YOLO11s)
- Traffic Sign Detection (YOLO11n)
- Traffic Sign Classification (ResNet18)

Usage:
    python performance_measurement.py

Requirements:
    - All backend servers running
    - psutil package for CPU/memory monitoring
"""

import asyncio
import httpx
import time
import psutil
import threading
from pathlib import Path
from typing import Dict, List
import json
import numpy as np
import cv2
from dataclasses import dataclass
from collections import deque


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# API Endpoints
MAIN_BACKEND_URL = "http://127.0.0.1:8001"
TRAFFIC_SIGN_API_URL = "http://127.0.0.1:8000"
ROAD_DAMAGE_API_URL = "http://127.0.0.1:8002"

ENDPOINTS = {
    "road_damage": f"{ROAD_DAMAGE_API_URL}/predict",
    "traffic_sign_detect": f"{TRAFFIC_SIGN_API_URL}/api/signboard/detect/",
    "traffic_sign_classify": f"{TRAFFIC_SIGN_API_URL}/api/signboard/predict/"
}

# Test Configuration
NUM_FRAMES = 30  # Number of frames to test
INTER_FRAME_DELAY = 0.1  # Seconds between frames (simulating 10 FPS)
TIMEOUT = 60.0

# Image Configuration
TEST_IMAGE_SIZE = (640, 640)
CLASSIFICATION_IMAGE_SIZE = (224, 224)


# ============================================================
# PERFORMANCE METRICS DATA CLASS
# ============================================================

@dataclass
class PerformanceMetrics:
    """Stores performance metrics for a single inference run."""
    frame_number: int
    capture_time: float
    request_sent_time: float
    response_received_time: float
    processing_time: float  # Total time from capture to result
    api_latency: float  # Time from request sent to response received
    cpu_percent: float
    memory_mb: float
    status: str  # "success" or "error"
    error_message: str = None


# ============================================================
# CPU/MONITORING THREAD
# ============================================================

class ResourceMonitor:
    """Monitors CPU and memory usage in a separate thread."""

    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self.running = False
        self.cpu_samples = deque(maxlen=100)
        self.memory_samples = deque(maxlen=100)
        self.thread = None

    def start(self):
        """Start monitoring in a separate thread."""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def _monitor_loop(self):
        """Monitoring loop."""
        process = psutil.Process()

        while self.running:
            try:
                cpu_percent = process.cpu_percent(interval=self.interval)
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)

                self.cpu_samples.append(cpu_percent)
                self.memory_samples.append(memory_mb)
            except Exception:
                pass

    def get_average_cpu(self) -> float:
        """Get average CPU usage."""
        if not self.cpu_samples:
            return 0.0
        return sum(self.cpu_samples) / len(self.cpu_samples)

    def get_average_memory(self) -> float:
        """Get average memory usage in MB."""
        if not self.memory_samples:
            return 0.0
        return sum(self.memory_samples) / len(self.memory_samples)

    def get_peak_memory(self) -> float:
        """Get peak memory usage in MB."""
        if not self.memory_samples:
            return 0.0
        return max(self.memory_samples)


# ============================================================
# TEST FUNCTIONS
# ============================================================

async def measure_road_damage_performance(
    client: httpx.AsyncClient,
    num_frames: int = NUM_FRAMES
) -> List[PerformanceMetrics]:
    """Measure performance for road damage detection."""
    print("\n[1/3] Measuring Road Damage Detection Performance")
    print("-" * 70)

    metrics = []
    monitor = ResourceMonitor(interval=0.05)
    monitor.start()

    try:
        for i in range(num_frames):
            # Simulate frame capture
            capture_time = time.perf_counter()

            # Create test image
            test_image = np.random.randint(0, 255, (*TEST_IMAGE_SIZE, 3), dtype=np.uint8)
            _, buffer = cv2.imencode('.jpg', test_image)
            image_bytes = buffer.tobytes()

            # Send request
            request_sent_time = time.perf_counter()

            files = {
                "file": (f"frame_{i}.jpg", image_bytes, "image/jpeg")
            }

            try:
                response = await client.post(
                    ENDPOINTS["road_damage"],
                    files=files,
                    timeout=TIMEOUT
                )

                response_received_time = time.perf_counter()

                if response.status_code == 200:
                    metric = PerformanceMetrics(
                        frame_number=i + 1,
                        capture_time=capture_time,
                        request_sent_time=request_sent_time,
                        response_received_time=response_received_time,
                        processing_time=response_received_time - capture_time,
                        api_latency=response_received_time - request_sent_time,
                        cpu_percent=monitor.get_average_cpu(),
                        memory_mb=monitor.get_average_memory(),
                        status="success"
                    )
                else:
                    metric = PerformanceMetrics(
                        frame_number=i + 1,
                        capture_time=capture_time,
                        request_sent_time=request_sent_time,
                        response_received_time=response_received_time,
                        processing_time=response_received_time - capture_time,
                        api_latency=response_received_time - request_sent_time,
                        cpu_percent=monitor.get_average_cpu(),
                        memory_mb=monitor.get_average_memory(),
                        status="error",
                        error_message=f"HTTP {response.status_code}"
                    )
            except Exception as e:
                response_received_time = time.perf_counter()
                metric = PerformanceMetrics(
                    frame_number=i + 1,
                    capture_time=capture_time,
                    request_sent_time=request_sent_time,
                    response_received_time=response_received_time,
                    processing_time=response_received_time - capture_time,
                    api_latency=response_received_time - request_sent_time,
                    cpu_percent=monitor.get_average_cpu(),
                    memory_mb=monitor.get_average_memory(),
                    status="error",
                    error_message=str(e)
                )

            metrics.append(metric)

            # Print progress
            if (i + 1) % 5 == 0 or i == num_frames - 1:
                print(f"  Processed {i + 1}/{num_frames} frames...")

            # Simulate inter-frame delay
            if i < num_frames - 1:
                await asyncio.sleep(INTER_FRAME_DELAY)

    finally:
        monitor.stop()

    return metrics


async def measure_traffic_sign_detection_performance(
    client: httpx.AsyncClient,
    num_frames: int = NUM_FRAMES
) -> List[PerformanceMetrics]:
    """Measure performance for traffic sign detection."""
    print("\n[2/3] Measuring Traffic Sign Detection Performance")
    print("-" * 70)

    metrics = []
    monitor = ResourceMonitor(interval=0.05)
    monitor.start()

    try:
        for i in range(num_frames):
            capture_time = time.perf_counter()

            test_image = np.random.randint(0, 255, (*TEST_IMAGE_SIZE, 3), dtype=np.uint8)
            _, buffer = cv2.imencode('.jpg', test_image)
            image_bytes = buffer.tobytes()

            request_sent_time = time.perf_counter()

            files = {
                "file": (f"frame_{i}.jpg", image_bytes, "image/jpeg")
            }

            try:
                response = await client.post(
                    ENDPOINTS["traffic_sign_detect"],
                    files=files,
                    timeout=TIMEOUT
                )

                response_received_time = time.perf_counter()

                if response.status_code == 200:
                    metric = PerformanceMetrics(
                        frame_number=i + 1,
                        capture_time=capture_time,
                        request_sent_time=request_sent_time,
                        response_received_time=response_received_time,
                        processing_time=response_received_time - capture_time,
                        api_latency=response_received_time - request_sent_time,
                        cpu_percent=monitor.get_average_cpu(),
                        memory_mb=monitor.get_average_memory(),
                        status="success"
                    )
                else:
                    metric = PerformanceMetrics(
                        frame_number=i + 1,
                        capture_time=capture_time,
                        request_sent_time=request_sent_time,
                        response_received_time=response_received_time,
                        processing_time=response_received_time - capture_time,
                        api_latency=response_received_time - request_sent_time,
                        cpu_percent=monitor.get_average_cpu(),
                        memory_mb=monitor.get_average_memory(),
                        status="error",
                        error_message=f"HTTP {response.status_code}"
                    )
            except Exception as e:
                response_received_time = time.perf_counter()
                metric = PerformanceMetrics(
                    frame_number=i + 1,
                    capture_time=capture_time,
                    request_sent_time=request_sent_time,
                    response_received_time=response_received_time,
                    processing_time=response_received_time - capture_time,
                    api_latency=response_received_time - request_sent_time,
                    cpu_percent=monitor.get_average_cpu(),
                    memory_mb=monitor.get_average_memory(),
                    status="error",
                    error_message=str(e)
                )

            metrics.append(metric)

            if (i + 1) % 5 == 0 or i == num_frames - 1:
                print(f"  Processed {i + 1}/{num_frames} frames...")

            if i < num_frames - 1:
                await asyncio.sleep(INTER_FRAME_DELAY)

    finally:
        monitor.stop()

    return metrics


async def measure_traffic_sign_classification_performance(
    client: httpx.AsyncClient,
    num_frames: int = NUM_FRAMES
) -> List[PerformanceMetrics]:
    """Measure performance for traffic sign classification."""
    print("\n[3/3] Measuring Traffic Sign Classification Performance")
    print("-" * 70)

    metrics = []
    monitor = ResourceMonitor(interval=0.05)
    monitor.start()

    try:
        for i in range(num_frames):
            capture_time = time.perf_counter()

            test_image = np.random.randint(0, 255, (*CLASSIFICATION_IMAGE_SIZE, 3), dtype=np.uint8)
            _, buffer = cv2.imencode('.jpg', test_image)
            image_bytes = buffer.tobytes()

            request_sent_time = time.perf_counter()

            files = {
                "file": (f"frame_{i}.jpg", image_bytes, "image/jpeg")
            }

            try:
                response = await client.post(
                    ENDPOINTS["traffic_sign_classify"],
                    files=files,
                    timeout=TIMEOUT
                )

                response_received_time = time.perf_counter()

                if response.status_code == 200:
                    metric = PerformanceMetrics(
                        frame_number=i + 1,
                        capture_time=capture_time,
                        request_sent_time=request_sent_time,
                        response_received_time=response_received_time,
                        processing_time=response_received_time - capture_time,
                        api_latency=response_received_time - request_sent_time,
                        cpu_percent=monitor.get_average_cpu(),
                        memory_mb=monitor.get_average_memory(),
                        status="success"
                    )
                else:
                    metric = PerformanceMetrics(
                        frame_number=i + 1,
                        capture_time=capture_time,
                        request_sent_time=request_sent_time,
                        response_received_time=response_received_time,
                        processing_time=response_received_time - capture_time,
                        api_latency=response_received_time - request_sent_time,
                        cpu_percent=monitor.get_average_cpu(),
                        memory_mb=monitor.get_average_memory(),
                        status="error",
                        error_message=f"HTTP {response.status_code}"
                    )
            except Exception as e:
                response_received_time = time.perf_counter()
                metric = PerformanceMetrics(
                    frame_number=i + 1,
                    capture_time=capture_time,
                    request_sent_time=request_sent_time,
                    response_received_time=response_received_time,
                    processing_time=response_received_time - capture_time,
                    api_latency=response_received_time - request_sent_time,
                    cpu_percent=monitor.get_average_cpu(),
                    memory_mb=monitor.get_average_memory(),
                    status="error",
                    error_message=str(e)
                )

            metrics.append(metric)

            if (i + 1) % 5 == 0 or i == num_frames - 1:
                print(f"  Processed {i + 1}/{num_frames} frames...")

            if i < num_frames - 1:
                await asyncio.sleep(INTER_FRAME_DELAY)

    finally:
        monitor.stop()

    return metrics


# ============================================================
# METRICS CALCULATION
# ============================================================

def calculate_statistics(metrics: List[PerformanceMetrics]) -> Dict:
    """Calculate statistics from performance metrics."""
    successful_metrics = [m for m in metrics if m.status == "success"]

    if not successful_metrics:
        return {
            "total_frames": len(metrics),
            "successful_frames": 0,
            "failed_frames": len(metrics),
            "success_rate": 0.0,
            "note": "All requests failed"
        }

    processing_times = [m.processing_time * 1000 for m in successful_metrics]  # Convert to ms
    api_latencies = [m.api_latency * 1000 for m in successful_metrics]  # Convert to ms
    cpu_usage = [m.cpu_percent for m in successful_metrics]
    memory_usage = [m.memory_mb for m in successful_metrics]

    return {
        "total_frames": len(metrics),
        "successful_frames": len(successful_metrics),
        "failed_frames": len(metrics) - len(successful_metrics),
        "success_rate": len(successful_metrics) / len(metrics) * 100,

        # Frame Delay (processing time)
        "avg_frame_delay_ms": np.mean(processing_times),
        "std_frame_delay_ms": np.std(processing_times),
        "min_frame_delay_ms": np.min(processing_times),
        "max_frame_delay_ms": np.max(processing_times),
        "median_frame_delay_ms": np.median(processing_times),

        # API Latency
        "avg_api_latency_ms": np.mean(api_latencies),
        "std_api_latency_ms": np.std(api_latencies),
        "min_api_latency_ms": np.min(api_latencies),
        "max_api_latency_ms": np.max(api_latencies),

        # CPU Usage
        "avg_cpu_percent": np.mean(cpu_usage),
        "std_cpu_percent": np.std(cpu_usage),
        "max_cpu_percent": np.max(cpu_usage),

        # Memory Usage
        "avg_memory_mb": np.mean(memory_usage),
        "std_memory_mb": np.std(memory_usage),
        "max_memory_mb": np.max(memory_usage)
    }


# ============================================================
# MAIN PERFORMANCE MEASUREMENT
# ============================================================

async def run_performance_measurement():
    """Run performance measurement for all detection models."""
    print("=" * 70)
    print("PERFORMANCE MEASUREMENT")
    print("=" * 70)
    print(f"Number of frames per test: {NUM_FRAMES}")
    print(f"Inter-frame delay: {INTER_FRAME_DELAY}s")
    print(f"Timeout: {TIMEOUT}s")
    print("=" * 70)

    results = {}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Measure Road Damage Detection
        try:
            road_damage_metrics = await measure_road_damage_performance(client, NUM_FRAMES)
            road_damage_stats = calculate_statistics(road_damage_metrics)
            results["road_damage_detection"] = {
                "statistics": road_damage_stats,
                "raw_metrics": [m.__dict__ for m in road_damage_metrics]
            }

            print(f"\n[OK] Road Damage Detection:")
            print(f"  Success Rate: {road_damage_stats['success_rate']:.1f}%")
            print(f"  Avg Frame Delay: {road_damage_stats['avg_frame_delay_ms']:.2f} ms")
            print(f"  Avg API Latency: {road_damage_stats['avg_api_latency_ms']:.2f} ms")
            print(f"  Avg CPU Usage: {road_damage_stats['avg_cpu_percent']:.1f}%")
            print(f"  Avg Memory: {road_damage_stats['avg_memory_mb']:.1f} MB")

        except Exception as e:
            print(f"\n[X] Road Damage Detection Error: {e}")
            results["road_damage_detection"] = {"error": str(e)}

        # Measure Traffic Sign Detection
        try:
            traffic_sign_detect_metrics = await measure_traffic_sign_detection_performance(client, NUM_FRAMES)
            traffic_sign_detect_stats = calculate_statistics(traffic_sign_detect_metrics)
            results["traffic_sign_detection"] = {
                "statistics": traffic_sign_detect_stats,
                "raw_metrics": [m.__dict__ for m in traffic_sign_detect_metrics]
            }

            print(f"\n[OK] Traffic Sign Detection:")
            print(f"  Success Rate: {traffic_sign_detect_stats['success_rate']:.1f}%")
            print(f"  Avg Frame Delay: {traffic_sign_detect_stats['avg_frame_delay_ms']:.2f} ms")
            print(f"  Avg API Latency: {traffic_sign_detect_stats['avg_api_latency_ms']:.2f} ms")
            print(f"  Avg CPU Usage: {traffic_sign_detect_stats['avg_cpu_percent']:.1f}%")
            print(f"  Avg Memory: {traffic_sign_detect_stats['avg_memory_mb']:.1f} MB")

        except Exception as e:
            print(f"\n[X] Traffic Sign Detection Error: {e}")
            results["traffic_sign_detection"] = {"error": str(e)}

        # Measure Traffic Sign Classification
        try:
            traffic_sign_classify_metrics = await measure_traffic_sign_classification_performance(client, NUM_FRAMES)
            traffic_sign_classify_stats = calculate_statistics(traffic_sign_classify_metrics)
            results["traffic_sign_classification"] = {
                "statistics": traffic_sign_classify_stats,
                "raw_metrics": [m.__dict__ for m in traffic_sign_classify_metrics]
            }

            print(f"\n[OK] Traffic Sign Classification:")
            print(f"  Success Rate: {traffic_sign_classify_stats['success_rate']:.1f}%")
            print(f"  Avg Frame Delay: {traffic_sign_classify_stats['avg_frame_delay_ms']:.2f} ms")
            print(f"  Avg API Latency: {traffic_sign_classify_stats['avg_api_latency_ms']:.2f} ms")
            print(f"  Avg CPU Usage: {traffic_sign_classify_stats['avg_cpu_percent']:.1f}%")
            print(f"  Avg Memory: {traffic_sign_classify_stats['avg_memory_mb']:.1f} MB")

        except Exception as e:
            print(f"\n[X] Traffic Sign Classification Error: {e}")
            results["traffic_sign_classification"] = {"error": str(e)}

    # Print performance summary table
    print("\n" + "=" * 70)
    print("PERFORMANCE MEASUREMENT SUMMARY")
    print("=" * 70)
    print(f"{'Model':<35} {'Frame Delay (ms)':<18} {'API Latency (ms)':<18} {'CPU (%)':<12}")
    print("-" * 70)

    for model_key in ["road_damage_detection", "traffic_sign_detection", "traffic_sign_classification"]:
        if model_key in results and "statistics" in results[model_key]:
            stats = results[model_key]["statistics"]
            model_name = model_key.replace("_", " ").title()
            print(f"{model_name:<35} "
                  f"{stats['avg_frame_delay_ms']:<18.2f} "
                  f"{stats['avg_api_latency_ms']:<18.2f} "
                  f"{stats['avg_cpu_percent']:<12.1f}")

    print("=" * 70)

    # Save results to JSON
    results_file = BASE_DIR / "tests" / "performance_measurement_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    results_dict = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "configuration": {
            "num_frames": NUM_FRAMES,
            "inter_frame_delay": INTER_FRAME_DELAY,
            "timeout": TIMEOUT
        },
        "results": results
    }

    with open(results_file, 'w') as f:
        json.dump(results_dict, f, indent=2)

    print(f"\nResults saved to: {results_file}")
    print("=" * 70)

    return results_dict


def main():
    """Main entry point."""
    try:
        results = asyncio.run(run_performance_measurement())
        return results
    except KeyboardInterrupt:
        print("\n\n⚠ Measurement interrupted by user.")
        return None
    except Exception as e:
        print(f"\n\n[X] Fatal error: {e}")
        return None


if __name__ == "__main__":
    main()
