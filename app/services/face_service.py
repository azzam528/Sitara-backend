from datetime import datetime
import json
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.face_embedding import FaceEmbedding
from app.models.face_verification import FaceVerification, FaceVerificationStatus
from app.models.medicine_schedule import MedicineSchedule
from app.models.treatment import Treatment
from app.repositories.face_repository import FaceRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.face import FaceRegisterResponse, FaceStatusResponse, FaceVerifyResponse
from app.services.face_recognition_service import FaceRecognitionService


ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class FaceService:
    """
    Business Logic Service for Face Registration, Verification, and Status Management.
    Enforces strict authenticated patient scoping and zero-trust ID validation.
    """

    def __init__(self):
        self.patient_repository = PatientRepository()
        self.face_repository = FaceRepository()
        self.recognition_service = FaceRecognitionService()

    def register_face(
        self,
        db: Session,
        current_user: User,
        image: UploadFile,
    ) -> FaceRegisterResponse:
        """
        Registers patient face embedding from an uploaded image.
        Ensures authenticated patient ownership and deactivates any previous embedding.
        """
        # 1. Resolve authenticated patient
        patient = self.patient_repository.get_by_user_id(db, current_user.id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data profil pasien tidak ditemukan untuk pengguna ini.",
            )

        # 2. Validate MIME content type
        content_type = image.content_type or ""
        if content_type.lower() not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format file tidak didukung. Harap unggah gambar JPG, PNG, atau WEBP.",
            )

        # 3. Read image file bytes
        file_bytes = image.file.read()
        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Berkas gambar kosong.",
            )

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ukuran gambar melebihi batas maksimum 10 MB.",
            )

        # 4. Decode image
        img = self.recognition_service.decode_image(file_bytes)

        # 5. Detect single face and validate quality
        face = self.recognition_service.detect_single_face(img)

        # 6. Extract 128-D embedding vector
        embedding_vector = self.recognition_service.extract_embedding(img, face)

        # 7. Serialize embedding as JSON string
        embedding_json = json.dumps(embedding_vector)

        # 8. Deactivate previous active embeddings for this patient
        self.face_repository.deactivate_embeddings_by_patient_id(db, patient.id)

        # 9. Persist new active FaceEmbedding record
        new_embedding = FaceEmbedding(
            patient_id=patient.id,
            embedding=embedding_json,
            model_version=settings.FACE_MODEL_VERSION,
            is_active=True,
        )
        self.face_repository.create_embedding(db, new_embedding)

        return FaceRegisterResponse(
            status="success",
            message="Wajah pasien berhasil didaftarkan.",
            model_version=settings.FACE_MODEL_VERSION,
        )

    def verify_face(
        self,
        db: Session,
        current_user: User,
        image: UploadFile,
        medicine_schedule_id: int,
    ) -> FaceVerifyResponse:
        """
        Verifies face identity of the authenticated patient against their registered active face embedding
        before proceeding to an AI-VOT medication intake session.
        Validates medicine schedule ownership and logs audit record in face_verifications table.
        """
        # 1. Resolve authenticated patient
        patient = self.patient_repository.get_by_user_id(db, current_user.id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data profil pasien tidak ditemukan untuk pengguna ini.",
            )

        # 2. Validate medicine schedule existence and ownership
        schedule = (
            db.query(MedicineSchedule)
            .join(Treatment, MedicineSchedule.treatment_id == Treatment.id)
            .filter(
                MedicineSchedule.id == medicine_schedule_id,
                MedicineSchedule.is_active == True,
            )
            .first()
        )

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jadwal minum obat tidak ditemukan atau sudah tidak aktif.",
            )

        if schedule.treatment.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akses ditolak. Jadwal obat ini bukan milik pasien yang sedang login.",
            )

        # 3. Retrieve active face embedding for patient
        active_embedding = self.face_repository.get_active_embedding_by_patient_id(
            db,
            patient.id,
        )

        if not active_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wajah pasien belum terdaftar. Harap lakukan pendaftaran wajah terlebih dahulu.",
            )

        # 4. Validate MIME content type
        content_type = image.content_type or ""
        if content_type.lower() not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format file tidak didukung. Harap unggah gambar JPG, PNG, atau WEBP.",
            )

        # 5. Read image file bytes
        file_bytes = image.file.read()
        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Berkas gambar kosong.",
            )

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ukuran gambar melebihi batas maksimum 10 MB.",
            )

        # 6. Decode image
        img = self.recognition_service.decode_image(file_bytes)

        # 7. Detect single face and validate quality
        face = self.recognition_service.detect_single_face(img)

        # 8. Extract 128-D embedding vector from current capture
        current_embedding_vector = self.recognition_service.extract_embedding(img, face)

        # 9. Parse registered embedding vector and compute Cosine Similarity
        raw_embedding = active_embedding.embedding
        if isinstance(raw_embedding, (str, bytes, bytearray)):
            registered_vector = json.loads(raw_embedding)
        else:
            registered_vector = raw_embedding

        similarity_score = self.recognition_service.calculate_similarity(
            registered_vector,
            current_embedding_vector,
        )

        # 10. Compare similarity against development threshold
        threshold = settings.FACE_SIMILARITY_THRESHOLD  # Default 0.70
        is_verified = (similarity_score >= threshold)
        verification_status = (
            FaceVerificationStatus.VERIFIED if is_verified else FaceVerificationStatus.FAILED
        )

        # 11. Create and persist FaceVerification audit record
        verification_record = FaceVerification(
            patient_id=patient.id,
            medicine_schedule_id=medicine_schedule_id,
            similarity_score=round(similarity_score, 4),
            threshold=threshold,
            status=verification_status,
            captured_at=datetime.utcnow(),
        )
        created_verification = self.face_repository.create_verification(db, verification_record)

        # 12. Return verification result response DTO
        return FaceVerifyResponse(
            verified=is_verified,
            similarity_score=round(similarity_score, 4),
            threshold=threshold,
            face_verification_id=created_verification.id,
            status=verification_status.value,
            message="Wajah cocok dengan data pasien terdaftar."
            if is_verified
            else "Wajah tidak cocok dengan pasien terdaftar.",
        )

    def get_face_status(
        self,
        db: Session,
        current_user: User,
    ) -> FaceStatusResponse:
        """
        Queries whether the authenticated patient has an active registered face embedding.
        """
        # 1. Resolve authenticated patient
        patient = self.patient_repository.get_by_user_id(db, current_user.id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data profil pasien tidak ditemukan untuk pengguna ini.",
            )

        # 2. Query active embedding
        active_embedding = self.face_repository.get_active_embedding_by_patient_id(
            db,
            patient.id,
        )

        if active_embedding:
            return FaceStatusResponse(
                is_registered=True,
                model_version=active_embedding.model_version,
                registered_at=active_embedding.created_at,
            )

        return FaceStatusResponse(
            is_registered=False,
            model_version=None,
            registered_at=None,
        )

