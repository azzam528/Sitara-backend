import os
import sys
from datetime import date, time, timedelta, datetime
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.patient import Patient, GenderEnum
from app.models.treatment import Treatment, TreatmentPhase, TreatmentStatus, RegimenEnum
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.daily_medication import DailyMedication, DailyMedicationStatus, VotStep
from app.models.video_verification import VideoVerification, VerificationStatus
from app.models.complaint import Complaint
from app.core.security import create_access_token
from app.services.dashboard_service import today_in_jakarta, now_time_in_jakarta

# Use isolated in-memory SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_tables():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db: Session):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def nakes_headers(db: Session):
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"nakes_dash_{uid}",
        email=f"nakes_dash_{uid}@sitara.com",
        password_hash="fakehash",
        role="nakes",
        is_active=True,
    )
    db.add(user)
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def create_base_patient_and_schedule(db: Session, prefix: str = "d"):
    uid = uuid.uuid4().hex[:8]
    user_p = User(
        username=f"6289{uid}",
        email=f"p_{uid}@sitara.com",
        password_hash="fakehash",
        role="patient",
        is_active=True,
    )
    db.add(user_p)
    db.commit()

    patient = Patient(
        user_id=user_p.id,
        nik=f"32{uid[:14]}",
        medical_record_number=f"RM-{uid}",
        full_name=f"Pasien Dashboard {prefix}",
        phone=user_p.username,
        birth_date=date(1990, 1, 1),
        gender=GenderEnum.MALE,
        address="Jl. Sehat No. 1",
        occupation="Karyawan",
        pmo_name="PMO Test",
        pmo_phone="628999999999",
        is_active=True,
    )
    db.add(patient)
    db.commit()

    treatment = Treatment(
        patient_id=patient.id,
        diagnosis_date=date(2026, 8, 1),
        therapy_start_date=date(2026, 8, 1),
        therapy_end_date=date(2027, 2, 1),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="dr. Paru",
        is_active=True,
    )
    db.add(treatment)
    db.commit()

    medicine = Medicine(
        code=f"OAT-{uid}",
        name=f"FDC-{prefix}",
        category="Kategori 1",
        strength="FDC",
        unit="Tablet",
        is_active=True,
    )
    db.add(medicine)
    db.commit()

    schedule1 = MedicineSchedule(
        treatment_id=treatment.id,
        medicine_id=medicine.id,
        dosage="3 tablet pagi",
        quantity_initial=60,
        quantity_remaining=60,
        drink_time=time(7, 0),
        is_active=True,
    )
    schedule2 = MedicineSchedule(
        treatment_id=treatment.id,
        medicine_id=medicine.id,
        dosage="3 tablet malam",
        quantity_initial=60,
        quantity_remaining=60,
        drink_time=time(19, 0),
        is_active=True,
    )
    db.add_all([schedule1, schedule2])
    db.commit()

    return patient, treatment, schedule1, schedule2


