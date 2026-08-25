from pydantic import BaseModel


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class MedicineDetection(BaseModel):
    medicine: str
    confidence: float
    bounding_box: BoundingBox


class MedicineDetectionResponse(BaseModel):
    detected: bool
    detections: list[MedicineDetection]


class MedicineScheduleDetectionResponse(BaseModel):
    status: str
    expected_medicine: str
    detected_medicine: str | None = None
    confidence: float = 0.0
    bounding_box: BoundingBox | None = None
    medicine_match: bool
    message: str
