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
os.environ["SECRET_KEY"] = "testsecretkeyforactivationlanding"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:5173"
os.environ["ACTIVATION_BASE_URL"] = "https://activation.test.local"
os.environ["SITARA_APP_DOWNLOAD_URL"] = "https://download.test.local/sitara"

from app.core.database import Base, get_db
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.health_facility import HealthFacility
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

PATIENT_PAYLOAD = {
    "medical_record_number": "MRN-ACT-001",
    "full_name": "Pasien Aktivasi",
    "nik": "3201010000000099",
    "birth_date": "1990-01-01",
    "gender": "male",
    "phone": "081234567890",
    "address": "Alamat Uji",
    "occupation": "Wiraswasta",
    "pmo_name": "PMO Uji",
    "pmo_phone": "081234567891",
    "clinical_note": None,
}


def create_test_token(user_id: int, role: str = "nakes") -> str:
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

    facility = HealthFacility(
        name="Puskesmas Aktivasi",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    nakes = User(
        username="nakes_activation",
        email="nakes_activation@sitara.test",
        password_hash=hash_password("NakesPass1"),
        role="nakes",
        facility_id=facility.id,
        is_active=True,
        must_change_password=False,
    )
    db.add(nakes)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _nakes_headers() -> dict:
    db = TestingSessionLocal()
    nakes = db.query(User).filter(User.username == "nakes_activation").one()
    token = create_test_token(nakes.id, role="nakes")
    db.close()
    return {"Authorization": f"Bearer {token}"}


def test_activation_landing_renders_deep_link_for_token():
    response = client.get("/activate", params={"token": "TEST123"})

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text
    assert "Aktivasi Akun SITARA" in html
    assert "Akun SITARA Anda siap diaktifkan." in html
    assert "Buka SITARA" in html
    assert 'href="sitara://activate?token=TEST123"' in html
    assert html.count("TEST123") == 1
    assert "/auth/activate" not in html
    assert "<script" not in html.lower()
    assert not re.search(r"fetch\s*\(", html)
    assert "Belum memiliki aplikasi SITARA?" in html


def test_activation_landing_without_token_is_invalid():
    response = client.get("/activate")

    assert response.status_code == 400
    html = response.text
    assert "Link aktivasi tidak valid." in html
    assert "Buka SITARA" not in html
    assert "sitara://" not in html
    assert "/auth/activate" not in html


def test_create_patient_activation_url_is_https():
    response = client.post(
        "/patients",
        json=PATIENT_PAYLOAD,
        headers=_nakes_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    activation_url = body["activation_url"]
    parsed = urlparse(activation_url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "activation.test.local"
    assert parsed.path == "/activate"
    assert "token" in query

    message = parse_qs(urlparse(body["whatsapp_url"]).query)["text"][0]
    assert activation_url in message
    assert body["username"] == "6281234567890"


def test_activate_account_accepts_token_from_create_patient():
    create_response = client.post(
        "/patients",
        json=PATIENT_PAYLOAD,
        headers=_nakes_headers(),
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
    assert activate_response.json()["username"] == "6281234567890"
