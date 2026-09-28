import base64
from pathlib import Path

import cv2
import numpy as np

from ultralytics import YOLO

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Road Damage Detection API",
    description="YOLO11-based road damage detection",
    version="1.0.0",
)


# ============================================================
# MODEL CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "YOLO11s_road_damage_640_best.pt"
)

model = YOLO(str(MODEL_PATH)) if MODEL_PATH.exists() else None


# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HOME ENDPOINT
# ============================================================

@app.get("/")
def home():
    return {
        "message": "Road Damage Detection API is running",
        "model_loaded": model is not None,
        "model": MODEL_PATH.name if model is not None else None,
        "endpoints": [
            "/health",
            "/predict",
        ],
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "running",
        "model_loaded": model is not None,
        "model_name": MODEL_PATH.name if model is not None else None,
    }


# ============================================================
# ROAD DAMAGE DETECTION
# ============================================================

@app.post("/predict")
async def predict_road_damage(
    file: UploadFile = File(...)
):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Road-damage model weights are not installed.",
        )

    # --------------------------------------------------------
    # VALIDATE FILE TYPE
    # --------------------------------------------------------

    if (
        not file.content_type
        or not file.content_type.startswith("image/")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid image.",
        )

    # --------------------------------------------------------
    # READ IMAGE
    # --------------------------------------------------------

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty.",
        )

    # --------------------------------------------------------
    # DECODE IMAGE
    # --------------------------------------------------------

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8,
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to decode the uploaded image.",
        )

    # --------------------------------------------------------
    # RUN YOLO11 MODEL
    # --------------------------------------------------------

    try:

        results = model.predict(
            source=image,
            conf=0.25,
            imgsz=640,
            verbose=False,
        )

        result = results[0]

        detections = []

        # ----------------------------------------------------
        # EXTRACT DETECTIONS
        # ----------------------------------------------------

        if result.boxes is not None:

            for box in result.boxes:

                class_id = int(
                    box.cls[0].item()
                )

                confidence = float(
                    box.conf[0].item()
                )

                x1, y1, x2, y2 = (
                    box.xyxy[0].cpu().tolist()
                )

                class_name = model.names.get(
                    class_id,
                    str(class_id),
                )

                detections.append(
                    {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": round(
                            confidence * 100,
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

        # ----------------------------------------------------
        # GENERATE ANNOTATED IMAGE
        # ----------------------------------------------------

        annotated_image = result.plot()

        success, buffer = cv2.imencode(
            ".jpg",
            annotated_image,
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Could not encode annotated image.",
            )

        # ----------------------------------------------------
        # CONVERT IMAGE TO BASE64
        # ----------------------------------------------------

        image_base64 = base64.b64encode(
            buffer.tobytes()
        ).decode("utf-8")

        # ----------------------------------------------------
        # RETURN RESPONSE
        # ----------------------------------------------------

        return {
            "filename": file.filename,
            "total_detections": len(detections),
            "detections": detections,
            "annotated_image": (
                "data:image/jpeg;base64,"
                + image_base64
            ),
        }

    # --------------------------------------------------------
    # ERROR HANDLING
    # --------------------------------------------------------

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Road damage prediction failed: "
                + str(error)
            ),
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)