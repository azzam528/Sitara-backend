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
