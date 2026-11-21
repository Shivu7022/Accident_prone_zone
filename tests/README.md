# Testing Scripts

This directory contains automated testing scripts for evaluating the AI-powered detection models and system performance.

## Scripts

### 1. `evaluate_model_performance.py`
Evaluates model accuracy metrics (Precision, Recall, mAP@0.5) and inference speed.

**Usage:**
```bash
python evaluate_model_performance.py
```

**Requirements:**
- Test dataset with ground truth annotations (optional - will use placeholders if not available)
- Model files in respective directories

**Output:**
- Console output with metrics
- `model_performance_results.json`

---

### 2. `behavior_testing.py`
Tests 7 core system functions for pass/fail status.

**Usage:**
```bash
python behavior_testing.py
```

**Requirements:**
- All backend servers running (ports 8000, 8001, 8002)
- TOMTOM_API_KEY configured

**Output:**
- Console output with pass/fail status
- `behavior_test_results.json`

---

### 3. `performance_measurement.py`
Measures runtime performance metrics (frame delay, CPU usage, latency).

**Usage:**
```bash
python performance_measurement.py
```

**Requirements:**
- All backend servers running
- psutil package installed

**Output:**
- Console output with performance statistics
- `performance_measurement_results.json`

---

## Quick Start

### Install Dependencies
```bash
pip install ultralytics torch torchvision opencv-python numpy Pillow httpx psutil
```

### Start Backend Servers
```bash
# Terminal 1
cd ../backend
python main.py

# Terminal 2
cd ../traffic_sign_api
python app.py

# Terminal 3
cd ../backend/road_damage_api
python app.py
```

### Run Tests
```bash
# Run behavior tests
python behavior_testing.py

# Run performance measurement
python performance_measurement.py

# Run model performance evaluation (optional)
python evaluate_model_performance.py
```

---

## Detailed Documentation

See `../TESTING_RESULTS.md` for comprehensive documentation including:
- Detailed explanation of each test
- Expected performance targets
- Troubleshooting guide
- Results tables (Table VI, Table VII)
