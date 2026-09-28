# RoadSafe Navigator

A map-first Bengaluru road-safety and trip-monitoring project built around OpenStreetMap, Leaflet, OSRM routing, device GPS, and local AI inference services.

## What It Does

- Searches locations and requests real driving-route alternatives from OSRM.
- Tracks the device GPS position during a trip, shows route progress, and flags separation from the selected route.
- Displays Bengaluru road-network context and historical police-station accident hotspots. Hotspots are regional context, not exact crash locations or route-risk scores.
- Loads traffic and weather only after a real start point or device location is available. It does not substitute the default map center for the user's location.
- Runs road-damage detection and traffic-sign-region detection from camera frames during an active trip. Sign regions are not classified by meaning and require visual confirmation.

## Run Locally

Requirements: Python 3.10+ and Node.js 20+.

Install the frontend dependencies:

```powershell
cd frontend
npm install
```

Install the API dependencies in a Python environment:

```powershell
cd ..
pip install -r backend/requirements.txt
pip install -r backend/road_damage_api/requirements.txt
pip install -r traffic_sign_api/requirements.txt
```

Run these services in separate terminals:

```powershell
cd backend
python main.py
```

```powershell
cd backend/road_damage_api
python app.py
```

```powershell
cd traffic_sign_api
python app.py
```

```powershell
cd frontend
npm run dev
```

Open the Vite URL printed by the frontend. Location-based services require a selected start point or browser location permission. Camera inference requires camera permission and the corresponding model files.

## Model Files

Model binaries are deliberately excluded from this repository. The APIs still start without them, report model readiness through their health endpoints, and return HTTP 503 for inference routes whose weights are missing.

Install only weights you are licensed to use at these paths:

- `backend/road_damage_api/models/YOLO11s_road_damage_640_best.pt`
- `traffic_sign_api/resnet18_gtsrb_best.pth` for the legacy GTSRB classification endpoint
- `traffic_sign_api/models/indian_traffic_sign_yolo11n.pt` for the live sign-region detector

The included `traffic_sign_api/train_indian_detector.py` uses a small academic sample whose terms prohibit commercial use and redistribution. Its trained checkpoint must remain local and must not be committed. Its single class locates sign regions only; it does not read sign meanings. The live camera path uses this detector, not the legacy GTSRB classifier.

## Important Limits

- Route alternatives are driving routes, not scored for accident risk.
- Accident records are associated with police-station locations, not exact accident coordinates.
- GPS, traffic, weather, camera, and inference availability depend on the user's device, network, permissions, and installed models.
- This project is an academic prototype, not a certified navigation or driver-safety system. Follow road signs and traffic laws.
