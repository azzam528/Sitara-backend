from sqlalchemy.orm import Session

from app.models.face_embedding import FaceEmbedding
from app.models.face_verification import FaceVerification


class FaceRepository:

    def create_embedding(
        self,
        db: Session,
        embedding: FaceEmbedding,
    ) -> FaceEmbedding:
        db.add(embedding)
        db.commit()
        db.refresh(embedding)
        return embedding

    def get_active_embedding_by_patient_id(
        self,
        db: Session,
        patient_id: int,
    ) -> FaceEmbedding | None:
        return (
            db.query(FaceEmbedding)
            .filter(
                FaceEmbedding.patient_id == patient_id,
                FaceEmbedding.is_active == True,
            )
            .order_by(FaceEmbedding.created_at.desc())
            .first()
        )

    def get_all_embeddings_by_patient_id(
        self,
        db: Session,
        patient_id: int,
    ) -> list[FaceEmbedding]:
        return (
            db.query(FaceEmbedding)
            .filter(FaceEmbedding.patient_id == patient_id)
            .order_by(FaceEmbedding.created_at.desc())
            .all()
        )

    def deactivate_embeddings_by_patient_id(
        self,
        db: Session,
        patient_id: int,
    ) -> None:
        """
        Deactivates all previous active embeddings for the patient
        before registering a new one, keeping history while ensuring
        only one active embedding exists.
        """
        active_records = (
            db.query(FaceEmbedding)
            .filter(
                FaceEmbedding.patient_id == patient_id,
                FaceEmbedding.is_active == True,
            )
            .all()
        )
        for record in active_records:
            record.is_active = False
        if active_records:
            db.commit()

    def create_verification(
        self,
        db: Session,
        verification: FaceVerification,
    ) -> FaceVerification:
        db.add(verification)
        db.commit()
        db.refresh(verification)
        return verification

    def get_verification_by_id(
        self,
        db: Session,
        verification_id: int,
    ) -> FaceVerification | None:
        return (
            db.query(FaceVerification)
            .filter(FaceVerification.id == verification_id)
            .first()
        )
