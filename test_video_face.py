import json

from app.core.database import SessionLocal
from app.repositories.face_repository import FaceRepository
from app.services.ai_service import AIService

PATIENT_ID = 1
VIDEO_PATH = "test_videos/face_test.mp4"


db = SessionLocal()

try:
    repository = FaceRepository()
    ai_service = AIService()

    # Ambil wajah yang sudah diregistrasikan
    face_embedding = repository.get_active_embedding_by_patient_id(
        db,
        PATIENT_ID,
    )

    if face_embedding is None:
        raise RuntimeError(
            f"Face embedding aktif untuk patient_id={PATIENT_ID} tidak ditemukan."
        )

    print("Face embedding ditemukan:")
    print(f"  ID            : {face_embedding.id}")
    print(f"  Patient ID    : {face_embedding.patient_id}")
    print(f"  Model version : {face_embedding.model_version}")
    print(f"  Active        : {face_embedding.is_active}")

    # Embedding disimpan sebagai JSON string di database
    registered_embedding = json.loads(face_embedding.embedding)

    print(f"  Embedding dim : {len(registered_embedding)}")

    # Proses video
    result = ai_service.verify_face_from_video(
        video_path=VIDEO_PATH,
        registered_embedding=registered_embedding,
        sample_fps=5,
        threshold=0.70,
    )

    print("\n=== HASIL FACE VIDEO VERIFICATION ===")
    print(f"Frames processed      : " f"{result['frames_processed']}")
    print(f"Face detected frames  : " f"{result['face_detected_frames']}")
    print(f"Verified frames       : " f"{result['verified_frames']}")
    print(f"Verification rate     : " f"{result['verification_rate']:.2%}")
    print(f"FINAL VERIFIED        : " f"{result['verified']}")

    print("\n=== SAMPLE FRAME RESULTS ===")

    for frame in result["frames"][:10]:
        print(
            f"Frame {frame['frame_index']:>3} | "
            f"{frame['timestamp']:.2f}s | "
            f"face={frame['face_detected']} | "
            f"similarity={frame['similarity']:.4f} | "
            f"verified={frame['verified']}"
        )

finally:
    db.close()
