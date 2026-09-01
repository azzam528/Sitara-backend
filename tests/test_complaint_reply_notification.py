import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforcomplaintreply"
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
from app.models.complaint import Complaint, ComplaintStatus
from app.models.notification import Notification, NotificationType
from app.models import (  # noqa: F401
    Medicine,
    MedicineSchedule,
    VideoVerification,
    RefillRequest,
    ControlSchedule,
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


def _user_id(username: str) -> int:
    db = TestingSessionLocal()
    user_id = db.query(User).filter(User.username == username).one().id
    db.close()
    return user_id


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(
        name="Puskesmas Complaint",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    nakes = User(
        username="nakes_complaint",
        email="nakes_complaint@sitara.test",
        password_hash="hashedpass",
        role="nakes",
        facility_id=facility.id,
        is_active=True,
    )
    user_a = User(
        username="patient_a",
        email="patient_a_complaint@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    user_b = User(
        username="patient_b",
        email="patient_b_complaint@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    db.add_all([nakes, user_a, user_b])
    db.commit()
    db.refresh(nakes)
    db.refresh(user_a)
    db.refresh(user_b)

    patient_a = Patient(
        user_id=user_a.id,
        medical_record_number="MRN-CMP-001",
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
        medical_record_number="MRN-CMP-002",
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

    today = datetime.now(timezone.utc).date()
    treatment_a = Treatment(
        patient_id=patient_a.id,
        diagnosis_date=today,
        therapy_start_date=today,
        therapy_end_date=today + timedelta(days=30),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="Dokter Uji",
        is_active=True,
    )
    treatment_b = Treatment(
        patient_id=patient_b.id,
        diagnosis_date=today,
        therapy_start_date=today,
        therapy_end_date=today + timedelta(days=30),
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

    complaint_a = Complaint(
        treatment_id=treatment_a.id,
        category="efek samping",
        description="Mual setelah minum obat",
        status=ComplaintStatus.PENDING,
        is_active=True,
    )
    db.add(complaint_a)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _complaint_a_id() -> int:
    db = TestingSessionLocal()
    complaint_id = db.query(Complaint).one().id
    db.close()
    return complaint_id


def test_patient_create_complaint_still_works():
    db = TestingSessionLocal()
    treatment_b = (
        db.query(Treatment)
        .join(Patient, Patient.id == Treatment.patient_id)
        .join(User, User.id == Patient.user_id)
        .filter(User.username == "patient_b")
        .one()
    )
    treatment_id = treatment_b.id
    db.close()

    response = client.post(
        "/complaints",
        json={
            "treatment_id": treatment_id,
            "category": "jadwal",
            "description": "Ingin reschedule",
        },
        headers=_headers("patient_b"),
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Ingin reschedule"


def test_nakes_reply_creates_notification_for_owning_patient_only():
    complaint_id = _complaint_a_id()
    reply = client.put(
        f"/complaints/{complaint_id}",
        json={
            "status": "in_progress",
            "response": "Silakan istirahat dan minum air.",
        },
        headers=_headers("nakes_complaint"),
    )
    assert reply.status_code == 200
    assert reply.json()["response"] == "Silakan istirahat dan minum air."

    patient_a_id = _user_id("patient_a")
    patient_b_id = _user_id("patient_b")

    notifications_a = client.get(
        "/notifications",
        headers=_headers("patient_a"),
    )
    assert notifications_a.status_code == 200
    body_a = notifications_a.json()
    assert len(body_a) == 1
    assert body_a[0]["user_id"] == patient_a_id
    assert body_a[0]["type"] == NotificationType.COMPLAINT.value
    assert body_a[0]["reference_id"] == complaint_id
    assert body_a[0]["is_read"] is False
    assert "membalas keluhan" in body_a[0]["message"].lower()

    notifications_b = client.get(
        "/notifications",
        headers=_headers("patient_b"),
    )
    assert notifications_b.status_code == 200
    assert notifications_b.json() == []
    assert patient_b_id != patient_a_id


def test_repeat_reply_does_not_duplicate_notification():
    complaint_id = _complaint_a_id()
    payload = {"response": "Balasan pertama."}
    first = client.put(
        f"/complaints/{complaint_id}",
        json=payload,
        headers=_headers("nakes_complaint"),
    )
    second = client.put(
        f"/complaints/{complaint_id}",
        json={"response": "Balasan diubah."},
        headers=_headers("nakes_complaint"),
    )
    assert first.status_code == 200
    assert second.status_code == 200

    db = TestingSessionLocal()
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == _user_id("patient_a"),
            Notification.type == NotificationType.COMPLAINT,
            Notification.reference_id == complaint_id,
        )
        .count()
    )
    db.close()
    assert count == 1


def test_status_only_update_does_not_create_reply_notification():
    complaint_id = _complaint_a_id()
    response = client.put(
        f"/complaints/{complaint_id}",
        json={"status": "in_progress"},
        headers=_headers("nakes_complaint"),
    )
    assert response.status_code == 200
    assert response.json()["response"] is None

    notifications = client.get(
        "/notifications",
        headers=_headers("patient_a"),
    )
    assert notifications.status_code == 200
    assert notifications.json() == []
