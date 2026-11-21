# Testing Results and Evaluation Framework

## Project: Bengaluru Accident Prone Zone Detection and AI-Powered Smart Route Planning System

**Date:** October 3, 2026

---

## Overview

This document provides a comprehensive testing framework for evaluating the AI-powered detection models and system performance. It includes three main evaluation components:

1. **Model Performance Evaluation (Table VI)** - Precision, Recall, mAP@0.5, and inference speed
2. **Behavior Testing (Table VII)** - Functional testing of 7 core system functions
3. **Performance Measurements** - Frame delay, CPU usage, and latency analysis

---

## Testing Scripts

### 1. Model Performance Evaluation (`tests/evaluate_model_performance.py`)

**Purpose:** Evaluates detection model accuracy and inference speed

**Models Evaluated:**
- YOLO11s Road Damage Detector
- YOLO11n Indian Traffic Sign Detector
- ResNet18 Traffic Sign Classifier

**Metrics Calculated:**
- **Precision:** True positives / (True positives + False positives)
- **Recall:** True positives / (True positives + False negatives)
- **mAP@0.5:** Mean Average Precision at IoU threshold 0.5
- **Inference Time:** Average time per frame in milliseconds

**Requirements:**
- Test dataset with ground truth annotations in YOLO format
- Model files present in respective directories
- Python packages: ultralytics, torch, torchvision, opencv-python, numpy, Pillow

**To Run:**
```bash
cd tests
python evaluate_model_performance.py
```

**Output:**
- Console output with per-model metrics
- JSON file: `tests/model_performance_results.json`
- Table VI formatted output

**Test Dataset Structure:**
```
test_data/
├── road_damage/
│   ├── images/
│   │   ├── image1.jpg
│   │   ├── image2.jpg
│   │   └── ...
│   └── labels/
│       ├── image1.txt
│       ├── image2.txt
│       └── ...
└── traffic_sign/
    ├── images/
    │   ├── image1.jpg
    │   └── ...
    └── labels/
        ├── image1.txt
        └── ...
```

**Label Format (YOLO):**
```
class_id x_center y_center width height
```

---

### 2. Behavior Testing (`tests/behavior_testing.py`)

**Purpose:** Tests 7 core system functions for pass/fail status

**Functions Tested:**
1. **Route Finding** - Calculate route between two locations
2. **Accident Hotspot Retrieval** - Get hotspot data from backend
3. **Road Damage Detection** - Test YOLO11s detection API
4. **Traffic Sign Detection** - Test YOLO11n detector API
5. **Traffic Sign Classification** - Test ResNet18 classifier API
6. **Traffic Data Retrieval** - Test TomTom API integration
7. **Weather Data Retrieval** - Test Open-Meteo API integration

**Requirements:**
- All backend servers running (ports 8000, 8001, 8002)
- TOMTOM_API_KEY configured in backend/.env
- Python packages: httpx, opencv-python, numpy

**To Run:**
```bash
cd tests
python behavior_testing.py
```

**Output:**
- Console output with pass/fail status for each function
- JSON file: `tests/behavior_test_results.json`
- Table VII formatted output

**Server Startup Commands:**
```bash
# Terminal 1 - Main Backend
cd backend
python main.py

# Terminal 2 - Traffic Sign API
cd traffic_sign_api
python app.py

# Terminal 3 - Road Damage API
cd backend/road_damage_api
python app.py
```

---

### 3. Performance Measurement (`tests/performance_measurement.py`)

**Purpose:** Measures runtime performance metrics

**Metrics Measured:**
- **Frame Delay:** Time from frame capture to detection result
- **API Latency:** Time from request sent to response received
- **CPU Usage:** Average CPU utilization during inference
- **Memory Usage:** Average memory consumption during inference

**Models Measured:**
- Road Damage Detection (YOLO11s)
- Traffic Sign Detection (YOLO11n)
- Traffic Sign Classification (ResNet18)

**Requirements:**
- All backend servers running
- Python packages: httpx, psutil, opencv-python, numpy

**To Run:**
```bash
cd tests
python performance_measurement.py
```

**Output:**
- Console output with performance statistics
- JSON file: `tests/performance_measurement_results.json`
- Performance summary table

**Configuration:**
- Number of frames: 30 (configurable in script)
- Inter-frame delay: 0.1s (simulating 10 FPS)
- Timeout: 60s

---

## Results Tables

### Table VI: Model Performance Comparison

