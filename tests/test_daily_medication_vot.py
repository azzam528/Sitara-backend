import os
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyfordailymedication"
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
from app.models.daily_medication import DailyMedication
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


def _add_treatment_and_schedule(
    db,
    patient_id: int,
    medicine: Medicine,
    *,
    start_offset_days: int = -10,
    end_offset_days: int = 10,
    schedule_active: bool = True,
    dosage: str = "1 tablet",
    drink_time: time = time(20, 0),
    quantity: int = 30,
):
    today = today_jakarta()
    treatment = Treatment(
        patient_id=patient_id,
        diagnosis_date=today + timedelta(days=start_offset_days),
        therapy_start_date=today + timedelta(days=start_offset_days),
        therapy_end_date=today + timedelta(days=end_offset_days),
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
        dosage=dosage,
        quantity_initial=quantity,
        quantity_remaining=quantity,
        drink_time=drink_time,
        is_active=schedule_active,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return treatment, schedule


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(
        name="Puskesmas VOT",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    user_a = User(
        username="patient_a",
        email="patient_a@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    user_b = User(
        username="patient_b",
        email="patient_b@sitara.test",
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
        medical_record_number="MRN-VOT-001",
        full_name="Pasien A",
        nik="3201010000000101",
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
        medical_record_number="MRN-VOT-002",
        full_name="Pasien B",
        nik="3201010000000102",
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

    medicine_a = Medicine(
        code="PROM-1",
        name="Promag",
        category="OAT",
        strength="1 tablet",
        unit="tablet",
        is_active=True,
    )
    medicine_b = Medicine(
        code="PARA-1",
        name="Paracetamol",
        category="OAT",
        strength="500mg",
        unit="tablet",
        is_active=True,
    )
    db.add_all([medicine_a, medicine_b])
    db.commit()
    db.refresh(medicine_a)
    db.refresh(medicine_b)

    _add_treatment_and_schedule(db, patient_a.id, medicine_a)
    _add_treatment_and_schedule(db, patient_b.id, medicine_b)

    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _patient_a_headers():
    return _auth_headers(_user_id("patient_a"))


def _patient_b_headers():
    return _auth_headers(_user_id("patient_b"))


def _schedule_id_for_patient(username: str) -> int:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == username).one()
    schedule = (
        db.query(MedicineSchedule)
        .join(Treatment, Treatment.id == MedicineSchedule.treatment_id)
        .join(Patient, Patient.id == Treatment.patient_id)
        .filter(Patient.user_id == user.id, MedicineSchedule.is_active.is_(True))
        .first()
    )
    schedule_id = schedule.id
    db.close()
    return schedule_id


def test_today_creates_pending_daily_medication():
    response = client.get("/medications/today", headers=_patient_a_headers())
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    item = body[0]
    assert item["medicine_name"] == "Promag"
    assert item["dosage"] == "1 tablet"
    assert item["quantity_remaining"] == 30
    assert item["status"] == "pending"
    assert item["vot_step"] == "waiting"
    assert item["scheduled_date"] == today_jakarta().isoformat()
    assert item["scheduled_time"] == "20:00:00"
    assert item["medicine_schedule_id"] == _schedule_id_for_patient("patient_a")
    assert item["daily_medication_id"] > 0
    assert "medicine_id" in item

    db = TestingSessionLocal()
    count = db.query(func.count(DailyMedication.id)).scalar()
    db.close()
    assert count == 1


def test_today_second_call_does_not_duplicate():
    first = client.get("/medications/today", headers=_patient_a_headers())
    second = client.get("/medications/today", headers=_patient_a_headers())
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()[0]["daily_medication_id"] == second.json()[0]["daily_medication_id"]

    db = TestingSessionLocal()
    count = (
        db.query(func.count(DailyMedication.id))
        .filter(
            DailyMedication.medicine_schedule_id
            == first.json()[0]["medicine_schedule_id"],
            DailyMedication.scheduled_date == today_jakarta(),
        )
        .scalar()
    )
    db.close()
    assert count == 1


def test_vot_start_changes_pending_to_in_progress():
    today = client.get("/medications/today", headers=_patient_a_headers())
    schedule_id = today.json()[0]["medicine_schedule_id"]
    daily_id = today.json()[0]["daily_medication_id"]

    started = client.post(
        "/vot/start",
        json={"medicine_schedule_id": schedule_id},
        headers=_patient_a_headers(),
    )
    assert started.status_code == 200
    body = started.json()
    assert body["daily_medication_id"] == daily_id
    assert body["status"] == "in_progress"
    assert body["vot_step"] == "waiting"
    assert body["medicine_schedule_id"] == schedule_id
    assert "scheduled_date" in body
    assert "scheduled_time" in body


def test_vot_start_second_call_returns_same_occurrence():
    schedule_id = _schedule_id_for_patient("patient_a")
    first = client.post(
        "/vot/start",
        json={"medicine_schedule_id": schedule_id},
        headers=_patient_a_headers(),
    )
    second = client.post(
        "/vot/start",
        json={"medicine_schedule_id": schedule_id},
        headers=_patient_a_headers(),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["daily_medication_id"] == second.json()["daily_medication_id"]
    assert second.json()["status"] == "in_progress"

    db = TestingSessionLocal()
    count = db.query(func.count(DailyMedication.id)).scalar()
    db.close()
    assert count == 1


def test_patient_cannot_access_other_patient_daily_medication():
    created = client.get("/medications/today", headers=_patient_a_headers())
    daily_id = created.json()[0]["daily_medication_id"]

    response = client.get(f"/vot/{daily_id}", headers=_patient_b_headers())
    assert response.status_code == 404


def test_patient_cannot_start_vot_for_other_patient_schedule():
    schedule_a = _schedule_id_for_patient("patient_a")
    response = client.post(
        "/vot/start",
        json={"medicine_schedule_id": schedule_a},
        headers=_patient_b_headers(),
    )
    assert response.status_code == 403


def test_schedule_outside_therapy_window_not_listed():
    db = TestingSessionLocal()
    user_a = db.query(User).filter(User.username == "patient_a").one()
    patient_a = db.query(Patient).filter(Patient.user_id == user_a.id).one()
    future_medicine = Medicine(
        code="FUT-1",
        name="FutureMed",
        category="OAT",
        strength="1 tablet",
        unit="tablet",
        is_active=True,
    )
    db.add(future_medicine)
    db.commit()
    db.refresh(future_medicine)
    _add_treatment_and_schedule(
        db,
        patient_a.id,
        future_medicine,
        start_offset_days=2,
        end_offset_days=30,
    )
    db.close()

    response = client.get("/medications/today", headers=_patient_a_headers())
    assert response.status_code == 200
    names = [item["medicine_name"] for item in response.json()]
    assert names == ["Promag"]
    assert "FutureMed" not in names


def test_inactive_schedule_not_listed():
    db = TestingSessionLocal()
    user_a = db.query(User).filter(User.username == "patient_a").one()
    patient_a = db.query(Patient).filter(Patient.user_id == user_a.id).one()
    inactive_med = Medicine(
        code="INA-S",
        name="InactiveScheduleMed",
        category="OAT",
        strength="1 tablet",
        unit="tablet",
        is_active=True,
    )
    db.add(inactive_med)
    db.commit()
    db.refresh(inactive_med)
    _add_treatment_and_schedule(
        db,
        patient_a.id,
        inactive_med,
        schedule_active=False,
    )
    db.close()

    response = client.get("/medications/today", headers=_patient_a_headers())
    names = [item["medicine_name"] for item in response.json()]
    assert "InactiveScheduleMed" not in names
    assert names == ["Promag"]


def test_inactive_medicine_not_listed():
    db = TestingSessionLocal()
    user_a = db.query(User).filter(User.username == "patient_a").one()
    patient_a = db.query(Patient).filter(Patient.user_id == user_a.id).one()
    inactive_med = Medicine(
        code="INA-M",
        name="InactiveMedicine",
        category="OAT",
        strength="1 tablet",
        unit="tablet",
        is_active=False,
    )
    db.add(inactive_med)
    db.commit()
    db.refresh(inactive_med)
    _add_treatment_and_schedule(db, patient_a.id, inactive_med)
    db.close()

    response = client.get("/medications/today", headers=_patient_a_headers())
    names = [item["medicine_name"] for item in response.json()]
    assert "InactiveMedicine" not in names
    assert names == ["Promag"]


def test_get_vot_session_returns_progress_for_owner():
    started = client.post(
        "/vot/start",
        json={"medicine_schedule_id": _schedule_id_for_patient("patient_a")},
        headers=_patient_a_headers(),
    )
    daily_id = started.json()["daily_medication_id"]
    response = client.get(f"/vot/{daily_id}", headers=_patient_a_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["daily_medication_id"] == daily_id
    assert body["status"] == "in_progress"
    assert body["vot_step"] == "waiting"
    assert body["medicine_name"] == "Promag"
