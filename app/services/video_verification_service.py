from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.video_verification import (
    VideoVerification,
    VerificationStatus,
)

from app.models.medicine_schedule import (
    MedicineSchedule,
)

from app.models.treatment import (
    Treatment,
)

from app.models.patient import (
    Patient,
)

from app.models.user import (
    User,
)

from app.models.notification import (
    NotificationType,
    NotificationReferenceType,
)

from app.repositories.video_verification_repository import (
    VideoVerificationRepository,
)

from app.repositories.medicine_schedule_repository import (
    MedicineScheduleRepository,
)

from app.schemas.video_verification import (
    VideoVerificationCreate,
    VideoVerificationUpdate,
)

from app.services.notification_service import (
    NotificationService,
)


class VideoVerificationService:

    def __init__(self):

        self.repository = VideoVerificationRepository()

        self.schedule_repository = (
            MedicineScheduleRepository()
        )

        self.notification_service = (
            NotificationService()
        )

    # =====================================================
    # CREATE VIDEO
    # PATIENT
    # =====================================================

    def create_video(
        self,
        db: Session,
        data: VideoVerificationCreate,
        current_user: User,
    ):

        # -------------------------------------------------
        # CHECK MEDICINE SCHEDULE
        # -------------------------------------------------

        schedule = self.schedule_repository.get_by_id(
            db,
            data.medicine_schedule_id,
        )

        if not schedule:

            raise HTTPException(
                status_code=404,
                detail="Medicine schedule not found",
            )

        # -------------------------------------------------
        # GET TREATMENT
        # -------------------------------------------------

        treatment = (
            db.query(Treatment)
            .filter(
                Treatment.id == schedule.treatment_id,
                Treatment.is_active.is_(True),
            )
            .first()
        )

        if not treatment:

            raise HTTPException(
                status_code=404,
                detail="Treatment not found",
            )

        # -------------------------------------------------
        # CHECK PATIENT OWNERSHIP
        # -------------------------------------------------

        patient = (
            db.query(Patient)
            .filter(
                Patient.id == treatment.patient_id,
                Patient.user_id == current_user.id,
                Patient.is_active.is_(True),
            )
            .first()
        )

        if not patient:

            raise HTTPException(
                status_code=403,
                detail=(
                    "Medicine schedule does not belong "
                    "to this patient"
                ),
            )

        # -------------------------------------------------
        # CREATE VIDEO
        # -------------------------------------------------

        video = VideoVerification(
            medicine_schedule_id=(
                data.medicine_schedule_id
            ),
            verification_date=(
                data.verification_date
            ),
            video_path=data.video_path,
            file_name=data.file_name,
            mime_type=data.mime_type,
            file_size=data.file_size,
            thumbnail_path=data.thumbnail_path,
            status=VerificationStatus.PENDING,
        )

        video = self.repository.create(
            db,
            video,
        )

        # -------------------------------------------------
        # NOTIFICATION TO NAKES
        # -------------------------------------------------

        nakes_list = (
            db.query(User)
            .filter(
                User.role == "nakes",
                User.is_active.is_(True),
            )
            .all()
        )

        for nakes in nakes_list:

            self.notification_service.create(
                db=db,
                user_id=nakes.id,
                title="Video Verifikasi Baru",
                message=(
                    "Pasien mengirim video "
                    "verifikasi minum obat."
                ),
                notification_type=(
                    NotificationType.VIDEO
                ),
                reference_type=(
                    NotificationReferenceType
                    .VIDEO_VERIFICATION
                ),
                reference_id=video.id,
            )

        return video

    # =====================================================
    # GET ALL
    # NAKES
    # =====================================================

    def get_all(
        self,
        db: Session,
    ):

        return self.repository.get_all(db)

    # =====================================================
    # GET BY ID
    # NAKES
    # =====================================================

    def get_by_id(
        self,
        db: Session,
        video_id: int,
    ):

        video = self.repository.get_by_id(
            db,
            video_id,
        )

        if not video:

            raise HTTPException(
                status_code=404,
                detail="Video verification not found",
            )

        return video

    # =====================================================
    # UPDATE
    # NAKES
    # =====================================================

    def update_video(
        self,
        db: Session,
        video_id: int,
        data: VideoVerificationUpdate,
    ):

        video = self.get_by_id(
            db,
            video_id,
        )

        # -------------------------------------------------
        # UPDATE AI CONFIDENCE
        # -------------------------------------------------

        if data.ai_confidence is not None:

            video.ai_confidence = (
                data.ai_confidence
            )

        # -------------------------------------------------
        # UPDATE STATUS
        # -------------------------------------------------

        if data.status is not None:

            video.status = data.status

        # -------------------------------------------------
        # UPDATE REVIEW NOTE
        # -------------------------------------------------

        if data.review_note is not None:

            video.review_note = (
                data.review_note
            )

        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

        video = self.repository.update(
            db,
            video,
        )

        # -------------------------------------------------
        # SEND NOTIFICATION IF FINAL STATUS
        # -------------------------------------------------

        if data.status in [
            VerificationStatus.VERIFIED,
            VerificationStatus.REJECTED,
        ]:

            schedule = (
                db.query(MedicineSchedule)
                .filter(
                    MedicineSchedule.id
                    == video.medicine_schedule_id,
                )
                .first()
            )

            if schedule:

                treatment = (
                    db.query(Treatment)
                    .filter(
                        Treatment.id
                        == schedule.treatment_id,
                        Treatment.is_active.is_(True),
                    )
                    .first()
                )

                if treatment:

                    patient = (
                        db.query(Patient)
                        .filter(
                            Patient.id
                            == treatment.patient_id,
                            Patient.is_active.is_(True),
                        )
                        .first()
                    )

                    if patient:

                        if (
                            data.status
                            == VerificationStatus.VERIFIED
                        ):

                            title = (
                                "Video Terverifikasi"
                            )

                            message = (
                                "Video verifikasi "
                                "minum obat kamu "
                                "telah berhasil "
                                "diverifikasi."
                            )

                        else:

                            title = (
                                "Video Ditolak"
                            )

                            message = (
                                "Video verifikasi "
                                "minum obat kamu "
                                "ditolak. Silakan "
                                "upload kembali."
                            )

                        self.notification_service.create(
                            db=db,
                            user_id=patient.user_id,
                            title=title,
                            message=message,
                            notification_type=(
                                NotificationType.VIDEO
                            ),
                            reference_type=(
                                NotificationReferenceType
                                .VIDEO_VERIFICATION
                            ),
                            reference_id=video.id,
                        )

        return video

    # =====================================================
    # DELETE
    # NAKES
    # =====================================================

    def delete_video(
        self,
        db: Session,
        video_id: int,
    ):

        video = self.get_by_id(
            db,
            video_id,
        )

        return self.repository.delete(
            db,
            video,
        )

    # =====================================================
    # GET PENDING
    # NAKES
    # =====================================================

    def get_pending(
        self,
        db: Session,
    ):

        return self.repository.get_pending(
            db
        )