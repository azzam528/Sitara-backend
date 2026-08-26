import os
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforvotmedicinedetect"
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
from app.models import (  # noqa: F401
    VideoVerification,
    Complaint,
    RefillRequest,
    ControlSchedule,
    Notification,
    ActivationToken,
    FaceEmbedding,
    FaceVerification,
)
from app.services.medicine_detection_service import medicine_detection_service
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

PROMAG_BOX = {"x": 120.0, "y": 80.0, "width": 200.0, "height": 250.0}


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


def _set_occurrence(daily_id: int, status: DailyMedicationStatus, vot_step: VotStep):
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


def _prepare_face_verified():
    started = _start_vot_for_a()
    daily_id = started["daily_medication_id"]
    _set_occurrence(
        daily_id,
        DailyMedicationStatus.IN_PROGRESS,
        VotStep.FACE_VERIFIED,
    )
    return started


def _detect(daily_id: int, headers=None, extra_data=None):
    data = {"daily_medication_id": str(daily_id)}
    if extra_data:
        data.update(extra_data)
    return client.post(
        "/vot/medicine-detect",
        headers=headers or _patient_a_headers(),
        data=data,
        files={"image": ("medicine.jpg", b"fake-image", "image/jpeg")},
    )


def _mock_detection(monkeypatch, *, detected, match, confidence=0.94, message=None):
    calls = []

    def fake_detect(image_bytes, expected_medicine):
        calls.append(
            {
                "image_bytes": image_bytes,
                "expected_medicine": expected_medicine,
            }
        )
        if detected is None:
            return {
                "status": "MEDICINE_NOT_DETECTED",
                "expected_medicine": expected_medicine,
                "detected_medicine": None,
                "confidence": 0.0,
                "bounding_box": None,
                "medicine_match": False,
                "message": "Obat belum terdeteksi.",
            }
        return {
            "status": "MEDICINE_MATCHED" if match else "MEDICINE_MISMATCH",
            "expected_medicine": expected_medicine,
            "detected_medicine": detected,
            "confidence": confidence,
            "bounding_box": PROMAG_BOX,
            "medicine_match": match,
            "message": message
            or (
                "Obat sesuai dengan jadwal."
                if match
                else "Obat yang terdeteksi tidak sesuai dengan jadwal obat."
            ),
        }

    monkeypatch.setattr(
        medicine_detection_service,
        "detect_expected_medicine",
        fake_detect,
    )
    return calls


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(
        name="Puskesmas VOT Med",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    user_a = User(
        username="patient_a",
        email="patient_a_vot_med@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    user_b = User(
        username="patient_b",
        email="patient_b_vot_med@sitara.test",
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
        medical_record_number="MRN-VOTM-001",
        full_name="Pasien A",
        nik="3201010000000301",
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
        medical_record_number="MRN-VOTM-002",
        full_name="Pasien B",
        nik="3201010000000302",
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
        code="PROM-VM",
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


def test_promag_match_advances_to_medicine_matched(monkeypatch):
    calls = _mock_detection(monkeypatch, detected="promag", match=True)
    started = _prepare_face_verified()
    daily_id = started["daily_medication_id"]

    response = _detect(daily_id)
    assert response.status_code == 200
    body = response.json()
    assert body["medicine_match"] is True
    assert body["expected_medicine"] == "Promag"
    assert body["detected_medicine"] == "promag"
    assert body["confidence"] == 0.94
    assert body["bounding_box"] == PROMAG_BOX
    assert body["status"] == "in_progress"
    assert body["vot_step"] == "medicine_matched"
    assert body["daily_medication_id"] == daily_id
    assert body["medicine_schedule_id"] == started["medicine_schedule_id"]
    assert calls[0]["expected_medicine"] == "Promag"

    db = TestingSessionLocal()
    occurrence = db.query(DailyMedication).filter(DailyMedication.id == daily_id).one()
    assert occurrence.status == DailyMedicationStatus.IN_PROGRESS
    assert occurrence.vot_step == VotStep.MEDICINE_MATCHED
    db.close()


def test_paracetamol_on_promag_schedule_is_mismatch(monkeypatch):
    _mock_detection(monkeypatch, detected="paracetamol", match=False, confidence=0.93)
    started = _prepare_face_verified()
    daily_id = started["daily_medication_id"]

    response = _detect(daily_id)
    assert response.status_code == 200
    body = response.json()
    assert body["medicine_match"] is False
    assert body["expected_medicine"] == "Promag"
    assert body["detected_medicine"] == "paracetamol"
    assert body["vot_step"] == "face_verified"
    assert body["status"] == "in_progress"

    db = TestingSessionLocal()
    occurrence = db.query(DailyMedication).filter(DailyMedication.id == daily_id).one()
    assert occurrence.vot_step == VotStep.FACE_VERIFIED
    assert occurrence.status == DailyMedicationStatus.IN_PROGRESS
    db.close()


def test_no_medicine_detected_stays_face_verified(monkeypatch):
    _mock_detection(monkeypatch, detected=None, match=False)
    daily_id = _prepare_face_verified()["daily_medication_id"]

    response = _detect(daily_id)
    assert response.status_code == 200
    body = response.json()
    assert body["detected_medicine"] is None
    assert body["medicine_match"] is False
    assert body["vot_step"] == "face_verified"
    assert body["message"] == "Obat belum terdeteksi."


def test_waiting_cannot_medicine_detect(monkeypatch):
    calls = _mock_detection(monkeypatch, detected="promag", match=True)
    daily_id = _start_vot_for_a()["daily_medication_id"]

    response = _detect(daily_id)
    assert response.status_code == 400
    assert response.json()["detail"] == "Face verification belum berhasil."
    assert calls == []


def test_pending_cannot_medicine_detect(monkeypatch):
    calls = _mock_detection(monkeypatch, detected="promag", match=True)
    today = client.get("/medications/today", headers=_patient_a_headers())
    daily_id = today.json()[0]["daily_medication_id"]

    response = _detect(daily_id)
    assert response.status_code == 400
    assert response.json()["detail"] == "VOT belum dimulai."
    assert calls == []


def test_verified_cannot_medicine_detect(monkeypatch):
    calls = _mock_detection(monkeypatch, detected="promag", match=True)
    daily_id = _start_vot_for_a()["daily_medication_id"]
    _set_occurrence(daily_id, DailyMedicationStatus.VERIFIED, VotStep.VERIFIED)

    response = _detect(daily_id)
    assert response.status_code == 400
    assert response.json()["detail"] == "VOT sudah selesai."
    assert calls == []


def test_other_patient_cannot_medicine_detect(monkeypatch):
    calls = _mock_detection(monkeypatch, detected="promag", match=True)
    daily_id = _prepare_face_verified()["daily_medication_id"]

    response = _detect(daily_id, headers=_patient_b_headers())
    assert response.status_code == 404
    assert calls == []


def test_client_cannot_override_expected_medicine(monkeypatch):
    calls = _mock_detection(monkeypatch, detected="promag", match=True)
    daily_id = _prepare_face_verified()["daily_medication_id"]

    response = _detect(
        daily_id,
        extra_data={"expected_medicine": "Paracetamol", "medicine_id": "999"},
    )
    assert response.status_code == 200
    assert response.json()["expected_medicine"] == "Promag"
    assert calls[0]["expected_medicine"] == "Promag"


def test_already_matched_does_not_rerun_detection(monkeypatch):
    calls = _mock_detection(monkeypatch, detected="promag", match=True)
    daily_id = _prepare_face_verified()["daily_medication_id"]
    first = _detect(daily_id)
    assert first.status_code == 200
    assert len(calls) == 1

    second = _detect(daily_id)
    assert second.status_code == 400
    assert second.json()["detail"] == "Medicine detection sudah selesai."
    assert len(calls) == 1

    db = TestingSessionLocal()
    occurrence = db.query(DailyMedication).filter(DailyMedication.id == daily_id).one()
    assert occurrence.vot_step == VotStep.MEDICINE_MATCHED
    db.close()