def test_case_1_no_daily_medications_returns_none(client, nakes_headers, db):
    # Case 1: No daily medications -> medication_adherence is null, no fake 92%
    create_base_patient_and_schedule(db, "1")

    res = client.get("/dashboard", headers=nakes_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["summary"]["medication_adherence"] is None
    assert len(data["adherence_trend"]) == 7
    for item in data["adherence_trend"]:
        assert item["percentage"] is None
        assert item["expected"] == 0
        assert item["taken"] == 0


def test_case_2_all_taken_returns_100_percent(client, nakes_headers, db):
    # Case 2: 10 expected, 10 taken -> 100%
    patient, treatment, s1, s2 = create_base_patient_and_schedule(db, "2")
    today = today_in_jakarta()

    # Create 10 doses in past 5 days (2 doses/day across s1 and s2)
    for i in range(1, 6):
        d = today - timedelta(days=i)
        dm1 = DailyMedication(
            medicine_schedule_id=s1.id,
            scheduled_date=d,
            scheduled_time=time(7, 0),
            status=DailyMedicationStatus.VERIFIED,
            is_active=True,
        )
        dm2 = DailyMedication(
            medicine_schedule_id=s2.id,
            scheduled_date=d,
            scheduled_time=time(19, 0),
            status=DailyMedicationStatus.VERIFIED,
            is_active=True,
        )
        db.add_all([dm1, dm2])
    db.commit()

    res = client.get("/dashboard", headers=nakes_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["medication_adherence"] == 100.0


def test_case_3_partial_taken_8_of_10_returns_80_percent(client, nakes_headers, db):
    # Case 3: 10 expected, 8 taken -> 80%
    patient, treatment, s1, s2 = create_base_patient_and_schedule(db, "3")
    today = today_in_jakarta()

    for i in range(1, 6):
        d = today - timedelta(days=i)
        # Taken dose on s1 (5 taken)
        dm1 = DailyMedication(
            medicine_schedule_id=s1.id,
            scheduled_date=d,
            scheduled_time=time(7, 0),
            status=DailyMedicationStatus.VERIFIED,
            is_active=True,
        )
        # 3 verified, 2 missed on s2 = 8 verified total out of 10
        dm2_status = DailyMedicationStatus.VERIFIED if i <= 3 else DailyMedicationStatus.MISSED
        dm2 = DailyMedication(
            medicine_schedule_id=s2.id,
            scheduled_date=d,
            scheduled_time=time(19, 0),
            status=dm2_status,
            is_active=True,
        )
        db.add_all([dm1, dm2])
    db.commit()

    res = client.get("/dashboard", headers=nakes_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["medication_adherence"] == 80.0


def test_case_4_zero_taken_returns_0_percent(client, nakes_headers, db):
    # Case 4: 10 expected, 0 taken -> 0.0% (not null, not 92%)
    patient, treatment, s1, s2 = create_base_patient_and_schedule(db, "4")
    today = today_in_jakarta()

    for i in range(1, 6):
        d = today - timedelta(days=i)
        dm1 = DailyMedication(
            medicine_schedule_id=s1.id,
            scheduled_date=d,
            scheduled_time=time(7, 0),
            status=DailyMedicationStatus.MISSED,
            is_active=True,
        )
        dm2 = DailyMedication(
            medicine_schedule_id=s2.id,
            scheduled_date=d,
            scheduled_time=time(19, 0),
            status=DailyMedicationStatus.REJECTED,
            is_active=True,
        )
        db.add_all([dm1, dm2])
    db.commit()

    res = client.get("/dashboard", headers=nakes_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["medication_adherence"] == 0.0


def test_case_5_future_schedule_excluded_from_denominator(client, nakes_headers, db):
    # Case 5: Future schedules (e.g. tomorrow) are NOT counted in denominator
    patient, treatment, s1, s2 = create_base_patient_and_schedule(db, "5")
    today = today_in_jakarta()

    # Yesterday: 1 dose taken
    dm_past = DailyMedication(
        medicine_schedule_id=s1.id,
        scheduled_date=today - timedelta(days=1),
        scheduled_time=time(7, 0),
        status=DailyMedicationStatus.VERIFIED,
        is_active=True,
    )
    # Tomorrow: future doses on s1 and s2 (status PENDING)
    dm_future1 = DailyMedication(
        medicine_schedule_id=s1.id,
        scheduled_date=today + timedelta(days=1),
        scheduled_time=time(7, 0),
        status=DailyMedicationStatus.PENDING,
        is_active=True,
    )
    dm_future2 = DailyMedication(
        medicine_schedule_id=s2.id,
        scheduled_date=today + timedelta(days=1),
        scheduled_time=time(19, 0),
        status=DailyMedicationStatus.PENDING,
        is_active=True,
    )
    db.add_all([dm_past, dm_future1, dm_future2])
    db.commit()

    res = client.get("/dashboard", headers=nakes_headers)
    assert res.status_code == 200
    data = res.json()
    # Denominator is 1 (yesterday), NOT 3 (yesterday + 2 tomorrow)
    assert data["summary"]["medication_adherence"] == 100.0


def test_case_6_7day_adherence_trend_has_actual_daily_data(client, nakes_headers, db):
    # Case 6: 7-day adherence trend returns accurate daily percentages
    patient, treatment, s1, s2 = create_base_patient_and_schedule(db, "6")
    today = today_in_jakarta()

    # Day 2 days ago: 2 expected (s1 taken, s2 missed) -> 50%
    d2 = today - timedelta(days=2)
    db.add_all([
        DailyMedication(
            medicine_schedule_id=s1.id,
            scheduled_date=d2,
            scheduled_time=time(7, 0),
            status=DailyMedicationStatus.VERIFIED,
            is_active=True,
        ),
        DailyMedication(
            medicine_schedule_id=s2.id,
            scheduled_date=d2,
            scheduled_time=time(19, 0),
            status=DailyMedicationStatus.MISSED,
            is_active=True,
        ),
    ])
    db.commit()

    res = client.get("/dashboard", headers=nakes_headers)
    assert res.status_code == 200
    data = res.json()
    trend = data["adherence_trend"]
    assert len(trend) == 7

    # Find the entry for 2 days ago
    d2_str = d2.isoformat()
    d2_item = next(item for item in trend if item["date"] == d2_str)
    assert d2_item["percentage"] == 50.0
    assert d2_item["expected"] == 2
    assert d2_item["taken"] == 1


def test_case_7_and_8_consistency_and_refetch_update(client, nakes_headers, db):
    # Case 7: Refresh dashboard returns identical data
    patient, treatment, s1, s2 = create_base_patient_and_schedule(db, "78")
    today = today_in_jakarta()

    d1 = today - timedelta(days=1)
    db.add(DailyMedication(
        medicine_schedule_id=s1.id,
        scheduled_date=d1,
        scheduled_time=time(7, 0),
        status=DailyMedicationStatus.MISSED,
        is_active=True,
    ))
    db.commit()

    res1 = client.get("/dashboard", headers=nakes_headers)
    assert res1.json()["summary"]["medication_adherence"] == 0.0

    # Repeat call (refresh)
    res2 = client.get("/dashboard", headers=nakes_headers)
    assert res2.json()["summary"]["medication_adherence"] == 0.0

    # Case 8: Add new verified dose on s2 -> adherence updates to 50%
    db.add(DailyMedication(
        medicine_schedule_id=s2.id,
        scheduled_date=d1,
        scheduled_time=time(19, 0),
        status=DailyMedicationStatus.VERIFIED,
        is_active=True,
    ))
    db.commit()

    res3 = client.get("/dashboard", headers=nakes_headers)
    assert res3.json()["summary"]["medication_adherence"] == 50.0


def test_case_9_today_verifications_count(client, nakes_headers, db):
    # Case 9: Verifikasi hari ini reflects today's VideoVerification count
    patient, treatment, s1, s2 = create_base_patient_and_schedule(db, "9")
    today = today_in_jakarta()

    res_init = client.get("/dashboard", headers=nakes_headers)
    init_count = res_init.json()["summary"]["today_verifications"]

    vv1 = VideoVerification(
        medicine_schedule_id=s1.id,
        verification_date=today,
        video_path="/videos/test1.mp4",
        file_name="test1.mp4",
        mime_type="video/mp4",
        file_size=1048576,
        status=VerificationStatus.VERIFIED,
        ai_confidence=0.95,
        is_active=True,
    )
    vv2 = VideoVerification(
        medicine_schedule_id=s2.id,
        verification_date=today,
        video_path="/videos/test2.mp4",
        file_name="test2.mp4",
        mime_type="video/mp4",
        file_size=1048576,
        status=VerificationStatus.PENDING,
        ai_confidence=0.88,
        is_active=True,
    )
    db.add_all([vv1, vv2])
    db.commit()

    res_after = client.get("/dashboard", headers=nakes_headers)
    assert res_after.json()["summary"]["today_verifications"] == init_count + 2
