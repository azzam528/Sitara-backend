import cv2

from app.core.database import SessionLocal
from app.repositories.face_repository import FaceRepository
from app.services.face_recognition_service import FaceRecognitionService


PATIENT_ID = 1
THRESHOLD = 0.70
CAMERA_INDEX = 0


def main():
    db = SessionLocal()

    try:
        # ==============================
        # 1. Ambil wajah terdaftar dari DB
        # ==============================
        repository = FaceRepository()

        face_record = repository.get_active_embedding_by_patient_id(
            db=db,
            patient_id=PATIENT_ID,
        )

        if face_record is None:
            raise RuntimeError(
                f"Face embedding aktif untuk patient_id={PATIENT_ID} "
                "tidak ditemukan."
            )

        print("Face embedding ditemukan:")
        print(f"  ID            : {face_record.id}")
        print(f"  Patient ID    : {face_record.patient_id}")
        print(f"  Model version : {face_record.model_version}")
        print(f"  Embedding dim : {len(face_record.embedding)}")

        # ==============================
        # 2. Siapkan Face Recognition
        # ==============================
        face_service = FaceRecognitionService()

        # Embedding di DB disimpan sebagai string.
        # Kalau formatnya JSON, ubah menjadi list float.
        import json

        registered_embedding = json.loads(face_record.embedding)

        # ==============================
        # 3. Buka kamera
        # ==============================
        cap = cv2.VideoCapture(CAMERA_INDEX)

        if not cap.isOpened():
            raise RuntimeError("Kamera tidak dapat dibuka.")

        print("\n========================================")
        print(" FACE CAMERA VERIFICATION")
        print("========================================")
        print("Tekan Q untuk keluar.")
        print("")

        while True:
            success, frame = cap.read()

            if not success:
                print("Gagal membaca frame kamera.")
                break

            h, w = frame.shape[:2]

            # ==============================
            # 4. Deteksi wajah
            # ==============================
            face_service.detector.setInputSize((w, h))
            _, faces = face_service.detector.detect(frame)

            status = "NO FACE"
            similarity = 0.0

            if faces is not None:

                if len(faces) == 0:
                    status = "NO FACE"

                elif len(faces) > 1:
                    status = "MULTIPLE FACES"

                else:
                    # ==============================
                    # 5. Ambil satu wajah
                    # ==============================
                    face = faces[0]

                    try:
                        # ==============================
                        # 6. Extract embedding wajah kamera
                        # ==============================
                        current_embedding = (
                            face_service.extract_embedding(
                                frame,
                                face,
                            )
                        )

                        # ==============================
                        # 7. Bandingkan dengan DB
                        # ==============================
                        similarity = (
                            face_service.calculate_similarity(
                                registered_embedding,
                                current_embedding,
                            )
                        )

                        if similarity >= THRESHOLD:
                            status = "FACE VERIFIED"
                        else:
                            status = "FACE NOT VERIFIED"

                    except Exception as error:
                        status = f"ERROR: {error}"

            # ==============================
            # 8. Gambar bounding box
            # ==============================
            if faces is not None and len(faces) == 1:

                face = faces[0]

                x, y, fw, fh = face[:4].astype(int)

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + fw, y + fh),
                    (0, 255, 0),
                    2,
                )

            # ==============================
            # 9. Tampilkan hasil
            # ==============================
            cv2.putText(
                frame,
                status,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
            )

            cv2.putText(
                frame,
                f"Similarity: {similarity:.4f}",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            cv2.putText(
                frame,
                f"Threshold: {THRESHOLD:.2f}",
                (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            cv2.imshow(
                "SITARA - Face Verification",
                frame,
            )

            # Q = keluar
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()

    finally:
        db.close()


if __name__ == "__main__":
    main()