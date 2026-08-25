from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)

from app.schemas.medicine_detection import (
    MedicineDetectionResponse,
)
from app.services.medicine_detection_service import (
    medicine_detection_service,
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
