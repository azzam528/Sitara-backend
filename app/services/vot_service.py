from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.daily_medication import DailyMedicationStatus, VotStep
from app.models.medicine_schedule import MedicineSchedule
from app.models.notification import NotificationType
from app.models.user import User
from app.repositories.daily_medication_repository import (
    DailyMedicationRepository,
)
from app.repositories.medicine_schedule_repository import (
    MedicineScheduleRepository,
)
from app.schemas.daily_medication import (
    VotFaceVerifyResponse,
    VotMedicineDetectResponse,
    VotSessionResponse,
    VotStartResponse,
    VotCompleteResponse,
)
from app.services.daily_medication_service import (
    DailyMedicationService,
    today_in_jakarta,
)
from app.services.face_service import FaceService
from app.services.medicine_detection_service import (
    medicine_detection_service,
)
from app.services.notification_service import NotificationService


class VOTService:

    def __init__(self):
        self.daily_medication_service = DailyMedicationService()
        self.repository = DailyMedicationRepository()
        self.schedule_repository = MedicineScheduleRepository()
        self.face_service = FaceService()
        self.medicine_detection_service = medicine_detection_service
        self.notification_service = NotificationService()

    def start(
        self,
        db: Session,
        current_user: User,
        medicine_schedule_id: int,
    ) -> VotStartResponse:
        self.daily_medication_service._require_active_patient(
            db,
            current_user,
        )

        schedule = self.schedule_repository.get_by_id(
            db,
            medicine_schedule_id,
        )
        if schedule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medicine schedule not found",
            )

        today = today_in_jakarta()
        owned_schedule = self.repository.get_owned_schedule_for_today(
            db,
            medicine_schedule_id,
            current_user.id,
            today,
        )
        if owned_schedule is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Medicine schedule does not belong to this patient",
            )

        occurrence = self.repository.get_or_create_for_schedule_date(
            db,
            owned_schedule,
            today,
        )

        if (
            occurrence.status == DailyMedicationStatus.VERIFIED
            or occurrence.vot_step == VotStep.VERIFIED
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT untuk jadwal obat ini hari ini sudah selesai.",
            )

        if occurrence.status in (
            DailyMedicationStatus.MISSED,
            DailyMedicationStatus.REJECTED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT untuk jadwal obat ini hari ini tidak dapat dimulai.",
            )

        if occurrence.status == DailyMedicationStatus.PENDING:
            occurrence.status = DailyMedicationStatus.IN_PROGRESS
            occurrence = self.repository.update(db, occurrence)

        return VotStartResponse(
            daily_medication_id=occurrence.id,
            medicine_schedule_id=occurrence.medicine_schedule_id,
            status=occurrence.status,
            vot_step=occurrence.vot_step,
            scheduled_date=occurrence.scheduled_date,
            scheduled_time=occurrence.scheduled_time,
        )

    def get_session(
        self,
        db: Session,
        current_user: User,
        daily_medication_id: int,
    ) -> VotSessionResponse:
        occurrence = self.daily_medication_service.get_owned(
            db,
            current_user,
            daily_medication_id,
        )
        schedule: MedicineSchedule = occurrence.medicine_schedule
        medicine_name = schedule.medicine.name if schedule.medicine else ""

        return VotSessionResponse(
            daily_medication_id=occurrence.id,
            medicine_schedule_id=occurrence.medicine_schedule_id,
            medicine_id=schedule.medicine_id,
            medicine_name=medicine_name,
            dosage=schedule.dosage,
            scheduled_date=occurrence.scheduled_date,
            scheduled_time=occurrence.scheduled_time,
            quantity_remaining=schedule.quantity_remaining,
            status=occurrence.status,
            vot_step=occurrence.vot_step,
        )

    def verify_face(
        self,
        db: Session,
        current_user: User,
        daily_medication_id: int,
        image: UploadFile,
    ) -> VotFaceVerifyResponse:
        occurrence = self.daily_medication_service.get_owned(
            db,
            current_user,
            daily_medication_id,
        )

        if occurrence.status == DailyMedicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT belum dimulai.",
            )

        if occurrence.status == DailyMedicationStatus.VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT sudah selesai.",
            )

        if occurrence.status in (
            DailyMedicationStatus.MISSED,
            DailyMedicationStatus.REJECTED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT tidak dapat dilanjutkan.",
            )

        if occurrence.status != DailyMedicationStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT tidak dapat dilanjutkan.",
            )

        if occurrence.vot_step == VotStep.FACE_VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Face verification sudah selesai.",
            )

        if occurrence.vot_step != VotStep.WAITING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Face verification tidak dapat dilakukan pada tahap VOT ini.",
            )

        medicine_schedule_id = occurrence.medicine_schedule_id
        face_result = self.face_service.verify_face(
            db=db,
            current_user=current_user,
            image=image,
            medicine_schedule_id=medicine_schedule_id,
        )

        occurrence = self.repository.get_owned_by_id(
            db,
            daily_medication_id,
            current_user.id,
        )
        if occurrence is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily medication not found",
            )

        if face_result.verified:
            occurrence.face_verification_id = face_result.face_verification_id
            occurrence.vot_step = VotStep.FACE_VERIFIED
            occurrence = self.repository.update(db, occurrence)

        return VotFaceVerifyResponse(
            daily_medication_id=occurrence.id,
            medicine_schedule_id=occurrence.medicine_schedule_id,
            face_verification_id=face_result.face_verification_id,
            verified=face_result.verified,
            similarity_score=face_result.similarity_score,
            threshold=face_result.threshold,
            status=face_result.status,
            vot_step=occurrence.vot_step,
            message=face_result.message,
        )

    def detect_medicine(
        self,
        db: Session,
        current_user: User,
        daily_medication_id: int,
        image: UploadFile,
    ) -> VotMedicineDetectResponse:
        occurrence = self.daily_medication_service.get_owned(
            db,
            current_user,
            daily_medication_id,
        )

        if occurrence.status == DailyMedicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT belum dimulai.",
            )

        if occurrence.status == DailyMedicationStatus.VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT sudah selesai.",
            )

        if occurrence.status in (
            DailyMedicationStatus.MISSED,
            DailyMedicationStatus.REJECTED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT tidak dapat dilanjutkan.",
            )

        if occurrence.status != DailyMedicationStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT tidak dapat dilanjutkan.",
            )

        if occurrence.vot_step == VotStep.WAITING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Face verification belum berhasil.",
            )

        if occurrence.vot_step == VotStep.MEDICINE_MATCHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medicine detection sudah selesai.",
            )

        if occurrence.vot_step != VotStep.FACE_VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medicine detection tidak dapat dilakukan pada tahap VOT ini.",
            )

        schedule: MedicineSchedule = occurrence.medicine_schedule
        if schedule is None or schedule.medicine is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medicine pada schedule tidak ditemukan.",
            )

        expected_medicine = schedule.medicine.name
        image_bytes = image.file.read()
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Berkas gambar kosong.",
            )

        detection = self.medicine_detection_service.detect_expected_medicine(
            image_bytes=image_bytes,
            expected_medicine=expected_medicine,
        )

        if detection["medicine_match"]:
            occurrence.vot_step = VotStep.MEDICINE_MATCHED
            occurrence = self.repository.update(db, occurrence)

        bounding_box = detection.get("bounding_box")
        return VotMedicineDetectResponse(
            daily_medication_id=occurrence.id,
            medicine_schedule_id=occurrence.medicine_schedule_id,
            expected_medicine=expected_medicine,
            detected_medicine=detection.get("detected_medicine"),
            confidence=detection.get("confidence") or 0.0,
            bounding_box=bounding_box,
            medicine_match=bool(detection.get("medicine_match")),
            status=occurrence.status,
            vot_step=occurrence.vot_step,
            message=detection.get("message") or "",
        )

    def complete(
        self,
        db: Session,
        current_user: User,
        daily_medication_id: int,
        drinking_verified: bool,
    ) -> VotCompleteResponse:
        occurrence = self.daily_medication_service.get_owned(
            db,
            current_user,
            daily_medication_id,
        )

        if occurrence.status == DailyMedicationStatus.VERIFIED:
            return VotCompleteResponse(
                daily_medication_id=occurrence.id,
                status=occurrence.status,
                vot_step=occurrence.vot_step,
                completed_at=occurrence.completed_at,
                message="VOT sudah selesai.",
            )

        if occurrence.status != DailyMedicationStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT tidak dapat diselesaikan pada status ini.",
            )

        if occurrence.vot_step != VotStep.MEDICINE_MATCHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verifikasi wajah dan obat belum selesai.",
            )

        if not drinking_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proses minum belum terverifikasi.",
            )

        occurrence.vot_step = VotStep.VERIFIED
        occurrence.status = DailyMedicationStatus.VERIFIED
        occurrence.completed_at = datetime.utcnow()

        occurrence = self.repository.update(
            db,
            occurrence,
        )

        self.notification_service.create(
            db=db,
            user_id=current_user.id,
            title="Verifikasi Minum Obat",
            message="Verifikasi minum obat berhasil.",
            notification_type=NotificationType.VIDEO,
            reference_id=occurrence.id,
        )

        return VotCompleteResponse(
            daily_medication_id=occurrence.id,
            status=occurrence.status,
            vot_step=occurrence.vot_step,
            completed_at=occurrence.completed_at,
            message="Verifikasi minum obat berhasil.",
        )
