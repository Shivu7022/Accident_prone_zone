# Indian Traffic-Sign Locator

This is a one-class object detector for locating traffic-sign regions in Indian road scenes. It does not identify the sign's meaning or legal applicability. The existing ResNet18 checkpoint is trained on GTSRB and must not be treated as an Indian sign classifier.

## Academic Training

The training script uses the 150-image sample from [DataCluster Labs' Indian Traffic Sign Image Dataset](https://huggingface.co/datasets/Dataclusterlabspvtltd/Indian_Traffic_Sign_Image_Dataset). The sample terms allow academic research with attribution, prohibit commercial use, and prohibit dataset redistribution. Keep the downloaded data and derived checkpoint local; do not commit or distribute either.

Install `traffic_sign_api/requirements.txt`, then run:

```powershell
python traffic_sign_api/train_indian_detector.py
```

The script downloads the sample and creates its train/validation data under `~/.roadsafe_training` (or `ROADSAVE_TRAINING_HOME`). It uses a deterministic 80/20 image-level split and writes the detector to `traffic_sign_api/models/indian_traffic_sign_yolo11n.pt`. Validation scores are for this small sample only and are not evidence of road-safety readiness.

The detector reports only `traffic_sign` boxes. User-facing safety alerts must not infer sign type from this model; sign meaning requires a separately trained and validated Indian-sign classifier.