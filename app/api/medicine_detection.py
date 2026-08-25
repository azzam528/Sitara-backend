from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.medicine_schedule import MedicineSchedule
from app.schemas.medicine_detection import (
    MedicineDetectionResponse,
)
from app.services.medicine_detection_service import (
    medicine_detection_service,
)
from app.schemas.medicine_detection import (
    MedicineDetectionResponse,
    MedicineScheduleDetectionResponse,
)

router = APIRouter(
    prefix="/medicine-detection",
    tags=["Medicine Detection"],
)


@router.post(
    "/detect",
    response_model=MedicineDetectionResponse,
)
async def detect_medicine(
    image: UploadFile = File(...),
):
    try:

        # Read uploaded image
        image_bytes = await image.read()

        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="Image is empty",
            )

        detections = medicine_detection_service.detect(image_bytes)

        return {
            "detected": len(detections) > 0,
            "detections": detections,
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Medicine detection failed: {str(e)}",
        )


@router.post(
    "/detect-schedule",
    response_model=MedicineScheduleDetectionResponse,
)
async def detect_medicine_for_schedule(
    medicine_schedule_id: int = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        # Ambil medicine schedule
        schedule = (
            db.query(MedicineSchedule)
            .filter(MedicineSchedule.id == medicine_schedule_id)
            .first()
        )

        if schedule is None:
            raise HTTPException(
                status_code=404,
                detail="Medicine schedule tidak ditemukan.",
            )

        if not schedule.is_active:
            raise HTTPException(
                status_code=400,
                detail="Medicine schedule tidak aktif.",
            )

        # Pastikan relasi medicine tersedia
        if schedule.medicine is None:
            raise HTTPException(
                status_code=404,
                detail="Medicine pada schedule tidak ditemukan.",
            )

        expected_medicine = schedule.medicine.name

        # Baca gambar
        image_bytes = await image.read()

        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="Image is empty.",
            )

        # Jalankan YOLO + comparison
        result = medicine_detection_service.detect_expected_medicine(
            image_bytes=image_bytes,
            expected_medicine=expected_medicine,
        )

        return result

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=("Medicine schedule detection failed: " f"{str(e)}"),
        )