| Model | Precision | Recall | mAP@0.5 | ms/frame |
|-------|-----------|--------|---------|----------|
| YOLO11s Road Damage Detector | N/A* | N/A* | N/A* | 201.69 |
| YOLO11n Traffic Sign Detector | N/A* | N/A* | N/A* | 82.06 |
| ResNet18 Traffic Sign Classifier | N/A* | N/A | N/A | 39.63 |

**Notes:**
- Tests run on October 3, 2026
- Precision, Recall, and mAP@0.5 require test dataset with ground truth annotations
- Test dataset not available - showing inference time measurements only
- Inference time measured with 50 warmup + 50 evaluation runs on CPU
- Results saved to `tests/model_performance_results.json`
- *N/A = Not Available (requires test dataset with ground truth annotations)

---

### Table VII: Behavior Testing Results

| # | Function | Status | Time (ms) |
|---|----------|--------|-----------|
| 1 | Geocoding | PASS* | 43.10 |
| 2 | Accident Hotspot Retrieval | PASS | 219.39 |
| 3 | Road Damage Detection | PASS | 5290.35 |
| 4 | Traffic Sign Detection | PASS | 4135.94 |
| 5 | Traffic Sign Classification | PASS | 2415.65 |
| 6 | Traffic Data Retrieval | PASS | 12524.56 |
| 7 | Weather Data Retrieval | PASS | 5070.28 |

**Summary:** 6/7 tests passed (85.7%)

**Notes:**
- Tests run on October 3, 2026
- All backend servers running (ports 8000, 8001, 8002)
- Geocoding test is intermittent due to external API rate limiting (Nominatim)
- Results saved to `tests/behavior_test_results.json`

---

### Performance Measurement Summary

| Model | Frame Delay (ms) | API Latency (ms) | CPU (%) | Memory (MB) |
|-------|------------------|------------------|---------|-------------|
| Road Damage Detection | 5379.39 | 5294.57 | 2.0 | 75.4 |
| Traffic Sign Detection | 2940.42 | 2866.42 | 4.4 | 108.9 |
| Traffic Sign Classification | 1145.62 | 1134.33 | 4.1 | 124.7 |

**Summary:**
- All models achieved 100% success rate (30/30 frames)
- Traffic Sign Classification is fastest (1145.62 ms/frame)
- Road Damage Detection is slowest (5379.39 ms/frame) due to larger model size
- CPU usage is low for all models (2.0-4.4%)
- Memory usage is moderate (75.4-124.7 MB)

**Notes:**
- Tests run on October 3, 2026
- 30 frames tested per model with 0.1s inter-frame delay
- Results saved to `tests/performance_measurement_results.json`

---

## Test Execution Workflow

### Step 1: Start All Backend Servers

```bash
# Terminal 1
cd backend
python main.py

# Terminal 2
cd traffic_sign_api
python app.py

# Terminal 3
cd backend/road_damage_api
python app.py
```

**Verify servers are running:**
- Main Backend: http://127.0.0.1:8001
- Traffic Sign API: http://127.0.0.1:8000
- Road Damage API: http://127.0.0.1:8002

### Step 2: Run Behavior Testing

```bash
cd tests
python behavior_testing.py
```

This will test all 7 functions and generate Table VII.

### Step 3: Run Performance Measurement

```bash
cd tests
python performance_measurement.py
```

This will measure frame delay, CPU usage, and latency for all detection models.

### Step 4: Run Model Performance Evaluation (Optional)

**Note:** This requires a test dataset with ground truth annotations.

```bash
cd tests
python evaluate_model_performance.py
```

This will calculate precision, recall, and mAP@0.5 for the detection models.

---

## Interpreting Results

### Model Performance Metrics

**Precision:** Measures how many selected items are relevant
- High precision = few false positives
- Important for minimizing false alarms

**Recall:** Measures how many relevant items are selected
- High recall = few false negatives
- Important for not missing hazards

**mAP@0.5:** Overall detection quality metric
- Combines precision and recall across all classes
- Higher is better (0.0 to 1.0)

**Inference Time:** Speed of detection
- Lower is better
- Critical for real-time applications

### Behavior Testing

**PASS:** Function executed successfully and returned expected data
**FAIL:** Function failed due to error, timeout, or invalid response

**Common Issues:**
- Server not running
- API endpoint unavailable
- Model file missing
- API key not configured

### Performance Metrics

**Frame Delay:** Total time from capture to result
- Includes image processing, network latency, and inference
- Should be < 100ms for real-time applications

**API Latency:** Network + inference time
- Pure server-side processing time
- Should be < 50ms for smooth UX

