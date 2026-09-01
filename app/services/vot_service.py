from datetime import datetime
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.daily_medication import DailyMedication, DailyMedicationStatus, VotStep
from app.models.medicine_schedule import MedicineSchedule
from app.models.notification import NotificationType, NotificationReferenceType
from app.models.user import User
from app.models.video_verification import VideoVerification, VerificationStatus
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

    def _handle_escalation(
        self,
        db: Session,
        current_user: User,
        occurrence: DailyMedication,
        reason: str,
        max_stage: str | None = None,
    ) -> DailyMedication:
        occurrence.status = DailyMedicationStatus.NEEDS_REVIEW
        occurrence.failure_reason = reason
        if max_stage:
            occurrence.max_drinking_stage = max_stage

        # Create or link VideoVerification record idempotently
        if not occurrence.video_verification_id:
            video = VideoVerification(
                medicine_schedule_id=occurrence.medicine_schedule_id,
                face_verification_id=occurrence.face_verification_id,
                verification_date=occurrence.scheduled_date,
                video_path="vot_escalation/pending",
                file_name="vot_escalation.mp4",
                mime_type="video/mp4",
                file_size=0,
                status=VerificationStatus.PENDING,
                review_note=f"Eskalasi AI VOT: {reason}",
            )
            db.add(video)
            db.flush()
            occurrence.video_verification_id = video.id

        occurrence = self.repository.update(db, occurrence)

        # Notify Nakes in the patient's facility
        patient_name = "Pasien"
        if hasattr(current_user, "patient") and current_user.patient and current_user.patient.full_name:
            patient_name = current_user.patient.full_name

        nakes_list = (
            db.query(User)
            .filter(
                User.role == "nakes",
                User.facility_id == current_user.facility_id,
                User.is_active.is_(True),
            )
            .all()
        )

        for nakes in nakes_list:
            self.notification_service.create(
                db=db,
                user_id=nakes.id,
                title="Eskalasi Verifikasi Obat",
                message=f"{patient_name} memerlukan peninjauan verifikasi minum obat ({reason}).",
                notification_type=NotificationType.VIDEO,
                reference_type=NotificationReferenceType.VIDEO_VERIFICATION,
                reference_id=occurrence.video_verification_id or occurrence.id,
            )

        return occurrence

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

        if occurrence.status == DailyMedicationStatus.NEEDS_REVIEW:
            return VotStartResponse(
                daily_medication_id=occurrence.id,
                medicine_schedule_id=occurrence.medicine_schedule_id,
                status=occurrence.status,
                vot_step=occurrence.vot_step,
                scheduled_date=occurrence.scheduled_date,
                scheduled_time=occurrence.scheduled_time,
                attempt_count=occurrence.attempt_count,
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
            attempt_count=occurrence.attempt_count,
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

        can_retry = (
            occurrence.status == DailyMedicationStatus.IN_PROGRESS
            and occurrence.attempt_count < 3
        )

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
            attempt_count=occurrence.attempt_count,
            can_retry=can_retry,
            failure_reason=occurrence.failure_reason,
            max_drinking_stage=occurrence.max_drinking_stage,
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

        if occurrence.status == DailyMedicationStatus.NEEDS_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT sedang dalam peninjauan Nakes.",
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
                verified=True,
                similarity_score=face_result.similarity_score,
                threshold=face_result.threshold,
                status=face_result.status,
                vot_step=occurrence.vot_step,
                message=face_result.message,
                attempt_count=occurrence.attempt_count,
                can_retry=False,
                failure_reason=None,
            )

        # Failure handling: increment attempt_count
        occurrence.attempt_count += 1
        occurrence.failure_reason = "FACE_VERIFICATION_FAILED"

        if occurrence.attempt_count >= 3:
            occurrence = self._handle_escalation(
                db, current_user, occurrence, reason="FACE_VERIFICATION_FAILED"
            )
            msg = face_result.message or "Wajah tidak cocok."
            return VotFaceVerifyResponse(
                daily_medication_id=occurrence.id,
                medicine_schedule_id=occurrence.medicine_schedule_id,
                face_verification_id=face_result.face_verification_id,
                verified=False,
                similarity_score=face_result.similarity_score,
                threshold=face_result.threshold,
                status=face_result.status,
                vot_step=occurrence.vot_step,
                message=f"{msg} Batas maksimal 3 percobaan tercapai, dialihkan ke Nakes.",
                attempt_count=occurrence.attempt_count,
                can_retry=False,
                failure_reason="FACE_VERIFICATION_FAILED",
            )

        occurrence = self.repository.update(db, occurrence)
        return VotFaceVerifyResponse(
            daily_medication_id=occurrence.id,
            medicine_schedule_id=occurrence.medicine_schedule_id,
            face_verification_id=face_result.face_verification_id,
            verified=False,
            similarity_score=face_result.similarity_score,
            threshold=face_result.threshold,
            status=face_result.status,
            vot_step=occurrence.vot_step,
            message=face_result.message,
            attempt_count=occurrence.attempt_count,
            can_retry=True,
            failure_reason="FACE_VERIFICATION_FAILED",
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

        if occurrence.status == DailyMedicationStatus.NEEDS_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT sedang dalam peninjauan Nakes.",
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

        bounding_box = detection.get("bounding_box")

        if detection["medicine_match"]:
            occurrence.vot_step = VotStep.MEDICINE_MATCHED
            occurrence = self.repository.update(db, occurrence)
            return VotMedicineDetectResponse(
                daily_medication_id=occurrence.id,
                medicine_schedule_id=occurrence.medicine_schedule_id,
                expected_medicine=expected_medicine,
                detected_medicine=detection.get("detected_medicine"),
                confidence=detection.get("confidence") or 0.0,
                bounding_box=bounding_box,
                medicine_match=True,
                status=occurrence.status,
                vot_step=occurrence.vot_step,
                message=detection.get("message") or "",
                attempt_count=occurrence.attempt_count,
                can_retry=False,
                failure_reason=None,
            )

        # Failure handling: increment attempt_count
        occurrence.attempt_count += 1
        occurrence.failure_reason = "MEDICINE_DETECTION_FAILED"

        if occurrence.attempt_count >= 3:
            occurrence = self._handle_escalation(
                db, current_user, occurrence, reason="MEDICINE_DETECTION_FAILED"
            )
            msg = detection.get("message") or "Obat tidak sesuai."
            return VotMedicineDetectResponse(
                daily_medication_id=occurrence.id,
                medicine_schedule_id=occurrence.medicine_schedule_id,
                expected_medicine=expected_medicine,
                detected_medicine=detection.get("detected_medicine"),
                confidence=detection.get("confidence") or 0.0,
                bounding_box=bounding_box,
                medicine_match=False,
                status=occurrence.status,
                vot_step=occurrence.vot_step,
                message=f"{msg} Batas maksimal 3 percobaan tercapai, dialihkan ke Nakes.",
                attempt_count=occurrence.attempt_count,
                can_retry=False,
                failure_reason="MEDICINE_DETECTION_FAILED",
            )

        occurrence = self.repository.update(db, occurrence)
        return VotMedicineDetectResponse(
            daily_medication_id=occurrence.id,
            medicine_schedule_id=occurrence.medicine_schedule_id,
            expected_medicine=expected_medicine,
            detected_medicine=detection.get("detected_medicine"),
            confidence=detection.get("confidence") or 0.0,
            bounding_box=bounding_box,
            medicine_match=False,
            status=occurrence.status,
            vot_step=occurrence.vot_step,
            message=detection.get("message") or "",
            attempt_count=occurrence.attempt_count,
            can_retry=True,
            failure_reason="MEDICINE_DETECTION_FAILED",
        )

    def complete(
        self,
        db: Session,
        current_user: User,
        daily_medication_id: int,
        drinking_verified: bool = True,
        max_drinking_stage: str | None = None,
        failure_reason: str | None = None,
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
                attempt_count=occurrence.attempt_count,
                can_retry=False,
                failure_reason=occurrence.failure_reason,
                max_drinking_stage=occurrence.max_drinking_stage,
            )

        if occurrence.status == DailyMedicationStatus.NEEDS_REVIEW:
            return VotCompleteResponse(
                daily_medication_id=occurrence.id,
                status=occurrence.status,
                vot_step=occurrence.vot_step,
                completed_at=occurrence.completed_at,
                message="VOT sedang dalam peninjauan Nakes.",
                attempt_count=occurrence.attempt_count,
                can_retry=False,
                failure_reason=occurrence.failure_reason,
                max_drinking_stage=occurrence.max_drinking_stage,
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

        # CASE E: DRINKING SUCCESS
        if drinking_verified or max_drinking_stage == "completed":
            occurrence.vot_step = VotStep.VERIFIED
            occurrence.status = DailyMedicationStatus.VERIFIED
            occurrence.completed_at = datetime.utcnow()
            occurrence.max_drinking_stage = "completed"
            occurrence = self.repository.update(db, occurrence)

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
                attempt_count=occurrence.attempt_count,
                can_retry=False,
                failure_reason=None,
                max_drinking_stage="completed",
            )

        # CASE D: DRINKING AMBIGUOUS (nearMouth / withdrawing reached, potential ingestion)
        # NO RETRY, DO NOT INCREMENT ATTEMPT COUNT (PATIENT MUST NOT RE-DRINK)
        if max_drinking_stage in ["nearMouth", "withdrawing"]:
            occurrence = self._handle_escalation(
                db,
                current_user,
                occurrence,
                reason="DRINKING_AMBIGUOUS",
                max_stage=max_drinking_stage,
            )
            return VotCompleteResponse(
                daily_medication_id=occurrence.id,
                status=occurrence.status,
                vot_step=occurrence.vot_step,
                completed_at=None,
                message="Proses minum terdeteksi sebagian dan dialihkan ke Nakes untuk ditinjau.",
                attempt_count=occurrence.attempt_count,
                can_retry=False,
                failure_reason="DRINKING_AMBIGUOUS",
                max_drinking_stage=max_drinking_stage,
            )

        # If drinking_verified is False and no max_drinking_stage is specified, preserve HTTP 400 contract for backwards compatibility
        if not drinking_verified and not max_drinking_stage:
            occurrence.attempt_count += 1
            reason = failure_reason or "DRINKING_TIMEOUT"
            occurrence.failure_reason = reason
            if occurrence.attempt_count >= 3:
                self._handle_escalation(
                    db,
                    current_user,
                    occurrence,
                    reason=reason,
                )
            else:
                self.repository.update(db, occurrence)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proses minum belum terverifikasi.",
            )

        # CASE C: DRINKING TIMEOUT (waiting / handWithMedicine / approachingMouth)
        occurrence.attempt_count += 1
        reason = failure_reason or "DRINKING_TIMEOUT"
        occurrence.failure_reason = reason
        occurrence.max_drinking_stage = max_drinking_stage

        if occurrence.attempt_count >= 3:
            occurrence = self._handle_escalation(
                db,
                current_user,
                occurrence,
                reason=reason,
                max_stage=max_drinking_stage,
            )
            return VotCompleteResponse(
                daily_medication_id=occurrence.id,
                status=occurrence.status,
                vot_step=occurrence.vot_step,
                completed_at=None,
                message="Batas maksimal 3 percobaan tercapai. Verifikasi diteruskan ke Nakes.",
                attempt_count=occurrence.attempt_count,
                can_retry=False,
                failure_reason=reason,
                max_drinking_stage=max_drinking_stage,
            )

        occurrence = self.repository.update(db, occurrence)
        return VotCompleteResponse(
            daily_medication_id=occurrence.id,
            status=occurrence.status,
            vot_step=occurrence.vot_step,
            completed_at=None,
            message="Proses minum belum terverifikasi. Silakan coba lagi.",
            attempt_count=occurrence.attempt_count,
            can_retry=True,
            failure_reason=reason,
            max_drinking_stage=max_drinking_stage,
        )
