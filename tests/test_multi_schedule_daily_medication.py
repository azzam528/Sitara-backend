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
os.environ["SECRET_KEY"] = "testsecretkeyformultischedule"
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


def _add_schedule(db, treatment_id: int, medicine: Medicine, drink_time: time):
    schedule = MedicineSchedule(
        treatment_id=treatment_id,
        medicine_id=medicine.id,
        dosage="1 tablet",
        quantity_initial=30,
        quantity_remaining=30,
        drink_time=drink_time,
        is_active=True,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def _relative_times():
    now = datetime.now(JAKARTA).replace(second=0, microsecond=0)
    today = now.date()
    overdue_dt = now - timedelta(hours=2)
    upcoming_dt = now + timedelta(hours=2)
    overdue = time(0, 0) if overdue_dt.date() < today else overdue_dt.time()
    due = now.time()
    if upcoming_dt.date() > today:
        upcoming = time(23, 59) if now.time() < time(23, 59) else None
    else:
        upcoming = upcoming_dt.time()
    return overdue, due, upcoming


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(
        name="Puskesmas Multi VOT",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    user = User(
        username="patient_multi",
        email="patient_multi@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    patient = Patient(
        user_id=user.id,
        medical_record_number="MRN-MULTI-001",
        full_name="Pasien Multi",
        nik="3201010000000601",
        birth_date=datetime(1990, 1, 1).date(),
        gender="male",
        phone="08111111111",
        address="Alamat A",
        occupation="Wiraswasta",
        pmo_name="PMO A",
        pmo_phone="08111111112",
        is_active=True,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    today = today_jakarta()
    treatment = Treatment(
        patient_id=patient.id,
        diagnosis_date=today,
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

    med_a = Medicine(
        code="OAT-A",
        name="Obat A",
        category="OAT",
        strength="150mg",
        unit="tablet",
        is_active=True,
    )
    med_b = Medicine(
        code="OAT-B",
        name="Obat B",
        category="OAT",
        strength="300mg",
        unit="tablet",
        is_active=True,
    )
    med_c = Medicine(
        code="OAT-C",
        name="Obat C",
        category="OAT",
        strength="400mg",
        unit="tablet",
        is_active=True,
    )
    db.add_all([med_a, med_b, med_c])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _treatment_and_medicines():
    db = TestingSessionLocal()
    treatment = db.query(Treatment).one()
    medicines = {
        medicine.name: medicine
        for medicine in db.query(Medicine).all()
    }
    treatment_id = treatment.id
    db.close()
    return treatment_id, medicines


def _seed_schedules(*pairs: tuple[str, time]):
    treatment_id, medicines = _treatment_and_medicines()
    db = TestingSessionLocal()
    treatment = db.query(Treatment).filter(Treatment.id == treatment_id).one()
    created = []
    for name, drink_time in pairs:
        medicine = db.query(Medicine).filter(Medicine.id == medicines[name].id).one()
        created.append(_add_schedule(db, treatment.id, medicine, drink_time))
    ids = [schedule.id for schedule in created]
    db.close()
    return ids


def test_one_schedule_creates_one_daily_medication():
    _seed_schedules(("Obat A", time(9, 48)))
    response = client.get("/medications/today", headers=_headers("patient_multi"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["medicine_name"] == "Obat A"
    assert body[0]["scheduled_time"] == "09:48:00"
    assert body[0]["scheduled_date"] == today_jakarta().isoformat()

    db = TestingSessionLocal()
    assert db.query(func.count(DailyMedication.id)).scalar() == 1
    db.close()


def test_two_schedules_create_two_daily_medications():
    _seed_schedules(("Obat A", time(9, 48)), ("Obat B", time(13, 0)))
    response = client.get("/medications/today", headers=_headers("patient_multi"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert [item["medicine_name"] for item in body] == ["Obat A", "Obat B"]
    assert body[0]["daily_medication_id"] != body[1]["daily_medication_id"]
    assert body[0]["medicine_schedule_id"] != body[1]["medicine_schedule_id"]
    assert body[0]["scheduled_time"] == "09:48:00"
    assert body[1]["scheduled_time"] == "13:00:00"

    db = TestingSessionLocal()
    assert db.query(func.count(DailyMedication.id)).scalar() == 2
    db.close()


def test_three_schedules_create_three_daily_medications_ordered_by_time():
    _seed_schedules(
        ("Obat C", time(18, 0)),
        ("Obat A", time(9, 48)),
        ("Obat B", time(13, 0)),
    )
    response = client.get("/medications/today", headers=_headers("patient_multi"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert [item["medicine_name"] for item in body] == ["Obat A", "Obat B", "Obat C"]
    assert [item["scheduled_time"] for item in body] == [
        "09:48:00",
        "13:00:00",
        "18:00:00",
    ]
    ids = {item["daily_medication_id"] for item in body}
    schedule_ids = {item["medicine_schedule_id"] for item in body}
    assert len(ids) == 3
    assert len(schedule_ids) == 3


def test_upcoming_due_and_overdue_eligibility():
    overdue, due, upcoming = _relative_times()
    pairs = [("Obat A", overdue), ("Obat B", due)]
    if upcoming is not None:
        pairs.append(("Obat C", upcoming))
    _seed_schedules(*pairs)

    response = client.get("/medications/today", headers=_headers("patient_multi"))
    assert response.status_code == 200
    by_name = {item["medicine_name"]: item for item in response.json()}

    assert by_name["Obat A"]["eligible"] is True
    assert by_name["Obat A"]["status"] == "pending"
    assert by_name["Obat B"]["eligible"] is True
    assert by_name["Obat B"]["status"] == "pending"
    if upcoming is not None:
        assert by_name["Obat C"]["eligible"] is False
        assert by_name["Obat C"]["status"] == "pending"
        assert "Obat C" in by_name


def test_verified_schedule_cannot_be_started_again():
    overdue, due, _upcoming = _relative_times()
    schedule_ids = _seed_schedules(("Obat A", overdue), ("Obat B", due))
    client.get("/medications/today", headers=_headers("patient_multi"))

    db = TestingSessionLocal()
    occurrence_a = (
        db.query(DailyMedication)
        .filter(DailyMedication.medicine_schedule_id == schedule_ids[0])
        .one()
    )
    occurrence_a.status = DailyMedicationStatus.VERIFIED
    occurrence_a.vot_step = VotStep.VERIFIED
    db.commit()
    db.close()

    today = client.get("/medications/today", headers=_headers("patient_multi"))
    by_name = {item["medicine_name"]: item for item in today.json()}
    assert by_name["Obat A"]["status"] == "verified"
    assert by_name["Obat A"]["vot_step"] == "verified"
    assert by_name["Obat A"]["eligible"] is False
    assert by_name["Obat B"]["status"] == "pending"
    assert by_name["Obat B"]["eligible"] is True

    blocked = client.post(
        "/vot/start",
        json={"medicine_schedule_id": schedule_ids[0]},
        headers=_headers("patient_multi"),
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == (
        "VOT untuk jadwal obat ini hari ini sudah selesai."
    )


def test_verified_schedule_a_does_not_block_start_of_schedule_b():
    overdue, due, _upcoming = _relative_times()
    schedule_ids = _seed_schedules(("Obat A", overdue), ("Obat B", due))
    listed = client.get("/medications/today", headers=_headers("patient_multi"))
    assert listed.status_code == 200

    db = TestingSessionLocal()
    occurrence_a = (
        db.query(DailyMedication)
        .filter(DailyMedication.medicine_schedule_id == schedule_ids[0])
        .one()
    )
    occurrence_a.status = DailyMedicationStatus.VERIFIED
    occurrence_a.vot_step = VotStep.VERIFIED
    db.commit()
    daily_a = occurrence_a.id
    db.close()

    started_b = client.post(
        "/vot/start",
        json={"medicine_schedule_id": schedule_ids[1]},
        headers=_headers("patient_multi"),
    )
    assert started_b.status_code == 200
    body = started_b.json()
    assert body["medicine_schedule_id"] == schedule_ids[1]
    assert body["daily_medication_id"] != daily_a
    assert body["status"] == "in_progress"
    assert body["vot_step"] == "waiting"

    db = TestingSessionLocal()
    assert db.query(func.count(DailyMedication.id)).scalar() == 2
    db.close()


def test_today_response_keeps_existing_identity_fields():
    _seed_schedules(("Obat A", time(9, 48)))
    response = client.get("/medications/today", headers=_headers("patient_multi"))
    assert response.status_code == 200
    item = response.json()[0]
    for field in (
        "daily_medication_id",
        "medicine_schedule_id",
        "scheduled_time",
        "status",
        "vot_step",
        "medicine_id",
        "medicine_name",
        "dosage",
        "scheduled_date",
        "quantity_remaining",
    ):
        assert field in item