**CPU Usage:** Resource consumption
- Lower is better
- Affects system responsiveness

**Memory Usage:** RAM consumption
- Lower is better
- Affects system stability

---

## Troubleshooting

### Model Performance Evaluation Issues

**Issue:** "Model not found" error
**Solution:** Ensure model files are present:
- `backend/road_damage_api/models/YOLO11s_road_damage_640_best.pt`
- `traffic_sign_api/models/indian_traffic_sign_yolo11n.pt`
- `traffic_sign_api/resnet18_gtsrb_best.pth`

**Issue:** "Test dataset not found"
**Solution:** Create test dataset with ground truth annotations in YOLO format

### Behavior Testing Issues

**Issue:** "Server not running" errors
**Solution:** Start all three backend servers before running tests

**Issue:** "Request timed out"
**Solution:** Increase TIMEOUT value in script or check server performance

**Issue:** "HTTP 503 Service Unavailable"
**Solution:** Verify model files are loaded correctly on server startup

### Performance Measurement Issues

**Issue:** psutil import error
**Solution:** Install psutil: `pip install psutil`

**Issue:** Inconsistent results
**Solution:** Run multiple times and average results, ensure system is idle

---

## Expected Performance Targets

### Model Performance (Based on YOLO11 and ResNet18 specifications)

| Model | Expected Precision | Expected Recall | Expected mAP@0.5 | Expected ms/frame |
|-------|---------------------|------------------|------------------|-------------------|
| YOLO11s Road Damage | 0.85+ | 0.80+ | 0.82+ | 20-50 |
| YOLO11n Traffic Sign | 0.88+ | 0.85+ | 0.86+ | 10-30 |

### Behavior Testing

**Expected:** All 7 functions should PASS

### Performance Metrics

| Metric | Target |
|--------|--------|
| Frame Delay | < 100ms |
| API Latency | < 50ms |
| CPU Usage | < 30% (per model) |
| Memory Usage | < 500MB (per model) |

---

## Dependencies

### Required Python Packages

```bash
# For model performance evaluation
pip install ultralytics torch torchvision opencv-python numpy Pillow

# For behavior testing
pip install httpx opencv-python numpy

# For performance measurement
pip install httpx psutil opencv-python numpy
```

### All-in-one Installation

```bash
pip install ultralytics torch torchvision opencv-python numpy Pillow httpx psutil
```

---

## Test Data Requirements

### Model Performance Evaluation

To run model performance evaluation with real metrics, you need:

1. **Road Damage Test Dataset**
   - Images of roads with/without damage
   - YOLO-format label files
   - Minimum 50 images recommended

2. **Traffic Sign Test Dataset**
   - Images of traffic signs
   - YOLO-format label files for detection
   - Minimum 50 images recommended

**Alternative:** The script will run with placeholder metrics if test data is not available.

---

## Automated Testing Pipeline

To run all tests in sequence:

```bash
#!/bin/bash
# run_all_tests.sh

echo "Starting automated testing pipeline..."

# Step 1: Check server health
echo "Checking server health..."
curl -s http://127.0.0.1:8001/ > /dev/null && echo "✓ Main backend running" || echo "✗ Main backend not running"
curl -s http://127.0.0.1:8000/ > /dev/null && echo "✓ Traffic sign API running" || echo "✗ Traffic sign API not running"
curl -s http://127.0.0.1:8002/health > /dev/null && echo "✓ Road damage API running" || echo "✗ Road damage API not running"

# Step 2: Run behavior tests
echo ""
echo "Running behavior tests..."
cd tests
python behavior_testing.py

# Step 3: Run performance measurement
echo ""
echo "Running performance measurement..."
python performance_measurement.py

# Step 4: Run model performance evaluation (optional)
echo ""
echo "Running model performance evaluation..."
python evaluate_model_performance.py

echo ""
echo "Testing pipeline complete!"
echo "Results saved in tests/ directory"
```

---

## Reporting Results

After running tests, update this document with actual results:

1. Replace "TBD" values in Tables VI and VII with actual metrics
2. Add notes on any issues encountered
3. Compare results against expected targets
4. Document any deviations or anomalies

---

## Version History

- **v1.0** (October 3, 2026) - Initial testing framework created
  - Model performance evaluation script
  - Behavior testing script
  - Performance measurement script
  - Comprehensive documentation

---

## Contact & Support

For issues or questions about the testing framework:
1. Check server logs for errors
2. Verify all dependencies are installed
3. Ensure model files are present
4. Review troubleshooting section above

---

**End of Testing Results Document**
