import cv2

from app.services.face_recognition_service import FaceRecognitionService


class AIService:

    def __init__(self):
        self.face_recognition = FaceRecognitionService()

    def sample_video_frames(
        self,
        video_path: str,
        sample_fps: int = 5,
    ):
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Video tidak dapat dibuka: {video_path}")

        original_fps = cap.get(cv2.CAP_PROP_FPS)

        if not original_fps or original_fps <= 0:
            cap.release()
            raise ValueError("FPS video tidak valid.")

        frame_interval = max(
            int(original_fps / sample_fps),
            1,
        )

        frames = []
        frame_index = 0

        while True:
            success, frame = cap.read()

            if not success:
                break

            if frame_index % frame_interval == 0:
                frames.append(
                    {
                        "frame_index": frame_index,
                        "timestamp": frame_index / original_fps,
                        "image": frame,
                    }
                )

            frame_index += 1

        cap.release()

        return frames

    def verify_face_from_video(
        self,
        video_path: str,
        registered_embedding: list[float],
        sample_fps: int = 5,
        threshold: float = 0.70,
    ):
        frames = self.sample_video_frames(
            video_path=video_path,
            sample_fps=sample_fps,
        )

        results = []

        for frame_data in frames:
            frame = frame_data["image"]

            try:
                h, w = frame.shape[:2]

                self.face_recognition.detector.setInputSize((w, h))

                _, faces = self.face_recognition.detector.detect(frame)

                # Tidak ada wajah pada frame
                if faces is None or len(faces) == 0:
                    results.append(
                        {
                            "frame_index": frame_data["frame_index"],
                            "timestamp": frame_data["timestamp"],
                            "face_detected": False,
                            "similarity": 0.0,
                            "verified": False,
                            "reason": "no_face",
                        }
                    )
                    continue

                # Lebih dari satu wajah
                if len(faces) > 1:
                    results.append(
                        {
                            "frame_index": frame_data["frame_index"],
                            "timestamp": frame_data["timestamp"],
                            "face_detected": False,
                            "similarity": 0.0,
                            "verified": False,
                            "reason": "multiple_faces",
                        }
                    )
                    continue

                face = faces[0]

                # Extract embedding wajah dari frame
                embedding = self.face_recognition.extract_embedding(
                    frame,
                    face,
                )

                # Bandingkan dengan wajah yang tersimpan di DB
                similarity = self.face_recognition.calculate_similarity(
                    registered_embedding,
                    embedding,
                )

                results.append(
                    {
                        "frame_index": frame_data["frame_index"],
                        "timestamp": frame_data["timestamp"],
                        "face_detected": True,
                        "similarity": similarity,
                        "verified": similarity >= threshold,
                    }
                )

            except Exception as error:
                results.append(
                    {
                        "frame_index": frame_data["frame_index"],
                        "timestamp": frame_data["timestamp"],
                        "face_detected": False,
                        "similarity": 0.0,
                        "verified": False,
                        "reason": str(error),
                    }
                )

        if not results:
            return {
                "verified": False,
                "frames_processed": 0,
                "face_detected_frames": 0,
                "verified_frames": 0,
                "verification_rate": 0.0,
                "frames": [],
            }

        detected_frames = [result for result in results if result["face_detected"]]

        verified_frames = [result for result in results if result["verified"]]

        verification_rate = (
            len(verified_frames) / len(detected_frames) if detected_frames else 0.0
        )

        return {
            "verified": verification_rate >= 0.70,
            "frames_processed": len(results),
            "face_detected_frames": len(detected_frames),
            "verified_frames": len(verified_frames),
            "verification_rate": verification_rate,
            "frames": results,
        }
