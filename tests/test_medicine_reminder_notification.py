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
os.environ["SECRET_KEY"] = "testsecretkeyformedicinereminder"
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
from app.models.notification import (
    Notification,
    NotificationType,
    NotificationReferenceType,
)
from app.models import (  # noqa: F401
    VideoVerification,
    Complaint,
    RefillRequest,
    ControlSchedule,
    ActivationToken,
    FaceEmbedding,
    FaceVerification,
    DailyMedication,
)
from app.services.medicine_reminder_service import MedicineReminderService
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

reminder_service = MedicineReminderService()


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


def _at(hour: int, minute: int) -> datetime:
    today = datetime.now(JAKARTA).date()
    return datetime(today.year, today.month, today.day, hour, minute, tzinfo=JAKARTA)


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(
        name="Puskesmas Reminder",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    user_a = User(
        username="patient_a",
        email="patient_a_reminder@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    user_b = User(
        username="patient_b",
        email="patient_b_reminder@sitara.test",
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
        medical_record_number="MRN-REM-001",
        full_name="Pasien A",
        nik="3201010000000701",
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
        medical_record_number="MRN-REM-002",
        full_name="Pasien B",
        nik="3201010000000702",
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
        code="RIF-R",
        name="Rifampicin",
        category="OAT",
        strength="150mg",
        unit="tablet",
        is_active=True,
    )
    db.add(medicine)
    db.commit()
    db.refresh(medicine)

    today = datetime.now(JAKARTA).date()
    treatment_a = Treatment(
        patient_id=patient_a.id,
        diagnosis_date=today,
        therapy_start_date=today - timedelta(days=10),
        therapy_end_date=today + timedelta(days=10),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="Dokter Uji",
        is_active=True,
    )
    treatment_b = Treatment(
        patient_id=patient_b.id,
        diagnosis_date=today,
        therapy_start_date=today - timedelta(days=10),
        therapy_end_date=today + timedelta(days=10),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="Dokter Uji",
        is_active=True,
    )
    db.add_all([treatment_a, treatment_b])
    db.commit()
    db.refresh(treatment_a)
    db.refresh(treatment_b)

    schedule_morning = MedicineSchedule(
        treatment_id=treatment_a.id,
        medicine_id=medicine.id,
        dosage="1 tablet",
        quantity_initial=30,
        quantity_remaining=30,
        drink_time=time(12, 35),
        is_active=True,
    )
    schedule_evening = MedicineSchedule(
        treatment_id=treatment_a.id,
        medicine_id=medicine.id,
        dosage="1 tablet",
        quantity_initial=30,
        quantity_remaining=30,
        drink_time=time(18, 0),
        is_active=True,
    )
    schedule_b = MedicineSchedule(
        treatment_id=treatment_b.id,
        medicine_id=medicine.id,
        dosage="1 tablet",
        quantity_initial=30,
        quantity_remaining=30,
        drink_time=time(12, 35),
        is_active=True,
    )
    db.add_all([schedule_morning, schedule_evening, schedule_b])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _dispatch(now: datetime):
    db = TestingSessionLocal()
    created = reminder_service.dispatch_due_reminders(db, now=now)
    snapshots = [
        {
            "user_id": item.user_id,
            "type": item.type,
            "message": item.message,
            "reference_id": item.reference_id,
            "reference_type": item.reference_type,
            "created_at": item.created_at,
        }
        for item in created
    ]
    db.close()
    return snapshots


def _schedule_id(username: str, drink_time: time) -> int:
    db = TestingSessionLocal()
    schedule = (
        db.query(MedicineSchedule)
        .join(Treatment, Treatment.id == MedicineSchedule.treatment_id)
        .join(Patient, Patient.id == Treatment.patient_id)
        .join(User, User.id == Patient.user_id)
        .filter(
            User.username == username,
            MedicineSchedule.drink_time == drink_time,
        )
        .one()
    )
    schedule_id = schedule.id
    db.close()
    return schedule_id


def test_active_patient_gets_medicine_reminder_at_drink_time():
    created = _dispatch(_at(12, 35))
    assert len(created) >= 1

    patient_a_id = _user_id("patient_a")
    schedule_id = _schedule_id("patient_a", time(12, 35))
    own = [item for item in created if item["user_id"] == patient_a_id]
    assert len(own) == 1
    reminder = own[0]
    assert reminder["type"] == NotificationType.MEDICINE
    assert reminder["message"] == "Sudah waktunya minum obat."
    assert reminder["reference_id"] == schedule_id
    assert reminder["reference_type"] == NotificationReferenceType.MEDICINE_SCHEDULE
    assert reminder["user_id"] == patient_a_id


def test_reminder_does_not_go_to_other_patient():
    _dispatch(_at(12, 35))
    patient_a_id = _user_id("patient_a")
    patient_b_id = _user_id("patient_b")

    db = TestingSessionLocal()
    a_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == patient_a_id,
            Notification.type == NotificationType.MEDICINE,
            Notification.reference_id == _schedule_id("patient_a", time(12, 35)),
        )
        .count()
    )
    b_wrong = (
        db.query(Notification)
        .filter(
            Notification.user_id == patient_b_id,
            Notification.reference_id == _schedule_id("patient_a", time(12, 35)),
        )
        .count()
    )
    db.close()
    assert a_count == 1
    assert b_wrong == 0


