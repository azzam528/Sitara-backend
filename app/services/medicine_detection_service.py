from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


class MedicineDetectionService:

    def __init__(self):
        # Root project:
        # SitaraBackend/
        root_dir = Path(__file__).resolve().parents[2]

        model_path = root_dir / "ai" / "medicine_detection" / "best.pt"

        if not model_path.exists():
            raise FileNotFoundError(f"Medicine detection model not found: {model_path}")

        self.model = YOLO(str(model_path))

        # Confidence minimum.
        # Nanti bisa kita tuning setelah testing.
        self.confidence_threshold = 0.50

    def detect(self, image_bytes: bytes):

        # Convert uploaded image → numpy array
        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8,
        )

        # Decode image
        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise ValueError("Failed to decode image")

        # Run YOLO
        results = self.model.predict(
            source=image,
            conf=self.confidence_threshold,
            verbose=False,
        )

        detections = []

        result = results[0]

        if result.boxes is None:
            return detections

        for box in result.boxes:

            confidence = float(box.conf[0].item())

            class_id = int(box.cls[0].item())

            class_name = self.model.names[class_id]

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            detections.append(
                {
                    "medicine": class_name,
                    "confidence": confidence,
                    "bounding_box": {
                        "x": x1,
                        "y": y1,
                        "width": x2 - x1,
                        "height": y2 - y1,
                    },
                }
            )

        return detections

    def detect_expected_medicine(
        self,
        image_bytes: bytes,
        expected_medicine: str,
    ):
        detections = self.detect(image_bytes)

        if not detections:
            return {
                "status": "MEDICINE_NOT_DETECTED",
                "expected_medicine": expected_medicine,
                "detected_medicine": None,
                "confidence": 0.0,
                "bounding_box": None,
                "medicine_match": False,
                "message": "Obat belum terdeteksi.",
            }

        # Ambil detection dengan confidence tertinggi
        best_detection = max(
            detections,
            key=lambda detection: detection["confidence"],
        )

        detected_medicine = best_detection["medicine"]
        confidence = best_detection["confidence"]
        bounding_box = best_detection["bounding_box"]

        # Case-insensitive comparison
        medicine_match = (
            detected_medicine.strip().lower() == expected_medicine.strip().lower()
        )

        if medicine_match:
            status = "MEDICINE_MATCHED"
            message = "Obat sesuai dengan jadwal."
        else:
            status = "MEDICINE_MISMATCH"
            message = "Obat yang terdeteksi tidak sesuai " "dengan jadwal obat."

        return {
            "status": status,
            "expected_medicine": expected_medicine,
            "detected_medicine": detected_medicine,
            "confidence": confidence,
            "bounding_box": bounding_box,
            "medicine_match": medicine_match,
            "message": message,
        }


medicine_detection_service = MedicineDetectionService()
