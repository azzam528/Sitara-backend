import json
import os
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforvotfaceverify"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:5173"
os.environ["ACTIVATION_BASE_URL"] = "https://activation.test.local"

from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.patient import Patient
from app.models.health_facility import HealthFacility
from app.models.treatment import (
    Treatment,
    TreatmentPhase,
    TreatmentStatus,
    RegimenEnum,
)
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.daily_medication import (
    DailyMedication,
    DailyMedicationStatus,
    VotStep,
)
from app.models.face_embedding import FaceEmbedding
from app.models.face_verification import FaceVerification
from app.models import (  # noqa: F401
    VideoVerification,
    Complaint,
    RefillRequest,
    ControlSchedule,
    Notification,
    ActivationToken,
)
from app.services.face_recognition_service import FaceRecognitionService
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
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


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

JAKARTA = timezone(timedelta(hours=7))
try:
    JAKARTA = ZoneInfo("Asia/Jakarta")
except ZoneInfoNotFoundError:
    JAKARTA = timezone(timedelta(hours=7))

FACE_VECTOR = [0.1] * 128


def today_jakarta():
    return datetime.now(JAKARTA).date()


def create_test_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "role": "patient",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _auth_headers(user_id: int) -> dict:
    return {"Authorization": f"Bearer {create_test_token(user_id)}"}


def _user_id(username: str) -> int:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == username).one()
    user_id = user.id
    db.close()
    return user_id


def _patient_a_headers():
    return _auth_headers(_user_id("patient_a"))


def _patient_b_headers():
    return _auth_headers(_user_id("patient_b"))