def test_duplicate_reminder_not_created_after_drink_time():
    _dispatch(_at(12, 35))
    _dispatch(_at(12, 36))
    _dispatch(_at(13, 0))

    db = TestingSessionLocal()
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == _user_id("patient_a"),
            Notification.type == NotificationType.MEDICINE,
            Notification.reference_id == _schedule_id("patient_a", time(12, 35)),
        )
        .count()
    )
    db.close()
    assert count == 1


def test_inactive_patient_does_not_receive_reminder():
    db = TestingSessionLocal()
    patient = (
        db.query(Patient)
        .join(User, User.id == Patient.user_id)
        .filter(User.username == "patient_a")
        .one()
    )
    patient.is_active = False
    db.commit()
    db.close()

    created = _dispatch(_at(12, 35))
    assert all(item["user_id"] != _user_id("patient_a") for item in created)


def test_inactive_user_does_not_receive_reminder():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "patient_a").one()
    user.is_active = False
    db.commit()
    db.close()

    created = _dispatch(_at(12, 35))
    assert all(item["user_id"] != _user_id("patient_a") for item in created)


def test_inactive_schedule_does_not_receive_reminder():
    db = TestingSessionLocal()
    schedule = (
        db.query(MedicineSchedule)
        .filter(MedicineSchedule.id == _schedule_id("patient_a", time(12, 35)))
        .one()
    )
    schedule.is_active = False
    db.commit()
    db.close()

    _dispatch(_at(12, 35))
    db = TestingSessionLocal()
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == _user_id("patient_a"),
            Notification.type == NotificationType.MEDICINE,
            Notification.reference_id == _schedule_id("patient_a", time(12, 35)),
        )
        .count()
    )
    db.close()
    assert count == 0


def test_multiple_schedules_create_separate_reminders():
    created = _dispatch(_at(18, 0))
    patient_a_id = _user_id("patient_a")
    own = [item for item in created if item["user_id"] == patient_a_id]
    assert len(own) == 2
    reference_ids = {item["reference_id"] for item in own}
    assert reference_ids == {
        _schedule_id("patient_a", time(12, 35)),
        _schedule_id("patient_a", time(18, 0)),
    }


def test_evening_schedule_not_reminded_at_morning_time():
    _dispatch(_at(12, 35))
    db = TestingSessionLocal()
    evening_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == _user_id("patient_a"),
            Notification.reference_id == _schedule_id("patient_a", time(18, 0)),
        )
        .count()
    )
    db.close()
    assert evening_count == 0


def test_jakarta_timezone_does_not_shift_drink_time():
    created_too_early = _dispatch(_at(5, 35))
    patient_a_id = _user_id("patient_a")
    morning_id = _schedule_id("patient_a", time(12, 35))
    assert not any(
        item["user_id"] == patient_a_id and item["reference_id"] == morning_id
        for item in created_too_early
    )

    created_on_time = _dispatch(_at(12, 35))
    assert any(
        item["user_id"] == patient_a_id and item["reference_id"] == morning_id
        for item in created_on_time
    )

    created_wrong_offset = _dispatch(_at(19, 35))
    db = TestingSessionLocal()
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == patient_a_id,
            Notification.type == NotificationType.MEDICINE,
            Notification.reference_id == morning_id,
        )
        .count()
    )
    db.close()
    assert count == 1
    assert created_wrong_offset is not None


def test_created_at_is_event_time_utc_not_relative_text():
    before = datetime.utcnow()
    created = _dispatch(_at(12, 35))
    after = datetime.utcnow()
    patient_a_id = _user_id("patient_a")
    reminder = next(item for item in created if item["user_id"] == patient_a_id)
    assert isinstance(reminder["created_at"], datetime)
    assert before - timedelta(seconds=2) <= reminder["created_at"] <= after + timedelta(seconds=2)


def test_get_notifications_returns_timestamp_and_medicine_type():
    _dispatch(_at(12, 35))
    response = client.get("/notifications", headers=_headers("patient_a"))
    assert response.status_code == 200
    body = response.json()
    medicine_items = [item for item in body if item["type"] == "medicine"]
    assert len(medicine_items) == 1
    item = medicine_items[0]
    assert item["message"] == "Sudah waktunya minum obat."
    assert item["reference_id"] == _schedule_id("patient_a", time(12, 35))
    assert item["is_read"] is False
    assert "created_at" in item
    assert item["created_at"]
    parsed = datetime.fromisoformat(item["created_at"])
    assert parsed.tzinfo is None or parsed.utcoffset() == timedelta(0)
