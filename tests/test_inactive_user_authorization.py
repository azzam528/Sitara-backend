import os
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforinactiveauth"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:5173"
os.environ["ACTIVATION_BASE_URL"] = "https://activation.test.local"

from app.core.database import Base, get_db
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.patient import Patient
from app.models.health_facility import HealthFacility
from app.models import (  # noqa: F401
    Treatment,
    Medicine,
    MedicineSchedule,
    VideoVerification,
    Complaint,
    RefillRequest,
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

PATIENT_PAYLOAD = {
    "medical_record_number": "MRN-INACT-001",
    "full_name": "Pasien Aktivasi",
    "nik": "3201010000000501",
    "birth_date": "1990-01-01",
    "gender": "male",
    "phone": "081234567890",
    "address": "Alamat Uji",
    "occupation": "Wiraswasta",
    "pmo_name": "PMO Uji",
    "pmo_phone": "081234567891",
    "clinical_note": None,
}


def create_test_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _headers_for(username: str) -> dict:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == username).one()
    token = create_test_token(user.id, user.role)
    db.close()
    return {"Authorization": f"Bearer {token}"}


def _deactivate(username: str) -> None:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == username).one()
    user.is_active = False
    db.commit()
    db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(
        name="Puskesmas Inactive",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    nakes = User(
        username="nakes_inactive",
        email="nakes_inactive@sitara.test",
        password_hash=hash_password("NakesPass1"),
        role="nakes",
        facility_id=facility.id,
        is_active=True,
        must_change_password=False,
    )
    patient_user = User(
        username="patient_inactive",
        email="patient_inactive@sitara.test",
        password_hash=hash_password("PatientPass1"),
        role="patient",
        facility_id=facility.id,
        is_active=True,
        must_change_password=False,
    )
    db.add_all([nakes, patient_user])
    db.commit()
    db.refresh(patient_user)

    patient = Patient(
        user_id=patient_user.id,
        medical_record_number="MRN-INACT-099",
        full_name="Pasien Existing",
        nik="3201010000000599",
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
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def test_active_patient_can_access_protected_endpoint():
    response = client.get(
        "/auth/profile",
        headers=_headers_for("patient_inactive"),
    )
    assert response.status_code == 200
    assert response.json()["username"] == "patient_inactive"
    assert response.json()["is_active"] is True


def test_inactive_patient_old_token_is_forbidden():
    headers = _headers_for("patient_inactive")
    _deactivate("patient_inactive")

    response = client.get("/auth/profile", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Akun tidak aktif."

    notifications = client.get("/notifications", headers=headers)
    assert notifications.status_code == 403
    assert notifications.json()["detail"] == "Akun tidak aktif."


def test_active_nakes_can_access_protected_endpoint():
    response = client.get(
        "/auth/profile",
        headers=_headers_for("nakes_inactive"),
    )
    assert response.status_code == 200
    assert response.json()["role"] == "nakes"


def test_inactive_nakes_old_token_is_forbidden():
    headers = _headers_for("nakes_inactive")
    _deactivate("nakes_inactive")

    response = client.get("/refills", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Akun tidak aktif."


def test_invalid_token_still_returns_401():
    response = client.get(
        "/auth/profile",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_activation_still_works_without_jwt():
    create_response = client.post(
        "/patients",
        json=PATIENT_PAYLOAD,
        headers=_headers_for("nakes_inactive"),
    )
    assert create_response.status_code == 200

    token = parse_qs(
        urlparse(create_response.json()["activation_url"]).query
    )["token"][0]

    activate_response = client.post(
        "/auth/activate",
        json={"token": token, "new_password": "NewPassword1"},
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["message"] == "Akun berhasil diaktivasi."
