import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforresendactivation"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:5173"
os.environ["ACTIVATION_BASE_URL"] = "https://activation.test.local"
os.environ["SITARA_APP_DOWNLOAD_URL"] = "https://download.test.local/sitara"

from app.core.database import Base, get_db
from app.core.config import settings
from app.core.security import hash_activation_token, hash_password
from app.models.user import User
from app.models.health_facility import HealthFacility
from app.models.activation_token import ActivationToken
from app.models import (  # noqa: F401
    Patient,
    Treatment,
    Medicine,
    MedicineSchedule,
    VideoVerification,
    Complaint,
    RefillRequest,
    ControlSchedule,
    Notification,
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
    "medical_record_number": "MRN-RESEND-001",
    "full_name": "Pasien Resend",
    "nik": "3201010000000801",
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


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility_a = HealthFacility(
        name="Puskesmas Resend A",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    facility_b = HealthFacility(
        name="Puskesmas Resend B",
        address="Jl. Kesehatan No. 2",
        phone="08123456780",
        is_active=True,
    )
    db.add_all([facility_a, facility_b])
    db.commit()
    db.refresh(facility_a)
    db.refresh(facility_b)

    nakes_a = User(
        username="nakes_resend_a",
        email="nakes_resend_a@sitara.test",
        password_hash=hash_password("NakesPass1"),
        role="nakes",
        facility_id=facility_a.id,
        is_active=True,
        must_change_password=False,
    )
    nakes_b = User(
        username="nakes_resend_b",
        email="nakes_resend_b@sitara.test",
        password_hash=hash_password("NakesPass1"),
        role="nakes",
        facility_id=facility_b.id,
        is_active=True,
        must_change_password=False,
    )
    db.add_all([nakes_a, nakes_b])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _headers(username: str) -> dict:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == username).one()
    token = create_test_token(user.id, user.role)
    db.close()
    return {"Authorization": f"Bearer {token}"}


def _create_patient():
    return client.post(
        "/patients",
        json=PATIENT_PAYLOAD,
        headers=_headers("nakes_resend_a"),
    )


def _token_from_activation_url(activation_url: str) -> str:
    return parse_qs(urlparse(activation_url).query)["token"][0]


def _token_from_whatsapp(whatsapp_url: str) -> str:
    message = parse_qs(urlparse(whatsapp_url).query)["text"][0]
    match = re.search(r"/activate\?token=([^\s]+)", message)
    assert match is not None
    return match.group(1)


def test_resend_activation_for_inactive_patient_succeeds():
    created = _create_patient()
    assert created.status_code == 200
    patient_id = created.json()["patient"]["id"]

    response = client.post(
        f"/patients/{patient_id}/activation/resend",
        headers=_headers("nakes_resend_a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Link aktivasi baru berhasil dibuat."
    assert "whatsapp_url" in body
    assert "token" not in body
    assert "activation_url" not in body
    assert "password" not in body
    message = parse_qs(urlparse(body["whatsapp_url"]).query)["text"][0]
    assert "Akun SITARA" in message
    assert created.json()["username"] in message
    assert "24 jam" in message
    assert "https://activation.test.local/activate?token=" in message


def test_resend_creates_new_expiry_and_invalidates_old_token():
    created = _create_patient()
    patient_id = created.json()["patient"]["id"]
    old_raw = _token_from_activation_url(created.json()["activation_url"])
    user_id = created.json()["patient"]["user_id"]

    db = TestingSessionLocal()
    old_row = (
        db.query(ActivationToken)
        .filter(ActivationToken.token_hash == hash_activation_token(old_raw))
        .one()
    )
    old_expires = old_row.expires_at
    old_password = db.query(User).filter(User.id == user_id).one().password_hash
    db.close()

    before = datetime.utcnow()
    resend = client.post(
        f"/patients/{patient_id}/activation/resend",
        headers=_headers("nakes_resend_a"),
    )
    after = datetime.utcnow()
    assert resend.status_code == 200
    new_raw = _token_from_whatsapp(resend.json()["whatsapp_url"])
    assert new_raw != old_raw

    db = TestingSessionLocal()
    old_row = (
        db.query(ActivationToken)
        .filter(ActivationToken.token_hash == hash_activation_token(old_raw))
        .one()
    )
    new_row = (
        db.query(ActivationToken)
        .filter(ActivationToken.token_hash == hash_activation_token(new_raw))
        .one()
    )
    user = db.query(User).filter(User.id == user_id).one()
    hashes = [item.token_hash for item in db.query(ActivationToken).all()]
    db.close()

    assert old_row.used_at is not None
    assert new_row.used_at is None
    assert new_row.expires_at > old_expires
    assert new_row.expires_at >= before + timedelta(hours=23, minutes=50)
    assert new_row.expires_at <= after + timedelta(hours=24, minutes=10)
    assert old_raw not in hashes
    assert new_raw not in hashes
    assert user.password_hash == old_password
    assert user.must_change_password is True

    old_activate = client.post(
        "/auth/activate",
        json={"token": old_raw, "new_password": "NewPassword1"},
    )
    assert old_activate.status_code == 400
    assert old_activate.json()["detail"] == "Link aktivasi sudah digunakan."

    new_activate = client.post(
        "/auth/activate",
        json={"token": new_raw, "new_password": "NewPassword1"},
    )
    assert new_activate.status_code == 200
    assert new_activate.json()["message"] == "Akun berhasil diaktivasi."


def test_resend_rejected_when_account_already_activated():
    created = _create_patient()
    patient_id = created.json()["patient"]["id"]
    token = _token_from_activation_url(created.json()["activation_url"])
    activate = client.post(
        "/auth/activate",
        json={"token": token, "new_password": "NewPassword1"},
    )
    assert activate.status_code == 200

    db = TestingSessionLocal()
    count_before = db.query(ActivationToken).count()
    db.close()

    response = client.post(
        f"/patients/{patient_id}/activation/resend",
        headers=_headers("nakes_resend_a"),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Akun sudah diaktivasi."

    db = TestingSessionLocal()
    count_after = db.query(ActivationToken).count()
    unused = (
        db.query(ActivationToken)
        .filter(ActivationToken.used_at.is_(None))
        .count()
    )
    db.close()
    assert count_after == count_before
    assert unused == 0


def test_nakes_cannot_resend_patient_from_other_facility():
    created = _create_patient()
    patient_id = created.json()["patient"]["id"]
    response = client.post(
        f"/patients/{patient_id}/activation/resend",
        headers=_headers("nakes_resend_b"),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Patient not found"


def test_resend_unknown_patient_returns_404():
    response = client.post(
        "/patients/99999/activation/resend",
        headers=_headers("nakes_resend_a"),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Patient not found"


def test_resend_requires_nakes_authorization():
    created = _create_patient()
    patient_id = created.json()["patient"]["id"]
    user_id = created.json()["patient"]["user_id"]

    unauthenticated = client.post(
        f"/patients/{patient_id}/activation/resend",
    )
    assert unauthenticated.status_code in (401, 403)

    patient_headers = {
        "Authorization": f"Bearer {create_test_token(user_id, 'patient')}"
    }
    forbidden = client.post(
        f"/patients/{patient_id}/activation/resend",
        headers=patient_headers,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Only nakes can access this endpoint"


def test_resend_activation_landing_keeps_existing_deep_link():
    created = _create_patient()
    patient_id = created.json()["patient"]["id"]
    resend = client.post(
        f"/patients/{patient_id}/activation/resend",
        headers=_headers("nakes_resend_a"),
    )
    token = _token_from_whatsapp(resend.json()["whatsapp_url"])

    landing = client.get("/activate", params={"token": token})
    assert landing.status_code == 200
    assert f'href="sitara://activate?token={token}"' in landing.text
    assert "/auth/activate" not in landing.text
