import os
from datetime import date, datetime, time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforvotcompletenotify"
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
from app.models.notification import Notification, NotificationType
from app.models import (  # noqa: F401
    VideoVerification,
    Complaint,
    RefillRequest,
    ControlSchedule,
    ActivationToken,
    FaceEmbedding,
    FaceVerification,
)
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


def create_test_token(user_id: int, role: str = "patient") -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _headers(username: str) -> dict:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == username).one()
    token = create_test_token(user.id, user.role)
    db.close()
    return {"Authorization": f"Bearer {token}"}


def _user_id(username: str) -> int:
    db = TestingSessionLocal()
    user_id = db.query(User).filter(User.username == username).one().id
    db.close()
    return user_id


def _add_ready_occurrence(db, patient_id: int, medicine: Medicine) -> DailyMedication:
    today = date.today()
    treatment = Treatment(
        patient_id=patient_id,
        diagnosis_date=today,
        therapy_start_date=today,
        therapy_end_date=today + timedelta(days=30),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="Dokter Uji",
        is_active=True,
    )
    db.add(treatment)
    db.commit()
    db.refresh(treatment)

    schedule = MedicineSchedule(
        treatment_id=treatment.id,
        medicine_id=medicine.id,
        dosage="1 tablet",
        quantity_initial=30,
        quantity_remaining=30,
        drink_time=time(20, 0),
        is_active=True,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    occurrence = DailyMedication(
        medicine_schedule_id=schedule.id,
        scheduled_date=today,
        scheduled_time=time(20, 0),
        status=DailyMedicationStatus.IN_PROGRESS,
        vot_step=VotStep.MEDICINE_MATCHED,
        is_active=True,
    )
    db.add(occurrence)
    db.commit()
    db.refresh(occurrence)
    return occurrence


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(
        name="Puskesmas VOT Notify",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    user_a = User(
        username="patient_a",
        email="patient_a_votn@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    user_b = User(
        username="patient_b",
        email="patient_b_votn@sitara.test",
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
        medical_record_number="MRN-VOTN-001",
        full_name="Pasien A",
        nik="3201010000000401",
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
        medical_record_number="MRN-VOTN-002",
        full_name="Pasien B",
        nik="3201010000000402",
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
        code="INH-1",
        name="Isoniazid",
        category="OAT",
        strength="300mg",
        unit="tablet",
        is_active=True,
    )
    db.add(medicine)
    db.commit()
    db.refresh(medicine)

    _add_ready_occurrence(db, patient_a.id, medicine)
    _add_ready_occurrence(db, patient_b.id, medicine)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _occurrence_id(username: str) -> int:
    db = TestingSessionLocal()
    occurrence = (
        db.query(DailyMedication)
        .join(MedicineSchedule, MedicineSchedule.id == DailyMedication.medicine_schedule_id)
        .join(Treatment, Treatment.id == MedicineSchedule.treatment_id)
        .join(Patient, Patient.id == Treatment.patient_id)
        .join(User, User.id == Patient.user_id)
        .filter(User.username == username)
        .one()
    )
    occurrence_id = occurrence.id
    db.close()
    return occurrence_id


def test_successful_vot_complete_creates_notification_for_owner_only():
    daily_id = _occurrence_id("patient_a")
    response = client.post(
        "/vot/complete",
        json={"daily_medication_id": daily_id, "drinking_verified": True},
        headers=_headers("patient_a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "verified"
    assert body["vot_step"] == "verified"
    assert body["message"] == "Verifikasi minum obat berhasil."
    assert body["daily_medication_id"] == daily_id
    assert "completed_at" in body

    notifications_a = client.get("/notifications", headers=_headers("patient_a"))
    assert notifications_a.status_code == 200
    items = notifications_a.json()
    assert len(items) == 1
    assert items[0]["type"] == NotificationType.VIDEO.value
    assert items[0]["reference_id"] == daily_id
    assert items[0]["is_read"] is False
    assert items[0]["user_id"] == _user_id("patient_a")
    assert items[0]["message"] == "Verifikasi minum obat berhasil."

    notifications_b = client.get("/notifications", headers=_headers("patient_b"))
    assert notifications_b.status_code == 200
    assert notifications_b.json() == []


def test_failed_vot_complete_does_not_create_notification():
    daily_id = _occurrence_id("patient_a")
    response = client.post(
        "/vot/complete",
        json={"daily_medication_id": daily_id, "drinking_verified": False},
        headers=_headers("patient_a"),
    )
    assert response.status_code == 400

    notifications = client.get("/notifications", headers=_headers("patient_a"))
    assert notifications.status_code == 200
    assert notifications.json() == []

    db = TestingSessionLocal()
    occurrence = db.query(DailyMedication).filter(DailyMedication.id == daily_id).one()
    assert occurrence.status == DailyMedicationStatus.IN_PROGRESS
    db.close()


def test_duplicate_complete_does_not_create_second_notification():
    daily_id = _occurrence_id("patient_a")
    first = client.post(
        "/vot/complete",
        json={"daily_medication_id": daily_id, "drinking_verified": True},
        headers=_headers("patient_a"),
    )
    second = client.post(
        "/vot/complete",
        json={"daily_medication_id": daily_id, "drinking_verified": True},
        headers=_headers("patient_a"),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["message"] == "VOT sudah selesai."

    db = TestingSessionLocal()
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == _user_id("patient_a"),
            Notification.type == NotificationType.VIDEO,
            Notification.reference_id == daily_id,
        )
        .count()
    )
    db.close()
    assert count == 1
