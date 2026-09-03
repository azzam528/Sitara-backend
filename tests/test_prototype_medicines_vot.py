from datetime import date, time, timedelta, datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, engine
from app.models.user import User
from app.models.patient import Patient, GenderEnum
from app.models.treatment import Treatment, TreatmentPhase, TreatmentStatus, RegimenEnum
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.daily_medication import DailyMedication, DailyMedicationStatus, VotStep
from app.core.security import create_access_token
from app.services.medicine_detection_service import medicine_detection_service


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session):
    def override_get_db():
        yield db

    from app.core.database import get_db
    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def nakes_headers(db: Session):
    user = User(
        username="nakes_proto_test",
        email="nakes_proto_test@sitara.com",
        password_hash="fakehash",
        role="nakes",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patient_user(db: Session):
    user_p = User(
        username="628999112233",
        email="patient_proto@sitara.com",
        password_hash="fakehash",
        role="patient",
        is_active=True,
    )
    db.add(user_p)
    db.flush()

    patient = Patient(
        user_id=user_p.id,
        nik="3201019999990001",
        medical_record_number="RM-PROTO-01",
        full_name="Pasien Prototype",
        phone=user_p.username,
        birth_date=date(1995, 1, 1),
        gender=GenderEnum.MALE,
        address="Jl. Prototype",
        occupation="Tester",
        pmo_name="PMO Proto",
        pmo_phone="628999112234",
        is_active=True,
    )
    db.add(patient)
    db.flush()

    treatment = Treatment(
        patient_id=patient.id,
        diagnosis_date=date(2026, 8, 1),
        therapy_start_date=date(2026, 8, 1),
        therapy_end_date=date(2027, 2, 1),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="dr. Spesialis TB",
        is_active=True,
    )
    db.add(treatment)
    db.commit()

    token = create_access_token({"sub": str(user_p.id), "role": user_p.role})
    headers = {"Authorization": f"Bearer {token}"}

    return user_p, patient, treatment, headers


def test_case_1_get_medicines_returns_paracetamol_and_promag(client, nakes_headers, db):
    # CASE 1: GET /medicines returns Paracetamol and Promag
    res = client.get("/medicines", headers=nakes_headers)
    assert res.status_code == 200
    meds = res.json()
    names = [m["name"] for m in meds]
    assert "Paracetamol" in names
    assert "Promag" in names

    pct = next(m for m in meds if m["name"] == "Paracetamol")
    assert pct["code"] == "MED-PCT-500"
    assert pct["strength"] == "500mg"
    assert pct["unit"] == "Tablet"

    pmg = next(m for m in meds if m["name"] == "Promag")
    assert pmg["code"] == "MED-PMG-200"
    assert pmg["strength"] == "200mg"
    assert pmg["unit"] == "Tablet"


def test_case_2_3_4_paracetamol_and_promag_database_id_consistency(client, nakes_headers, db):
    # CASE 2, 3, 4: Ensure exact DB ID matching
    pct_db = db.query(Medicine).filter(Medicine.name == "Paracetamol").first()
    pmg_db = db.query(Medicine).filter(Medicine.name == "Promag").first()

    assert pct_db is not None
    assert pmg_db is not None
    assert pct_db.name == "Paracetamol"
    assert pmg_db.name == "Promag"

    # API check
    res_pct = client.get(f"/medicines/{pct_db.id}", headers=nakes_headers)
    assert res_pct.status_code == 200
    assert res_pct.json()["id"] == pct_db.id
    assert res_pct.json()["name"] == "Paracetamol"

    res_pmg = client.get(f"/medicines/{pmg_db.id}", headers=nakes_headers)
    assert res_pmg.status_code == 200
    assert res_pmg.json()["id"] == pmg_db.id
    assert res_pmg.json()["name"] == "Promag"


def test_case_5_create_medicine_schedule_paracetamol(client, nakes_headers, patient_user, db):
    # CASE 5: Create medicine schedule with Paracetamol
    _, _, treatment, _ = patient_user
    pct_db = db.query(Medicine).filter(Medicine.name == "Paracetamol").first()

    payload = {
        "treatment_id": treatment.id,
        "medicine_id": pct_db.id,
        "dosage": "1 tablet setelah makan",
        "quantity_initial": 30,
        "quantity_remaining": 30,
        "drink_time": "08:00:00",
    }
    res = client.post("/medicine-schedules", json=payload, headers=nakes_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["treatment_id"] == treatment.id
    assert data["medicine_id"] == pct_db.id
    assert data["dosage"] == "1 tablet setelah makan"


def test_case_6_create_medicine_schedule_promag(client, nakes_headers, patient_user, db):
    # CASE 6: Create medicine schedule with Promag
    _, _, treatment, _ = patient_user
    pmg_db = db.query(Medicine).filter(Medicine.name == "Promag").first()

    payload = {
        "treatment_id": treatment.id,
        "medicine_id": pmg_db.id,
        "dosage": "1 tablet kunyah sebelum makan",
        "quantity_initial": 20,
        "quantity_remaining": 20,
        "drink_time": "12:00:00",
    }
    res = client.post("/medicine-schedules", json=payload, headers=nakes_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["treatment_id"] == treatment.id
    assert data["medicine_id"] == pmg_db.id
    assert data["dosage"] == "1 tablet kunyah sebelum makan"


def test_case_7_and_8_vot_matching_with_paracetamol_and_promag(db):
    # CASE 7 & 8: AI VOT matching logic against database medicine names
    pct_db = db.query(Medicine).filter(Medicine.name == "Paracetamol").first()
    pmg_db = db.query(Medicine).filter(Medicine.name == "Promag").first()

    # YOLO returns lowercase 'paracetamol' and 'promag'
    yolo_classes = medicine_detection_service.model.names
    assert 0 in yolo_classes and yolo_classes[0] == "paracetamol"
    assert 1 in yolo_classes and yolo_classes[1] == "promag"

    # Matching Paracetamol:
    assert pct_db.name.strip().lower() == yolo_classes[0]
    # Matching Promag:
    assert pmg_db.name.strip().lower() == yolo_classes[1]


def test_case_9_and_10_no_duplicates_and_exact_names(db):
    # CASE 9 & 10: No duplicates and exact naming
    pct_all = db.query(Medicine).filter(Medicine.name == "Paracetamol").all()
    pmg_all = db.query(Medicine).filter(Medicine.name == "Promag").all()

    assert len(pct_all) == 1, "There should be exactly 1 Paracetamol record"
    assert len(pmg_all) == 1, "There should be exactly 1 Promag record"

    assert pct_all[0].name == "Paracetamol"
    assert pmg_all[0].name == "Promag"
