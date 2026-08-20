import os
from pathlib import Path
from fastapi import HTTPException
import cv2
import numpy as np

from app.core.config import settings


class FaceRecognitionService:
    """
    Core Computer Vision Service for Face Detection and Embedding Extraction
    using OpenCV YuNet (Face Detection) and OpenCV SFace (Face Recognition 128-D).
    Model version: opencv_yunet_sface_v1
    """

    def __init__(self):
        # Base directory for ML model weights
        base_dir = Path(__file__).resolve().parent.parent / "ml_models" / "face"
        self.yunet_path = str(base_dir / "yunet_2023mar.onnx")
        self.sface_path = str(base_dir / "sface_2021dec.onnx")

        if not os.path.exists(self.yunet_path):
            raise RuntimeError(f"YuNet model artifact not found at {self.yunet_path}")
        if not os.path.exists(self.sface_path):
            raise RuntimeError(f"SFace model artifact not found at {self.sface_path}")

        # Initialize detector and recognizer
        self.detector = cv2.FaceDetectorYN.create(
            self.yunet_path,
            "",
            (320, 320),
            score_threshold=settings.FACE_DETECTION_THRESHOLD,
            nms_threshold=0.3,
            top_k=5000,
        )
        self.recognizer = cv2.FaceRecognizerSF.create(
            self.sface_path,
            "",
        )

    def decode_image(self, file_bytes: bytes) -> np.ndarray:
        """
        Decodes raw image bytes into a BGR OpenCV numpy image.
        Raises HTTPException 400 if bytes cannot be decoded as an image.
        """
        if not file_bytes or len(file_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="File gambar kosong.",
            )

        np_arr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(
                status_code=400,
                detail="Format berkas bukan gambar yang valid atau berkas rusak.",
            )

        return img

    def detect_single_face(self, img: np.ndarray) -> np.ndarray:
        """
        Runs YuNet face detection and enforces strict single-face validation.
        Validates:
        - Exactly 1 face must be present.
        - Face bounding box dimensions must meet minimum size quality threshold.
        """
        h, w = img.shape[:2]
        self.detector.setInputSize((w, h))

        _, faces = self.detector.detect(img)

        if faces is None or len(faces) == 0:
            raise HTTPException(
                status_code=400,
                detail="Tidak ada wajah yang terdeteksi pada foto. Pastikan wajah berada di dalam bingkai dan pencahayaan memadai.",
            )

        if len(faces) > 1:
            raise HTTPException(
                status_code=400,
                detail="Terdeteksi lebih dari satu wajah pada foto. Pastikan hanya ada satu orang di depan kamera.",
            )

        face = faces[0]
        face_w = float(face[2])
        face_h = float(face[3])

        if face_w < settings.FACE_MIN_SIZE or face_h < settings.FACE_MIN_SIZE:
            raise HTTPException(
                status_code=400,
                detail="Ukuran wajah terlalu kecil pada foto. Posisikan wajah lebih dekat ke kamera.",
            )

        return face

    def extract_embedding(self, img: np.ndarray, face: np.ndarray) -> list[float]:
        """
        Aligns the face crop and extracts a 128-dimensional L2-normalized float feature vector.
        """
        aligned_face = self.recognizer.alignCrop(img, face)
        feature_vector = self.recognizer.feature(aligned_face)  # shape (1, 128)
        
        flat_feature = feature_vector.flatten()
        return [float(val) for val in flat_feature]

    def calculate_similarity(self, emb1: list[float], emb2: list[float]) -> float:
        """
        Computes Cosine Similarity between two 128-D embedding vectors.
        Returns float score between -1.0 and 1.0.
        """
        v1 = np.array(emb1, dtype=np.float32)
        v2 = np.array(emb2, dtype=np.float32)

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        return float(np.dot(v1, v2) / (norm1 * norm2))
