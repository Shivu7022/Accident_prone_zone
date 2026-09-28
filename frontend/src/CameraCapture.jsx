import { useCallback, useEffect, useRef, useState } from "react";
import "./CameraCapture.css";

const API_URL = "http://127.0.0.1:8001/api/roaddamage/predict";
const TRAFFIC_SIGN_API_URL = "http://127.0.0.1:8001/api/signboard/detect";

export default function CameraCapture({ tripStatus, onRoadDamageDetection, onTrafficSignDetection }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const detectionIntervalRef = useRef(null);
  const detectionInProgressRef = useRef(false);
  const cameraRequestedRef = useRef(false);
  const onRoadDamageDetectionRef = useRef(onRoadDamageDetection);
  const onTrafficSignDetectionRef = useRef(onTrafficSignDetection);

  const [cameraActive, setCameraActive] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [resultImage, setResultImage] = useState(null);
  const [detections, setDetections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const autoMode = tripStatus === "in_progress" && cameraActive;
  const [autoResult, setAutoResult] = useState("");
  const [trafficSignCandidate, setTrafficSignCandidate] = useState(null);

  useEffect(() => {
    onRoadDamageDetectionRef.current = onRoadDamageDetection;
    onTrafficSignDetectionRef.current = onTrafficSignDetection;
  }, [onRoadDamageDetection, onTrafficSignDetection]);

  // Open camera
  const startCamera = useCallback(async () => {
    setError("");
    setMessage("");

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(
          "Camera access is unavailable. Open the application on localhost or HTTPS."
        );
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setCameraActive(true);
    } catch (err) {
      setError(
        err.message ||
          "Unable to access the camera. Please check camera permissions."
      );
    }
  }, []);

  // Stop camera
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraActive(false);
  };

  // Capture image from camera
  const captureImage = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas || !video.videoWidth) {
      setError("Camera is not ready. Please try again.");
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext("2d");

    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageData = canvas.toDataURL("image/jpeg", 0.92);

    setCapturedImage(imageData);
    setResultImage(null);
    setDetections([]);
    setError("");
    setMessage("Image captured successfully.");
  };

  // Convert data URL to Blob
  const dataURLToBlob = async (dataURL) => {
    const response = await fetch(dataURL);
    return response.blob();
  };

  // Send captured image to road damage API
  const detectRoadDamage = async () => {
    if (!capturedImage) {
      setError("Please capture an image first.");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const blob = await dataURLToBlob(capturedImage);

      const formData = new FormData();

      formData.append("file", blob, "road_capture.jpg");

      const response = await fetch(API_URL, {
        method: "POST",
        body: formData,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.detail || data.message || "Road damage detection failed."
        );
      }

      setDetections(data.detections || []);

      if (data.annotated_image) {
        const imageData = data.annotated_image;

        setResultImage(
          imageData.startsWith("data:")
            ? imageData
            : `data:image/jpeg;base64,${imageData}`
        );
      } else {
        setResultImage(null);
      }

      setMessage(
        `Detection completed. ${
          data.total_detections ?? data.detections?.length ?? 0
        } damage objects detected.`
      );
    } catch (err) {
      setError(
        err.message ||
          "Unable to connect to the Road Damage API. Check that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  // Reset captured image and results
  const resetCapture = () => {
    setCapturedImage(null);
    setResultImage(null);
    setDetections([]);
    setError("");
    setMessage("");
  };

  // Stop camera when component unmounts
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
      }
    };
  }, []);

  // Auto-start camera when trip starts
  useEffect(() => {
    if (
      tripStatus === "in_progress" &&
      !cameraActive &&
      !cameraRequestedRef.current
    ) {
      cameraRequestedRef.current = true;
      startCamera();
    } else if (tripStatus !== "in_progress" && cameraRequestedRef.current) {
      cameraRequestedRef.current = false;
      stopCamera();
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
        detectionIntervalRef.current = null;
      }
    }
  }, [tripStatus, cameraActive, startCamera]);

  // Automatic detection during trip
  const performAutoDetection = useCallback(async () => {
    if (detectionInProgressRef.current || !videoRef.current || !videoRef.current.videoWidth) {
      return;
    }
    detectionInProgressRef.current = true;

    const canvas = canvasRef.current;
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;

    const context = canvas.getContext("2d");
    context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);

    const imageData = canvas.toDataURL("image/jpeg", 0.85);

    try {
      const blob = await dataURLToBlob(imageData);
      const requestPrediction = async (url) => {
        const formData = new FormData();
        formData.append("file", blob, "auto_capture.jpg");
        const response = await fetch(url, { method: "POST", body: formData });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.detail || data.message || `Request failed (${response.status})`);
        }
        return data;
      };

      const [roadResult, signResult] = await Promise.allSettled([
        requestPrediction(API_URL),
        requestPrediction(TRAFFIC_SIGN_API_URL),
      ]);
      const summaries = [];

      if (roadResult.status === "fulfilled") {
        const roadDamageData = roadResult.value;
        const roadDetections = roadDamageData.detections || [];
        setDetections(roadDetections);
        if (roadDamageData.annotated_image) {
          setResultImage(
            roadDamageData.annotated_image.startsWith("data:")
              ? roadDamageData.annotated_image
              : `data:image/jpeg;base64,${roadDamageData.annotated_image}`
          );
        }
        roadDetections.forEach((detection) => {
          onRoadDamageDetectionRef.current?.(detection);
        });
        summaries.push(`${roadDetections.length} road damage object${roadDetections.length === 1 ? "" : "s"}`);
      } else {
        setDetections([]);
        setResultImage(null);
        summaries.push(`Road damage model unavailable: ${roadResult.reason.message}`);
      }

      if (signResult.status === "fulfilled") {
        const signData = signResult.value;
        const signDetections = signData.detections || [];
        const hasCandidate = signDetections.length > 0;
        setTrafficSignCandidate(
          hasCandidate
            ? { detections: signDetections, annotatedImage: signData.annotated_image }
            : null
        );
        summaries.push(`${signDetections.length} unclassified traffic sign region${signDetections.length === 1 ? "" : "s"} located`);
      } else {
        setTrafficSignCandidate(null);
        summaries.push(`Traffic sign model unavailable: ${signResult.reason.message}`);
      }

      setAutoResult(`Last AI check ${new Date().toLocaleTimeString()} · ${summaries.join(" · ")}`);
    } catch (err) {
      console.error("Auto-detection error:", err);
      setAutoResult(`Camera inference could not run: ${err.message}`);
    } finally {
      detectionInProgressRef.current = false;
    }
  }, []);

  const confirmTrafficSign = () => {
    if (!trafficSignCandidate) return;
    trafficSignCandidate.detections.forEach((detection) => {
      onTrafficSignDetectionRef.current?.({
        ...detection,
        sign_name: "Traffic sign region (unclassified)",
        confirmedByUser: true,
        timestamp: new Date(),
      });
    });
    setMessage(
      `Added ${trafficSignCandidate.detections.length} user-confirmed sign region${trafficSignCandidate.detections.length === 1 ? "" : "s"}.`
    );
    setTrafficSignCandidate(null);
  };

  // Periodic detection during trip
  useEffect(() => {
    if (cameraActive && autoMode && tripStatus === "in_progress") {
      performAutoDetection();
      detectionIntervalRef.current = setInterval(() => {
        performAutoDetection();
      }, 10000);
    }

    return () => {
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
      }
    };
  }, [cameraActive, autoMode, tripStatus, performAutoDetection]);

  return (
    <section className="camera-damage-card">
      <div className="camera-damage-header">
        <div>
          <h2>📷 Road Damage Scanner</h2>
          <p>
            {autoMode
              ? "Automatic monitoring during trip"
              : "Capture a road image and detect damage using AI."}
          </p>
        </div>

        <span className="camera-ai-badge">YOLO11s + YOLO11n</span>
        {autoMode && <span className="camera-auto-badge">Auto Mode</span>}
      </div>

      {/* Camera Preview */}
      <div className="camera-preview">
        {cameraActive ? (
          <video
            ref={videoRef}
            className="camera-video"
            autoPlay
            muted
            playsInline
          />
        ) : capturedImage ? (
          <img
            src={capturedImage}
            alt="Captured road"
            className="camera-video"
          />
        ) : (
          <div className="camera-placeholder">
            <span>📷</span>
            <p>Camera is not active</p>
            <small>Start the camera to capture a road image.</small>
          </div>
        )}
      </div>

      <canvas ref={canvasRef} style={{ display: "none" }} />

      {/* Camera Controls */}
      <div className="camera-controls">
        {!autoMode && !cameraActive ? (
          <button
            type="button"
            className="camera-btn camera-start-btn"
            onClick={startCamera}
          >
            📷 Start Camera
          </button>
        ) : !autoMode && cameraActive ? (
          <>
            <button
              type="button"
              className="camera-btn camera-capture-btn"
              onClick={captureImage}
            >
              📸 Capture Image
            </button>

            <button
              type="button"
              className="camera-btn camera-stop-btn"
              onClick={stopCamera}
            >
              ⏹ Stop Camera
            </button>
          </>
        ) : (
          <div className="camera-auto-status">
            <span className="auto-indicator" />
            <span>Monitoring road conditions...</span>
          </div>
        )}
      </div>

      {/* Captured Image Controls */}
      {capturedImage && (
        <div className="camera-controls">
          <button
            type="button"
            className="camera-btn camera-detect-btn"
            onClick={detectRoadDamage}
            disabled={loading}
          >
            {loading ? "🔄 Detecting Damage..." : "🔍 Detect Road Damage"}
          </button>

          <button
            type="button"
            className="camera-btn camera-reset-btn"
            onClick={resetCapture}
            disabled={loading}
          >
            🔄 Retake Image
          </button>
        </div>
      )}

      {/* Status Messages */}
      {message && <div className="camera-success">{message}</div>}

      {error && <div className="camera-error">{error}</div>}

      {autoMode && (
        <div className="camera-live-result" role="status" aria-live="polite">
          {autoResult || "Camera ready. Running the first model check..."}
        </div>
      )}

      {autoMode && trafficSignCandidate && (
        <div className="traffic-sign-candidate">
          <div>
            <strong>
              {trafficSignCandidate.detections.length} sign region{trafficSignCandidate.detections.length === 1 ? "" : "s"} located
            </strong>
            <small>
              This detector locates sign-shaped regions but does not identify their meaning. Validation used a small academic sample; visually verify before logging.
            </small>
            {trafficSignCandidate.detections.map((detection, index) => (
              <span key={`${detection.bounding_box?.x1}-${index}`}>
                Region {index + 1}: {Number(detection.confidence).toFixed(1)}% confidence
              </span>
            ))}
            {trafficSignCandidate.annotatedImage && (
              <img
                src={trafficSignCandidate.annotatedImage}
                alt="Traffic sign regions outlined by the detector"
                className="traffic-sign-candidate-image"
              />
            )}
          </div>
          <button type="button" onClick={confirmTrafficSign}>
            Confirm sign regions
          </button>
        </div>
      )}

      {/* Detection Results */}
      {resultImage && (
        <div className="damage-result">
          <h3>AI Detection Result</h3>

          <img
            src={resultImage}
            alt="Road damage detection result"
            className="damage-result-image"
          />
        </div>
      )}

      {/* Detection List */}
      {detections.length > 0 && (
        <div className="damage-detection-list">
          <h3>Detected Road Damage</h3>

          <div className="damage-detection-summary">
            Total detections: <strong>{detections.length}</strong>
          </div>

          {detections.map((item, index) => (
            <div className="damage-detection-item" key={index}>
              <div>
                <strong>
                  {item.class_name || item.class || "Road Damage"}
                </strong>

                {item.bounding_box && (
                  <small>
                    Bounding box: {JSON.stringify(item.bounding_box)}
                  </small>
                )}
              </div>

              <span className="damage-confidence">
                {typeof item.confidence === "number"
                  ? `${(item.confidence > 1 ? item.confidence : item.confidence * 100).toFixed(1)}%`
                  : item.confidence ?? "N/A"}
              </span>
            </div>
          ))}
        </div>
      )}

      {!loading && detections.length === 0 && resultImage && (
        <div className="camera-no-damage">
          No road damage objects were detected in this image.
        </div>
      )}
    </section>
  );
}