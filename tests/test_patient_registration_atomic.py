import os
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforatomicregistration"
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
from app.models.activation_token import ActivationToken
from app.main import app
from app.services.patient_service import PatientService

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
client = TestClient(app, raise_server_exceptions=False)


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
        name="Puskesmas Uji Atomik",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    nakes = User(
        username="nakes_atomic_test",
        email="nakes_atomic@sitara.test",
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
    nakes = db.query(User).filter(User.username == "nakes_atomic_test").one()
    token = create_test_token(nakes.id, role="nakes")
    db.close()
    return {"Authorization": f"Bearer {token}"}


def test_tc01_new_patient_registration_success():
    """TEST 1: Registrasi pasien baru dengan data valid -> HTTP 200, User & Patient tersimpan."""
    payload = {
        "medical_record_number": "RM-ATOM-001",
        "full_name": "Pasien Atomik Sukses",
        "nik": "3201010000000001",
        "birth_date": "1995-05-20",
        "gender": "male",
        "phone": "087711223344",
        "address": "Jl. Sehat No. 1",
        "occupation": "Karyawan",
        "pmo_name": "PMO Test",
        "pmo_phone": "087799887766",
        "clinical_note": None,
    }

    res = client.post("/patients", json=payload, headers=_nakes_headers())
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["username"] == "6287711223344"
    assert "token=" in data["activation_url"]

    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "6287711223344").first()
    assert user is not None
    assert user.role == "patient"

    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    assert patient is not None
    assert patient.full_name == "Pasien Atomik Sukses"
    assert patient.phone == "6287711223344"
    assert patient.pmo_phone == "6287799887766"

    token = db.query(ActivationToken).filter(ActivationToken.user_id == user.id).first()
    assert token is not None
    db.close()


def test_tc02_duplicate_whatsapp_rejected():
    """TEST 2: Registrasi menggunakan WhatsApp yang sudah benar-benar memiliki akun pasien."""
    payload1 = {
        "medical_record_number": "RM-ATOM-002A",
        "full_name": "Pasien Pertama",
        "nik": "3201010000000002",
        "birth_date": "1995-05-20",
        "gender": "female",
        "phone": "087711223355",
        "address": "Jl. Sehat No. 2",
        "occupation": "Karyawan",
        "pmo_name": "PMO Test",
        "pmo_phone": "087799887766",
        "clinical_note": None,
    }
    res1 = client.post("/patients", json=payload1, headers=_nakes_headers())
    assert res1.status_code == 200

    payload2 = {
        "medical_record_number": "RM-ATOM-002B",
        "full_name": "Pasien Kedua",
        "nik": "3201010000000003",
        "birth_date": "1996-06-20",
        "gender": "female",
        "phone": "087711223355",
        "address": "Jl. Sehat No. 2B",
        "occupation": "Wiraswasta",
        "pmo_name": "PMO Test 2",
        "pmo_phone": "087799887766",
        "clinical_note": None,
    }
    res2 = client.post("/patients", json=payload2, headers=_nakes_headers())
    assert res2.status_code == 400
    assert res2.json()["detail"] == "Nomor WhatsApp sudah terdaftar sebagai akun."


def test_tc03_and_tc04_rollback_on_failure_and_retry_succeeds():
    """
    TEST 3 & 4:
    TC-03: Simulasikan kegagalan setelah User dibuat (saat pembuatan Patient) -> ROLLBACK, tidak ada orphan User.
    TC-04: Setelah TC-03 gagal, gunakan nomor WhatsApp yang sama untuk registrasi ulang -> BERHASIL!
    """
    test_phone = "087711223366"
    payload = {
        "medical_record_number": "RM-ATOM-003",
        "full_name": "Pasien Simulasi Gagal",
        "nik": "3201010000000004",
        "birth_date": "1990-01-01",
        "gender": "male",
        "phone": test_phone,
        "address": "Jl. Gagal No. 1",
        "occupation": "Pekerja",
        "pmo_name": "PMO Gagal",
        "pmo_phone": "087799887766",
        "clinical_note": None,
    }

    # 1. Simulate failure during PatientRepository.create
    with patch("app.repositories.patient_repository.PatientRepository.create", side_effect=RuntimeError("Simulated DB error on patient create")):
        res_fail = client.post("/patients", json=payload, headers=_nakes_headers())
        assert res_fail.status_code == 500

    # Verify TC-03: ROLLBACK happened, no orphan user exists in DB
    db = TestingSessionLocal()
    orphan_user = db.query(User).filter(User.username == "6287711223366").first()
    assert orphan_user is None, "CRITICAL: Orphan user found after patient creation failed!"
    orphan_patient = db.query(Patient).filter(Patient.phone == "6287711223366").first()
    assert orphan_patient is None
    db.close()

    # 2. Verify TC-04: Retry with the EXACT SAME WhatsApp number succeeds!
    res_retry = client.post("/patients", json=payload, headers=_nakes_headers())
    assert res_retry.status_code == 200
    assert res_retry.json()["username"] == "6287711223366"

    # Verify saved properly
    db = TestingSessionLocal()
    user_after = db.query(User).filter(User.username == "6287711223366").first()
    assert user_after is not None
    patient_after = db.query(Patient).filter(Patient.user_id == user_after.id).first()
    assert patient_after is not None
    assert patient_after.full_name == "Pasien Simulasi Gagal"
    db.close()


