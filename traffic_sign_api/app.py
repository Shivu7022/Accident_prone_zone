
import base64
import os
import json
import io
from pathlib import Path

import cv2
import torch
import torch.nn as nn

from PIL import Image
from torchvision import models, transforms
from fastapi import FastAPI, UploadFile, File, HTTPException
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "resnet18_gtsrb_best.pth")
CLASS_PATH = os.path.join(BASE_DIR, "class_names.json")
DETECTOR_PATH = Path(BASE_DIR) / "models" / "indian_traffic_sign_yolo11n.pt"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

with open(CLASS_PATH, "r") as f:
    raw_classes = json.load(f)

if isinstance(raw_classes, dict):
    class_names = {int(k): v for k, v in raw_classes.items()}
else:
    class_names = {i: v for i, v in enumerate(raw_classes)}

model = None
if os.path.exists(MODEL_PATH):
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 43)
    checkpoint = torch.load(
        MODEL_PATH,
        map_location=device,
        weights_only=False,
    )

    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        model.load_state_dict(checkpoint)

    model.to(device)
    model.eval()
detector = YOLO(str(DETECTOR_PATH)) if DETECTOR_PATH.exists() else None

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

app = FastAPI(
    title="Traffic Sign Recognition API",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Traffic Sign Recognition API is running",
        "device": str(device),
        "classifier_loaded": model is not None,
        "detector_loaded": detector is not None,
        "detector_name": DETECTOR_PATH.name if detector is not None else None,
    }


@app.post("/api/signboard/detect/")
async def detect_sign_regions(file: UploadFile = File(...)):
    if detector is None:
        raise HTTPException(
            status_code=503,
            detail="The Indian traffic-sign detector is not installed.",
        )

    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=400,
            detail="Upload a JPEG, PNG, or WEBP image.",
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image must be smaller than 10 MB.",
        )

    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file.",
        ) from error

    try:
        result = detector.predict(
            source=image,
            conf=0.25,
            imgsz=640,
            device="cpu",
            verbose=False,
        )[0]

        detections = []
        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                x1, y1, x2, y2 = box.xyxy[0].cpu().tolist()
                detections.append(
                    {
                        "class_id": class_id,
                        "class_name": detector.names.get(
                            class_id,
                            "traffic_sign",
                        ),
                        "confidence": round(
                            float(box.conf[0].item()) * 100,
                            2,
                        ),
                        "bounding_box": {
                            "x1": round(x1, 2),
                            "y1": round(y1, 2),
                            "x2": round(x2, 2),
                            "y2": round(y2, 2),
                        },
                    }
                )

        success, buffer = cv2.imencode(".jpg", result.plot())
        if not success:
            raise RuntimeError("Could not encode the annotated image.")

        return {
            "model": DETECTOR_PATH.name,
            "class_scope": "traffic_sign_region_only",
            "total_detections": len(detections),
            "detections": detections,
            "annotated_image": "data:image/jpeg;base64,"
            + base64.b64encode(buffer.tobytes()).decode("ascii"),
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Traffic-sign detection failed: {error}",
        ) from error


@app.post("/api/signboard/predict/")
async def predict_sign(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="GTSRB classifier weights are not installed.",
        )

    if file.content_type not in [
        "image/jpeg", "image/png", "image/webp"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Upload a JPEG, PNG, or WEBP image."
        )

    contents = await file.read()

    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image must be smaller than 10 MB."
        )

    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file."
        )

    image_tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(image_tensor)
        probabilities = torch.softmax(outputs, dim=1)
        confidence, predicted = torch.max(probabilities, dim=1)

    class_id = int(predicted.item())

    return {
        "class_id": class_id,
        "sign_name": class_names[class_id],
        "confidence": round(float(confidence.item()) * 100, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
