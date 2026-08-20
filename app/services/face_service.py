import json
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.face_embedding import FaceEmbedding
from app.repositories.face_repository import FaceRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.face import FaceRegisterResponse, FaceStatusResponse
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
    Business Logic Service for Face Registration and Status Management.
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