def _install_face_score(monkeypatch, score: float):
    monkeypatch.setattr(
        FaceRecognitionService,
        "decode_image",
        lambda self, file_bytes: np.zeros((200, 200, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(
        FaceRecognitionService,
        "detect_single_face",
        lambda self, img: np.array([10.0, 10.0, 80.0, 80.0, 0.99]),
    )
    monkeypatch.setattr(
        FaceRecognitionService,
        "extract_embedding",
        lambda self, img, face: FACE_VECTOR,
    )
    monkeypatch.setattr(
        FaceRecognitionService,
        "calculate_similarity",
        lambda self, emb1, emb2: score,
    )


def _seed_embedding(username: str = "patient_a"):
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == username).one()
    patient = db.query(Patient).filter(Patient.user_id == user.id).one()
    db.add(
        FaceEmbedding(
            patient_id=patient.id,
            embedding=json.dumps(FACE_VECTOR),
            model_version=settings.FACE_MODEL_VERSION,
            is_active=True,
        )
    )
    db.commit()
    db.close()


def _set_occurrence_status(daily_id: int, status: DailyMedicationStatus, vot_step: VotStep):
    db = TestingSessionLocal()
    occurrence = db.query(DailyMedication).filter(DailyMedication.id == daily_id).one()
    occurrence.status = status
    occurrence.vot_step = vot_step
    db.commit()
    db.close()


def _start_vot_for_a():
    db = TestingSessionLocal()
    schedule = (
        db.query(MedicineSchedule)
        .join(Treatment)
        .join(Patient)
        .join(User, Patient.user_id == User.id)
        .filter(User.username == "patient_a")
        .first()
    )
    schedule_id = schedule.id
    db.close()
    started = client.post(
        "/vot/start",
        json={"medicine_schedule_id": schedule_id},
        headers=_patient_a_headers(),
    )
    assert started.status_code == 200
    return started.json()


def _face_verify(daily_id: int, headers=None):
    return client.post(
        "/vot/face-verify",
        headers=headers or _patient_a_headers(),
        data={"daily_medication_id": str(daily_id)},
        files={"image": ("face.jpg", b"fake-image", "image/jpeg")},
    )


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(
        name="Puskesmas VOT Face",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    user_a = User(
        username="patient_a",
        email="patient_a_vot_face@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    user_b = User(
        username="patient_b",
        email="patient_b_vot_face@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    patient_a = Patient(
        user_id=user_a.id,
        medical_record_number="MRN-VOTF-001",
        full_name="Pasien A",
        nik="3201010000000201",
        birth_date=datetime(1990, 1, 1).date(),
        gender="male",
        phone="08111111111",
        address="Alamat A",
        occupation="Wiraswasta",
        pmo_name="PMO A",
        pmo_phone="08111111112",
        is_active=True,
    )
    patient_b = Patient(
        user_id=user_b.id,
        medical_record_number="MRN-VOTF-002",
        full_name="Pasien B",
        nik="3201010000000202",
        birth_date=datetime(1995, 5, 5).date(),
        gender="female",
        phone="08222222222",
        address="Alamat B",
        occupation="Guru",
        pmo_name="PMO B",
        pmo_phone="08222222223",
        is_active=True,
    )
    db.add_all([patient_a, patient_b])
    db.commit()
    db.refresh(patient_a)
    db.refresh(patient_b)

    medicine = Medicine(
        code="PROM-VF",
        name="Promag",
        category="OAT",
        strength="1 tablet",
        unit="tablet",
        is_active=True,
    )
    db.add(medicine)
    db.commit()
    db.refresh(medicine)

    today = today_jakarta()
    for patient in (patient_a, patient_b):
        treatment = Treatment(
            patient_id=patient.id,
            diagnosis_date=today - timedelta(days=10),
            therapy_start_date=today - timedelta(days=10),
            therapy_end_date=today + timedelta(days=10),
            phase=TreatmentPhase.INTENSIVE,
            regimen=RegimenEnum.CATEGORY_1,
            status=TreatmentStatus.ACTIVE,
            doctor_name="Dokter Uji",
            is_active=True,
        )
        db.add(treatment)
        db.commit()
        db.refresh(treatment)
        db.add(
            MedicineSchedule(
                treatment_id=treatment.id,
                medicine_id=medicine.id,
                dosage="1 tablet",
                quantity_initial=30,
                quantity_remaining=30,
                drink_time=time(20, 0),
                is_active=True,
            )
        )
        db.commit()

    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def test_owner_can_verify_face_and_advance_vot_step(monkeypatch):
    _install_face_score(monkeypatch, 0.87)
    _seed_embedding()
    started = _start_vot_for_a()
    daily_id = started["daily_medication_id"]

    response = _face_verify(daily_id)
    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is True
    assert body["status"] == "verified"
    assert body["vot_step"] == "face_verified"
    assert body["daily_medication_id"] == daily_id
    assert body["medicine_schedule_id"] == started["medicine_schedule_id"]
    assert body["face_verification_id"] > 0
    assert body["similarity_score"] >= 0.70
    assert body["threshold"] == 0.70

    db = TestingSessionLocal()
    occurrence = db.query(DailyMedication).filter(DailyMedication.id == daily_id).one()
    assert occurrence.status == DailyMedicationStatus.IN_PROGRESS
    assert occurrence.vot_step == VotStep.FACE_VERIFIED
    assert occurrence.face_verification_id == body["face_verification_id"]
    db.close()

    session = client.get(f"/vot/{daily_id}", headers=_patient_a_headers())
    assert session.status_code == 200
    assert session.json()["vot_step"] == "face_verified"
    assert session.json()["status"] == "in_progress"


def test_other_patient_cannot_face_verify_daily_medication(monkeypatch):
    _install_face_score(monkeypatch, 0.87)
    _seed_embedding()
    daily_id = _start_vot_for_a()["daily_medication_id"]

    response = _face_verify(daily_id, headers=_patient_b_headers())
    assert response.status_code == 404

    db = TestingSessionLocal()
    assert db.query(func.count(FaceVerification.id)).scalar() == 0
    db.close()


def test_pending_daily_medication_cannot_face_verify(monkeypatch):
    _install_face_score(monkeypatch, 0.87)
    _seed_embedding()
    today = client.get("/medications/today", headers=_patient_a_headers())
    daily_id = today.json()[0]["daily_medication_id"]

    response = _face_verify(daily_id)
    assert response.status_code == 400
    assert response.json()["detail"] == "VOT belum dimulai."

    db = TestingSessionLocal()
    occurrence = db.query(DailyMedication).filter(DailyMedication.id == daily_id).one()
    assert occurrence.vot_step == VotStep.WAITING
    assert db.query(func.count(FaceVerification.id)).scalar() == 0
    db.close()


def test_verified_daily_medication_cannot_face_verify(monkeypatch):
    _install_face_score(monkeypatch, 0.87)
    _seed_embedding()
    daily_id = _start_vot_for_a()["daily_medication_id"]
    _set_occurrence_status(
        daily_id,
        DailyMedicationStatus.VERIFIED,
        VotStep.VERIFIED,
    )

    response = _face_verify(daily_id)
    assert response.status_code == 400
    assert response.json()["detail"] == "VOT sudah selesai."
    db = TestingSessionLocal()
    assert db.query(func.count(FaceVerification.id)).scalar() == 0
    db.close()


def test_rejected_and_missed_cannot_face_verify(monkeypatch):
    _install_face_score(monkeypatch, 0.87)
    _seed_embedding()
    daily_id = _start_vot_for_a()["daily_medication_id"]

    _set_occurrence_status(
        daily_id,
        DailyMedicationStatus.REJECTED,
        VotStep.WAITING,
    )
    rejected = _face_verify(daily_id)
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "VOT tidak dapat dilanjutkan."

    _set_occurrence_status(
        daily_id,
        DailyMedicationStatus.MISSED,
        VotStep.WAITING,
    )
    missed = _face_verify(daily_id)
    assert missed.status_code == 400
    assert missed.json()["detail"] == "VOT tidak dapat dilanjutkan."

    db = TestingSessionLocal()
    assert db.query(func.count(FaceVerification.id)).scalar() == 0
    db.close()


def test_failed_face_keeps_waiting_step(monkeypatch):
    _install_face_score(monkeypatch, 0.20)
    _seed_embedding()
    daily_id = _start_vot_for_a()["daily_medication_id"]

    response = _face_verify(daily_id)
    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is False
    assert body["status"] == "failed"
    assert body["vot_step"] == "waiting"
    assert body["face_verification_id"] > 0

    db = TestingSessionLocal()
    occurrence = db.query(DailyMedication).filter(DailyMedication.id == daily_id).one()
    assert occurrence.status == DailyMedicationStatus.IN_PROGRESS
    assert occurrence.vot_step == VotStep.WAITING
    assert occurrence.face_verification_id is None
    assert db.query(func.count(FaceVerification.id)).scalar() == 1
    db.close()


def test_already_face_verified_does_not_move_back_or_duplicate(monkeypatch):
    _install_face_score(monkeypatch, 0.87)
    _seed_embedding()
    daily_id = _start_vot_for_a()["daily_medication_id"]

    first = _face_verify(daily_id)
    assert first.status_code == 200
    face_id = first.json()["face_verification_id"]

    second = _face_verify(daily_id)
    assert second.status_code == 400
    assert second.json()["detail"] == "Face verification sudah selesai."

    db = TestingSessionLocal()
    occurrence = db.query(DailyMedication).filter(DailyMedication.id == daily_id).one()
    assert occurrence.vot_step == VotStep.FACE_VERIFIED
    assert occurrence.status == DailyMedicationStatus.IN_PROGRESS
    assert occurrence.face_verification_id == face_id
    assert db.query(func.count(FaceVerification.id)).scalar() == 1
    db.close()
