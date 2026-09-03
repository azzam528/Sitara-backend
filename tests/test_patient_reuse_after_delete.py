import os
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforpatientreuse"
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
from app.models.treatment import (
    Treatment,
    TreatmentPhase,
    TreatmentStatus,
    RegimenEnum,
)
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.control_schedule import ControlSchedule, ControlScheduleStatus
from app.models.face_embedding import FaceEmbedding
from app.models import (  # noqa: F401
    VideoVerification,
    Complaint,
    RefillRequest,
    Notification,
    ActivationToken,
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

BASE_PAYLOAD = {
    "medical_record_number": "MRN-REUSE-001",
    "full_name": "Pasien Reuse",
    "nik": "3201010000000301",
    "birth_date": "1990-01-01",
    "gender": "male",
    "phone": "081234567890",
    "address": "Alamat Uji",
    "occupation": "Wiraswasta",
    "pmo_name": "PMO Uji",
    "pmo_phone": "081234567891",
    "clinical_note": None,
}


def _payload(**overrides):
    data = dict(BASE_PAYLOAD)
    data.update(overrides)
    return data


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
        name="Puskesmas Reuse",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    nakes = User(
        username="nakes_reuse",
        email="nakes_reuse@sitara.test",
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
    nakes = db.query(User).filter(User.username == "nakes_reuse").one()
    token = create_test_token(nakes.id, role="nakes")
    db.close()
    return {"Authorization": f"Bearer {token}"}


def _token_from_url(activation_url: str) -> str:
    return parse_qs(urlparse(activation_url).query)["token"][0]


def _attach_history(patient_id: int) -> None:
    db = TestingSessionLocal()
    treatment = Treatment(
        patient_id=patient_id,
        diagnosis_date=date(2026, 1, 1),
        therapy_start_date=date(2026, 1, 2),
        therapy_end_date=date(2026, 6, 1),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="Dokter Uji",
        is_active=True,
    )
    db.add(treatment)
    db.commit()
    db.refresh(treatment)

    medicine = Medicine(
        code="MED-REUSE-1",
        name="Obat Uji",
        category="OAT",
        strength="150mg",
        unit="tablet",
        is_active=True,
    )
    db.add(medicine)
    db.commit()
    db.refresh(medicine)

    db.add(
        MedicineSchedule(
            treatment_id=treatment.id,
            medicine_id=medicine.id,
            dosage="1x1",
            quantity_initial=30,
            quantity_remaining=30,
            drink_time=time(8, 0),
            is_active=True,
        )
    )
    db.add(
        ControlSchedule(
            treatment_id=treatment.id,
            control_date=date(2026, 2, 1),
            control_time=time(9, 0),
            status=ControlScheduleStatus.PENDING,
            is_active=True,
        )
    )
    db.add(
        FaceEmbedding(
            patient_id=patient_id,
            embedding="[0.1,0.2]",
            model_version="test",
            is_active=True,
        )
    )
    db.commit()
    db.close()


def test_create_new_patient_succeeds():
    response = client.post(
        "/patients",
        json=_payload(),
        headers=_nakes_headers(),
    )
    assert response.status_code == 200
    assert response.json()["username"] == "6281234567890"
    assert response.json()["patient"]["is_active"] is True


def test_delete_archives_patient_and_user():
    headers = _nakes_headers()
    created = client.post("/patients", json=_payload(), headers=headers)
    patient_id = created.json()["patient"]["id"]
    user_id = created.json()["patient"]["user_id"]

    deleted = client.delete(f"/patients/{patient_id}", headers=headers)
    assert deleted.status_code == 200

    db = TestingSessionLocal()
    assert db.query(Patient).filter(Patient.id == patient_id).one().is_active is False
    assert db.query(User).filter(User.id == user_id).one().is_active is False
    db.close()


def test_reuse_after_delete_creates_new_user_and_patient():
    headers = _nakes_headers()
    created = client.post("/patients", json=_payload(), headers=headers)
    old_patient_id = created.json()["patient"]["id"]
    old_user_id = created.json()["patient"]["user_id"]
    old_token = _token_from_url(created.json()["activation_url"])
    _attach_history(old_patient_id)

    client.delete(f"/patients/{old_patient_id}", headers=headers)

    recreated = client.post("/patients", json=_payload(), headers=headers)
    assert recreated.status_code == 200
    body = recreated.json()
    new_patient_id = body["patient"]["id"]
    new_user_id = body["patient"]["user_id"]
    new_token = _token_from_url(body["activation_url"])
    parsed = urlparse(body["activation_url"])

    assert new_patient_id != old_patient_id
    assert new_user_id != old_user_id
    assert body["username"] == "6281234567890"
    assert body["patient"]["is_active"] is True
    assert parsed.scheme == "https"
    assert parsed.netloc == "activation.test.local"
    assert parsed.path == "/activate"
    assert new_token != old_token

    db = TestingSessionLocal()
    old_patient = db.query(Patient).filter(Patient.id == old_patient_id).one()
    old_user = db.query(User).filter(User.id == old_user_id).one()
    new_patient = db.query(Patient).filter(Patient.id == new_patient_id).one()
    new_user = db.query(User).filter(User.id == new_user_id).one()
    assert old_patient.is_active is False
    assert old_user.is_active is False
    assert new_patient.is_active is True
    assert new_user.is_active is True
    assert db.query(Treatment).filter(Treatment.patient_id == old_patient_id).count() == 1
    assert db.query(Treatment).filter(Treatment.patient_id == new_patient_id).count() == 0
    assert db.query(FaceEmbedding).filter(FaceEmbedding.patient_id == old_patient_id).count() == 1
    assert db.query(FaceEmbedding).filter(FaceEmbedding.patient_id == new_patient_id).count() == 0
    old_treatment_id = (
        db.query(Treatment).filter(Treatment.patient_id == old_patient_id).one().id
    )
    assert (
        db.query(MedicineSchedule)
        .filter(MedicineSchedule.treatment_id == old_treatment_id)
        .count()
        == 1
    )
    assert (
        db.query(ControlSchedule)
        .filter(ControlSchedule.treatment_id == old_treatment_id)
        .count()
        == 1
    )
    db.close()

    landing = client.get("/activate", params={"token": new_token})
    assert landing.status_code == 200
    assert 'href="sitara://activate?token=' in landing.text

    activate = client.post(
        "/auth/activate",
        json={"token": new_token, "new_password": "NewReusePass1"},
    )
    assert activate.status_code == 200

    login = client.post(
        "/auth/login",
        json={"username": "6281234567890", "password": "NewReusePass1"},
    )
    assert login.status_code == 200
    payload = jwt.decode(
        login.json()["access_token"],
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
    assert int(payload["sub"]) == new_user_id


def test_reuse_same_nik_after_delete_succeeds():
    headers = _nakes_headers()
    created = client.post("/patients", json=_payload(), headers=headers)
    client.delete(f"/patients/{created.json()['patient']['id']}", headers=headers)

    response = client.post(
        "/patients",
        json=_payload(phone="081211111111", medical_record_number="MRN-REUSE-NIK"),
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["patient"]["nik"] == "3201010000000301"


def test_reuse_same_mrn_after_delete_succeeds():
    headers = _nakes_headers()
    created = client.post("/patients", json=_payload(), headers=headers)
    client.delete(f"/patients/{created.json()['patient']['id']}", headers=headers)

    response = client.post(
        "/patients",
        json=_payload(phone="081222222222", nik="3201010000000399"),
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["patient"]["medical_record_number"] == "MRN-REUSE-001"


def test_duplicate_active_phone_nik_mrn_rejected():
    headers = _nakes_headers()
    assert client.post("/patients", json=_payload(), headers=headers).status_code == 200

    phone = client.post(
        "/patients",
        json=_payload(nik="3201010000000310", medical_record_number="MRN-DUP-P"),
        headers=headers,
    )
    assert phone.status_code == 400
    assert phone.json()["detail"] == "Nomor WhatsApp sudah terdaftar sebagai akun."

    nik = client.post(
        "/patients",
        json=_payload(phone="081298765431", medical_record_number="MRN-DUP-N"),
        headers=headers,
    )
    assert nik.status_code == 400
    assert nik.json()["detail"] == "NIK sudah terdaftar dalam sistem."

    mrn = client.post(
        "/patients",
        json=_payload(phone="081298765432", nik="3201010000000311"),
        headers=headers,
    )
    assert mrn.status_code == 400
    assert mrn.json()["detail"] == "Nomor rekam medis sudah terdaftar."


def test_login_ignores_inactive_user():
    headers = _nakes_headers()
    created = client.post("/patients", json=_payload(), headers=headers)
    old_token = _token_from_url(created.json()["activation_url"])
    old_patient_id = created.json()["patient"]["id"]
    client.post(
        "/auth/activate",
        json={"token": old_token, "new_password": "OldReusePass1"},
    )
    client.delete(f"/patients/{old_patient_id}", headers=headers)

    inactive_login = client.post(
        "/auth/login",
        json={"username": "6281234567890", "password": "OldReusePass1"},
    )
    assert inactive_login.status_code in (401, 403)

    recreated = client.post("/patients", json=_payload(), headers=headers)
    new_user_id = recreated.json()["patient"]["user_id"]
    new_token = _token_from_url(recreated.json()["activation_url"])
    client.post(
        "/auth/activate",
        json={"token": new_token, "new_password": "NewReusePass1"},
    )
    login = client.post(
        "/auth/login",
        json={"username": "6281234567890", "password": "NewReusePass1"},
    )
    assert login.status_code == 200
    payload = jwt.decode(
        login.json()["access_token"],
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
    assert int(payload["sub"]) == new_user_id


def test_active_non_patient_username_rejected():
    db = TestingSessionLocal()
    facility = db.query(HealthFacility).one()
    db.add(
        User(
            username="6281111111111",
            email="nakes_phone@sitara.test",
            password_hash=hash_password("NakesPass1"),
            role="nakes",
            facility_id=facility.id,
            is_active=True,
            must_change_password=False,
        )
    )
    db.commit()
    db.close()

    response = client.post(
        "/patients",
        json=_payload(phone="081111111111"),
        headers=_nakes_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Nomor WhatsApp sudah terdaftar sebagai akun non-pasien."
    )

def test_future_or_today_birth_date_rejected():
    from datetime import date, timedelta
    headers = _nakes_headers()
    today_str = date.today().isoformat()
    future_str = (date.today() + timedelta(days=1)).isoformat()

    # Today birth date rejected
    res_today = client.post(
        "/patients",
        json=_payload(phone="081299990001", nik="3201019999000001", medical_record_number="MRN-BD-1", birth_date=today_str),
        headers=headers,
    )
    assert res_today.status_code == 400
    assert res_today.json()["detail"] == "Tanggal lahir tidak boleh di masa depan."

    # Future birth date rejected
    res_future = client.post(
        "/patients",
        json=_payload(phone="081299990002", nik="3201019999000002", medical_record_number="MRN-BD-2", birth_date=future_str),
        headers=headers,
    )
    assert res_future.status_code == 400
    assert res_future.json()["detail"] == "Tanggal lahir tidak boleh di masa depan."
