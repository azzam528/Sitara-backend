import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforrefillmy"
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
from app.models.refill_request import RefillRequest, RefillRequestStatus
from app.models import (  # noqa: F401
    MedicineSchedule,
    VideoVerification,
    Complaint,
    ControlSchedule,
    Notification,
    ActivationToken,
    FaceEmbedding,
    FaceVerification,
    DailyMedication,
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


def create_test_token(user_id: int, role: str) -> str:
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


def _add_treatment(db, patient_id: int) -> Treatment:
    today = datetime.now(timezone.utc).date()
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
    return treatment


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(
        name="Puskesmas Refill",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    nakes = User(
        username="nakes_refill",
        email="nakes_refill@sitara.test",
        password_hash="hashedpass",
        role="nakes",
        facility_id=facility.id,
        is_active=True,
    )
    user_a = User(
        username="patient_a",
        email="patient_a_refill@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    user_b = User(
        username="patient_b",
        email="patient_b_refill@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    user_empty = User(
        username="patient_empty",
        email="patient_empty_refill@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    db.add_all([nakes, user_a, user_b, user_empty])
    db.commit()
    db.refresh(nakes)
    db.refresh(user_a)
    db.refresh(user_b)
    db.refresh(user_empty)

    patient_a = Patient(
        user_id=user_a.id,
        medical_record_number="MRN-REFILL-001",
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
        medical_record_number="MRN-REFILL-002",
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
    patient_empty = Patient(
        user_id=user_empty.id,
        medical_record_number="MRN-REFILL-003",
        full_name="Pasien Kosong",
        nik="3201010000000203",
        birth_date=datetime(1992, 2, 2).date(),
        gender="male",
        phone="08333333333",
        address="Alamat C",
        occupation="Karyawan",
        pmo_name="PMO C",
        pmo_phone="08333333334",
        is_active=True,
    )
    db.add_all([patient_a, patient_b, patient_empty])
    db.commit()
    db.refresh(patient_a)
    db.refresh(patient_b)
    db.refresh(patient_empty)

    medicine = Medicine(
        code="RIF-1",
        name="Rifampicin",
        category="OAT",
        strength="150mg",
        unit="tablet",
        is_active=True,
    )
    db.add(medicine)
    db.commit()
    db.refresh(medicine)

    treatment_a = _add_treatment(db, patient_a.id)
    treatment_b = _add_treatment(db, patient_b.id)
    _add_treatment(db, patient_empty.id)

    refill_a = RefillRequest(
        treatment_id=treatment_a.id,
        medicine_id=medicine.id,
        quantity=30,
        reason="Stok hampir habis",
        description="Milik A",
        status=RefillRequestStatus.PENDING,
        is_active=True,
    )
    refill_b = RefillRequest(
        treatment_id=treatment_b.id,
        medicine_id=medicine.id,
        quantity=20,
        reason="Stok habis",
        description="Milik B",
        status=RefillRequestStatus.APPROVED,
        is_active=True,
    )
    db.add_all([refill_a, refill_b])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def test_patient_get_my_refills_returns_200():
    response = client.get("/refills/my", headers=_headers("patient_a"))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_patient_sees_only_own_refills():
    response = client.get("/refills/my", headers=_headers("patient_a"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["description"] == "Milik A"
    assert body[0]["quantity"] == 30


def test_patient_a_does_not_see_patient_b_refill():
    response = client.get("/refills/my", headers=_headers("patient_a"))
    assert response.status_code == 200
    descriptions = [item["description"] for item in response.json()]
    assert "Milik B" not in descriptions


def test_patient_without_refill_gets_empty_list():
    response = client.get("/refills/my", headers=_headers("patient_empty"))
    assert response.status_code == 200
    assert response.json() == []


def test_nakes_can_still_list_all_refills():
    response = client.get("/refills", headers=_headers("nakes_refill"))
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_nakes_cannot_use_patient_my_endpoint():
    response = client.get("/refills/my", headers=_headers("nakes_refill"))
    assert response.status_code == 403
    assert response.json()["detail"] == "Only patient can access this endpoint"


def test_patient_cannot_use_nakes_all_refills():
    response = client.get("/refills", headers=_headers("patient_a"))
    assert response.status_code == 403
    assert response.json()["detail"] == "Only nakes can access this endpoint"