def test_tc05_rollback_on_activation_token_failure():
    """TEST 5: Simulasikan kegagalan pembuatan ActivationToken -> ROLLBACK SEMUA, tidak ada orphan User/Patient."""
    test_phone = "087711223377"
    payload = {
        "medical_record_number": "RM-ATOM-005",
        "full_name": "Pasien Token Gagal",
        "nik": "3201010000000005",
        "birth_date": "1992-02-02",
        "gender": "female",
        "phone": test_phone,
        "address": "Jl. Token No. 5",
        "occupation": "Guru",
        "pmo_name": "PMO Guru",
        "pmo_phone": "087799887766",
        "clinical_note": None,
    }

    with patch("app.repositories.activation_token_repository.ActivationTokenRepository.create", side_effect=RuntimeError("Simulated token creation failure")):
        res_fail = client.post("/patients", json=payload, headers=_nakes_headers())
        assert res_fail.status_code == 500

    db = TestingSessionLocal()
    orphan_user = db.query(User).filter(User.username == "6287711223377").first()
    assert orphan_user is None, "CRITICAL: Orphan user found after token creation failed!"
    orphan_patient = db.query(Patient).filter(Patient.phone == "6287711223377").first()
    assert orphan_patient is None
    db.close()


def test_tc06_double_submit_frontend_guard():
    """TEST 6: Validasi guard isSubmitting di frontend PatientAddView.js."""
    from pathlib import Path
    fe_file = Path(r"d:/Coding/sitara/sitara-admin/sitaraweb/src/views/patient/PatientAddView.js")
    content = fe_file.read_text(encoding="utf-8")
    assert "if (isSubmitting.value) {" in content
    assert "return;" in content


def test_tc07_network_or_db_error_consistency():
    """TEST 7: Simulasi DB Commit Exception -> Rollback konsisten."""
    test_phone = "087711223388"
    payload = {
        "medical_record_number": "RM-ATOM-007",
        "full_name": "Pasien DB Crash",
        "nik": "3201010000000007",
        "birth_date": "1993-03-03",
        "gender": "male",
        "phone": test_phone,
        "address": "Jl. Crash No. 7",
        "occupation": "Teknisi",
        "pmo_name": "PMO Crash",
        "pmo_phone": "087799887766",
        "clinical_note": None,
    }

    with patch.object(PatientService, "_build_activation_url", side_effect=RuntimeError("URL Builder failure")):
        res_fail = client.post("/patients", json=payload, headers=_nakes_headers())
        assert res_fail.status_code == 500

    db = TestingSessionLocal()
    orphan_user = db.query(User).filter(User.username == "6287711223388").first()
    assert orphan_user is None
    db.close()


def test_tc08_phone_normalization_consistency():
    """TEST 8: Validasi normalisasi nomor WhatsApp: 08..., +628..., 628..."""
    service = PatientService()
    assert service._normalize_phone("081234567890") == "6281234567890"
    assert service._normalize_phone("+6281234567890") == "6281234567890"
    assert service._normalize_phone("6281234567890") == "6281234567890"
    assert service._normalize_phone("0812-3456-7890") == "6281234567890"
    assert service._normalize_phone(" +62 812 3456 7890 ") == "6281234567890"
    assert service._normalize_phone("81234567890") == "6281234567890"
