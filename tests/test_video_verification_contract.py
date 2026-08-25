import os
import pytest
from datetime import datetime, date, time, timezone, timedelta
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup test environment
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforphase8a"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:5173"
os.environ["ACTIVATION_BASE_URL"] = "https://activation.test.local"

from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.patient import Patient, GenderEnum
from app.models.health_facility import HealthFacility
from app.models.treatment import Treatment, TreatmentPhase, TreatmentStatus, RegimenEnum
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.face_verification import FaceVerification, FaceVerificationStatus
from app.models.video_verification import VideoVerification
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


def create_test_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.fixture(autouse=True)
def setup_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(name="RS SITARA", is_active=True)
    db.add(facility)
    db.commit()

    # User 1 (Patient 1)
    user1 = User(
        username="patient1_p8a",
        email="patient1_p8a@sitara.com",
        password_hash="hashedpassword123",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    # User 2 (Patient 2)
    user2 = User(
        username="patient2_p8a",
        email="patient2_p8a@sitara.com",
        password_hash="hashedpassword123",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    db.add_all([user1, user2])
    db.commit()

    patient1 = Patient(
        user_id=user1.id,
        medical_record_number="MRN-P8A-001",
        full_name="Patient One",
        nik="3201010000000081",
        phone="08111111111",
        gender=GenderEnum.MALE,
        birth_date=date(1990, 1, 1),
        address="Address 1",
        occupation="Employee",
        pmo_name="PMO 1",
        pmo_phone="08111111112",
        is_active=True,
    )
    patient2 = Patient(
        user_id=user2.id,
        medical_record_number="MRN-P8A-002",
        full_name="Patient Two",
        nik="3201010000000082",
        phone="08222222222",
        gender=GenderEnum.FEMALE,
        birth_date=date(1992, 2, 2),
        address="Address 2",
        occupation="Employee",
        pmo_name="PMO 2",
        pmo_phone="08222222223",
        is_active=True,
    )
    db.add_all([patient1, patient2])
    db.commit()

    treatment1 = Treatment(
        patient_id=patient1.id,
        doctor_name="dr. Sitara",
        diagnosis_date=date.today(),
        therapy_start_date=date.today(),
        therapy_end_date=date.today() + timedelta(days=180),
        phase=TreatmentPhase.INTENSIVE,
        status=TreatmentStatus.ACTIVE,
        regimen=RegimenEnum.CATEGORY_1,
        is_active=True,
    )
    treatment2 = Treatment(
        patient_id=patient2.id,
        doctor_name="dr. Sitara",
        diagnosis_date=date.today(),
        therapy_start_date=date.today(),
        therapy_end_date=date.today() + timedelta(days=180),
        phase=TreatmentPhase.INTENSIVE,
        status=TreatmentStatus.ACTIVE,
        regimen=RegimenEnum.CATEGORY_1,
        is_active=True,
    )
    db.add_all([treatment1, treatment2])
    db.commit()

    med = Medicine(
        code="MED01",
        name="Rifampisin",
        category="OAT",
        strength="450mg",
        unit="Tablet",
        is_active=True,
    )
    db.add(med)
    db.commit()

    sched1 = MedicineSchedule(
        treatment_id=treatment1.id,
        medicine_id=med.id,
        dosage="1 Tablet",
        quantity_initial=60,
        quantity_remaining=50,
        drink_time=time(8, 0, 0),
        is_active=True,
    )
    sched2 = MedicineSchedule(
        treatment_id=treatment2.id,
        medicine_id=med.id,
        dosage="1 Tablet",
        quantity_initial=60,
        quantity_remaining=50,
        drink_time=time(8, 0, 0),
        is_active=True,
    )
    db.add_all([sched1, sched2])
    db.commit()

    now = datetime.now(timezone.utc)
    # Face Verification Records
    fv_verified1 = FaceVerification(
        patient_id=patient1.id,
        medicine_schedule_id=sched1.id,
        similarity_score=0.88,
        threshold=0.70,
        status=FaceVerificationStatus.VERIFIED,
        captured_at=now,
    )
    fv_failed1 = FaceVerification(
        patient_id=patient1.id,
        medicine_schedule_id=sched1.id,
        similarity_score=0.41,
        threshold=0.70,
        status=FaceVerificationStatus.FAILED,
        captured_at=now,
    )
    fv_pending1 = FaceVerification(
        patient_id=patient1.id,
        medicine_schedule_id=sched1.id,
        similarity_score=0.00,
        threshold=0.70,
        status=FaceVerificationStatus.PENDING,
        captured_at=now,
    )
    fv_patient2 = FaceVerification(
        patient_id=patient2.id,
        medicine_schedule_id=sched2.id,
        similarity_score=0.85,
        threshold=0.70,
        status=FaceVerificationStatus.VERIFIED,
        captured_at=now,
    )
    db.add_all([fv_verified1, fv_failed1, fv_pending1, fv_patient2])
    db.commit()

    yield

    db.close()
    Base.metadata.drop_all(bind=engine)


def get_auth_headers(user_id: int = 1):
    token = create_test_token(user_id)
    return {"Authorization": f"Bearer {token}"}


# =========================================================
# PHASE 8A BACKEND CONTRACT TESTS
# =========================================================

def test_01_create_video_without_face_verification_id_success():
    """1. Backward compatibility: Create video without face_verification_id"""
    payload = {
        "medicine_schedule_id": 1,
        "verification_date": str(date.today()),
        "video_path": "/storage/videos/test.mp4",
        "file_name": "test.mp4",
        "mime_type": "video/mp4",
        "file_size": 1024000,
    }
    response = client.post("/video-verifications", json=payload, headers=get_auth_headers(1))
    assert response.status_code == 200
    data = response.json()
    assert data["medicine_schedule_id"] == 1
    assert data["face_verification_id"] is None


def test_02_create_video_with_valid_verified_face_verification_id():
    """2. Create video with valid verified face_verification_id -> SUCCESS"""
    payload = {
        "medicine_schedule_id": 1,
        "face_verification_id": 1,
        "verification_date": str(date.today()),
        "video_path": "/storage/videos/test.mp4",
        "file_name": "test.mp4",
        "mime_type": "video/mp4",
        "file_size": 1024000,
    }
    response = client.post("/video-verifications", json=payload, headers=get_auth_headers(1))
    assert response.status_code == 200
    data = response.json()
    assert data["medicine_schedule_id"] == 1
    assert data["face_verification_id"] == 1


def test_03_create_video_with_nonexistent_face_verification_id():
    """3. Non-existent face_verification_id -> HTTP 404"""
    payload = {
        "medicine_schedule_id": 1,
        "face_verification_id": 99999,
        "verification_date": str(date.today()),
        "video_path": "/storage/videos/test.mp4",
        "file_name": "test.mp4",
        "mime_type": "video/mp4",
        "file_size": 1024000,
    }
    response = client.post("/video-verifications", json=payload, headers=get_auth_headers(1))
    assert response.status_code == 404
    assert "Face verification not found" in response.json()["detail"]


def test_04_create_video_with_other_patient_face_verification_id():
    """4. face_verification_id belongs to another patient -> HTTP 403"""
    payload = {
        "medicine_schedule_id": 1,
        "face_verification_id": 4,  # Belongs to Patient 2 (user 2)
        "verification_date": str(date.today()),
        "video_path": "/storage/videos/test.mp4",
        "file_name": "test.mp4",
        "mime_type": "video/mp4",
        "file_size": 1024000,
    }
    response = client.post("/video-verifications", json=payload, headers=get_auth_headers(1))
    assert response.status_code == 403
    assert "does not belong to this patient" in response.json()["detail"]


def test_05_create_video_with_different_schedule_face_verification_id():
    """5. face_verification_id is for a different schedule -> HTTP 400"""
    db = TestingSessionLocal()
    sched_other = MedicineSchedule(
        treatment_id=1,
        medicine_id=1,
        dosage="2 Tablet",
        quantity_initial=60,
        quantity_remaining=50,
        drink_time=time(20, 0, 0),
        is_active=True,
    )
    db.add(sched_other)
    db.commit()
    sched_other_id = sched_other.id
    db.close()

    payload = {
        "medicine_schedule_id": sched_other_id,
        "face_verification_id": 1,  # Belongs to schedule 1
        "verification_date": str(date.today()),
        "video_path": "/storage/videos/test.mp4",
        "file_name": "test.mp4",
        "mime_type": "video/mp4",
        "file_size": 1024000,
    }
    response = client.post("/video-verifications", json=payload, headers=get_auth_headers(1))
    assert response.status_code == 400
    assert "different medicine schedule" in response.json()["detail"]


def test_06_create_video_with_failed_face_verification_status():
    """6. face_verification_id has status FAILED -> HTTP 400"""
    payload = {
        "medicine_schedule_id": 1,
        "face_verification_id": 2,  # Status: FAILED
        "verification_date": str(date.today()),
        "video_path": "/storage/videos/test.mp4",
        "file_name": "test.mp4",
        "mime_type": "video/mp4",
        "file_size": 1024000,
    }
    response = client.post("/video-verifications", json=payload, headers=get_auth_headers(1))
    assert response.status_code == 400
    assert "must be verified" in response.json()["detail"]


def test_07_create_video_with_pending_face_verification_status():
    """7. face_verification_id has status PENDING -> HTTP 400"""
    payload = {
        "medicine_schedule_id": 1,
        "face_verification_id": 3,  # Status: PENDING
        "verification_date": str(date.today()),
        "video_path": "/storage/videos/test.mp4",
        "file_name": "test.mp4",
        "mime_type": "video/mp4",
        "file_size": 1024000,
    }
    response = client.post("/video-verifications", json=payload, headers=get_auth_headers(1))
    assert response.status_code == 400
    assert "must be verified" in response.json()["detail"]


def test_08_database_persistence_and_response_schema():
    """8, 9, 10. Persistence in DB, response schema, and existing fields unchanged"""
    payload = {
        "medicine_schedule_id": 1,
        "face_verification_id": 1,
        "verification_date": str(date.today()),
        "video_path": "/storage/videos/audit_test.mp4",
        "file_name": "audit_test.mp4",
        "mime_type": "video/mp4",
        "file_size": 2048000,
        "thumbnail_path": "/storage/thumbnails/audit_test.jpg",
    }
    response = client.post("/video-verifications", json=payload, headers=get_auth_headers(1))
    assert response.status_code == 200
    data = response.json()

    assert data["id"] > 0
    assert data["medicine_schedule_id"] == 1
    assert data["face_verification_id"] == 1
    assert data["video_path"] == "/storage/videos/audit_test.mp4"
    assert data["file_name"] == "audit_test.mp4"
    assert data["mime_type"] == "video/mp4"
    assert data["file_size"] == 2048000
    assert data["thumbnail_path"] == "/storage/thumbnails/audit_test.jpg"
    assert data["status"] == "pending"

    # Verify directly from DB
    db = TestingSessionLocal()
    video_db = db.query(VideoVerification).filter(VideoVerification.id == data["id"]).first()
    assert video_db is not None
    assert video_db.face_verification_id == 1
    assert video_db.medicine_schedule_id == 1
    db.close()
