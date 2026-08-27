import os
import sys
from datetime import date, datetime, time, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.health_facility import HealthFacility
from app.models.patient import Patient, GenderEnum
from app.models.treatment import Treatment, TreatmentPhase, TreatmentStatus, RegimenEnum
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.video_verification import VideoVerification, VerificationStatus
from app.models import (  # noqa: F401
    Complaint,
    RefillRequest,
    ControlSchedule,
    Notification,
    ActivationToken,
    FaceEmbedding,
    FaceVerification,
)
from app.core.security import hash_password

# Use isolated in-memory SQLite database with StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
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


def get_auth_headers(user_id: int = 1, role: str = "nakes"):
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module", autouse=True)
def setup_test_data():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # 1. Facility
    facility = HealthFacility(
        name="Puskesmas SITARA Jaya",
        address="Jl. SITARA No. 1",
        phone="0221234567",
        is_active=True,
    )
    db.add(facility)
    db.commit()

    # 2. Users
    nakes_user = User(
        username="nakes1",
        role="nakes",
        facility_id=facility.id,
        password_hash=hash_password("password123"),
        is_active=True,
    )
    patient_user1 = User(
        username="6285156366541",
        role="patient",
        facility_id=facility.id,
        password_hash=hash_password("password123"),
        is_active=True,
    )
    patient_user2 = User(
        username="6281234567890",
        role="patient",
        facility_id=facility.id,
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db.add_all([nakes_user, patient_user1, patient_user2])
    db.commit()

    # 3. Patients (Gibral Haikal & Siti Mariam)
    patient1 = Patient(
        user_id=patient_user1.id,
        medical_record_number="RM-TB-2026-8813",
        full_name="Gibral Haikal",
        nik="1234567891011123",
        birth_date=date(2006, 7, 31),
        gender=GenderEnum.MALE,
        phone="6285156366541",
        address="Jl. Merdeka No. 10",
        occupation="Mahasiswa",
        pmo_name="Ibu Ratna",
        pmo_phone="6281298765432",
        clinical_note="Pasien TB Sensitif Obat",
        is_active=True,
    )
    patient2 = Patient(
        user_id=patient_user2.id,
        medical_record_number="RM-TB-2026-0089",
        full_name="Siti Mariam",
        nik="3201015502940002",
        birth_date=date(1998, 4, 15),
        gender=GenderEnum.FEMALE,
        phone="6281234567890",
        address="Kp. Babakan RT 02/05",
        occupation="Wiraswasta",
        pmo_name="Bpk. Hendra",
        pmo_phone="6281398765431",
        clinical_note="Fase Lanjutan",
        is_active=True,
    )
    db.add_all([patient1, patient2])
    db.commit()

    # 4. Medicines
    med1 = Medicine(
        code="MED-001",
        name="4FDC",
        category="OAT",
        strength="Kombinasi Dosis Tetap",
        unit="Tablet",
        is_active=True,
    )
    db.add(med1)
    db.commit()

    # 5. Treatments
    treatment1 = Treatment(
        patient_id=patient1.id,
        diagnosis_date=date(2026, 8, 20),
        therapy_start_date=date(2026, 8, 27),
        therapy_end_date=date(2027, 2, 27),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="dr. Agus Sp.P",
        doctor_note="Mulai terapi intensif 2 bulan",
        is_active=True,
    )
    treatment2 = Treatment(
        patient_id=patient2.id,
        diagnosis_date=date(2026, 6, 10),
        therapy_start_date=date(2026, 6, 15),
        therapy_end_date=date(2026, 12, 15),
        phase=TreatmentPhase.CONTINUATION,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="dr. Siti Sp.P",
        doctor_note="Masuk fase lanjutan",
        is_active=True,
    )
    db.add_all([treatment1, treatment2])
    db.commit()

    # 6. Medicine Schedules
    sched1 = MedicineSchedule(
        treatment_id=treatment1.id,
        medicine_id=med1.id,
        dosage="3 Tablet",
        quantity_initial=60,
        quantity_remaining=54,
        drink_time=time(8, 0, 0),
        is_active=True,
    )
    sched2 = MedicineSchedule(
        treatment_id=treatment2.id,
        medicine_id=med1.id,
        dosage="2 Tablet",
        quantity_initial=60,
        quantity_remaining=40,
        drink_time=time(7, 30, 0),
        is_active=True,
    )
    db.add_all([sched1, sched2])
    db.commit()

    # 7. Video Verifications
    video1 = VideoVerification(
        medicine_schedule_id=sched1.id,
        verification_date=date(2026, 8, 27),
        video_path="/storage/videos/haikal_video1.mp4",
        file_name="haikal_video1.mp4",
        mime_type="video/mp4",
        file_size=5000000,
        ai_confidence=0.95,
        status=VerificationStatus.PENDING,
        review_note="Video rekaman pertama Haikal",
        is_active=True,
    )
    video2 = VideoVerification(
        medicine_schedule_id=sched2.id,
        verification_date=date(2026, 8, 27),
        video_path="/storage/videos/siti_video2.mp4",
        file_name="siti_video2.mp4",
        mime_type="video/mp4",
        file_size=4200000,
        ai_confidence=0.64,
        status=VerificationStatus.PENDING,
        review_note="Pencahayaan agak redup",
        is_active=True,
    )
    db.add_all([video1, video2])
    db.commit()

    yield

    db.close()


# =========================================================
# TEST INVARIANTS
# =========================================================

def test_01_treatment_detail_returns_exact_matching_patient():
    """1. Treatment detail returns complete & exact matching patient entity"""
    res = client.get("/treatments/1", headers=get_auth_headers(1, "nakes"))
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == 1
    assert data["patient_id"] == 1
    patient = data["patient"]
    assert patient["id"] == 1
    assert patient["full_name"] == "Gibral Haikal"
    assert patient["nik"] == "1234567891011123"
    assert patient["medical_record_number"] == "RM-TB-2026-8813"
    assert patient["birth_date"] == "2006-07-31"
    assert patient["gender"] == "male"
    assert patient["phone"] == "6285156366541"
    assert patient["occupation"] == "Mahasiswa"
    assert patient["address"] == "Jl. Merdeka No. 10"


def test_02_video_verification_detail_returns_exact_matching_patient():
    """2. Video verification detail returns exact patient attached to the schedule -> treatment -> patient"""
    res = client.get("/video-verifications/1", headers=get_auth_headers(1, "nakes"))
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == 1
    assert data["medicine_schedule_id"] == 1
    assert data["patient"] is not None
    assert data["patient"]["id"] == 1
    assert data["patient"]["full_name"] == "Gibral Haikal"
    assert data["patient"]["nik"] == "1234567891011123"
    assert data["patient"]["medical_record_number"] == "RM-TB-2026-8813"
    assert data["patient"]["phone"] == "6285156366541"
    assert data["treatment"] is not None
    assert data["treatment"]["phase"] == "intensive"


def test_03_video_list_and_video_detail_match_perfectly():
    """3. Video list items and video detail items have identical patient data for both patients"""
    list_res = client.get("/video-verifications", headers=get_auth_headers(1, "nakes"))
    assert list_res.status_code == 200
    videos = list_res.json()
    assert len(videos) == 2

    # Map by ID
    v1_list = next(v for v in videos if v["id"] == 1)
    v2_list = next(v for v in videos if v["id"] == 2)

    # Check detail for video 1 (Gibral Haikal)
    d1_res = client.get("/video-verifications/1", headers=get_auth_headers(1, "nakes"))
    d1 = d1_res.json()
    assert v1_list["patient"]["full_name"] == d1["patient"]["full_name"] == "Gibral Haikal"
    assert v1_list["patient"]["nik"] == d1["patient"]["nik"] == "1234567891011123"
    assert v1_list["ai_confidence"] == d1["ai_confidence"] == 0.95

    # Check detail for video 2 (Siti Mariam)
    d2_res = client.get("/video-verifications/2", headers=get_auth_headers(1, "nakes"))
    d2 = d2_res.json()
    assert v2_list["patient"]["full_name"] == d2["patient"]["full_name"] == "Siti Mariam"
    assert v2_list["patient"]["nik"] == d2["patient"]["nik"] == "3201015502940002"
    assert v2_list["ai_confidence"] == d2["ai_confidence"] == 0.64


def test_04_patient_get_detail_and_get_by_id_consistency():
    """4. Patient GET /patients/{id} and GET /patients/{id}/detail match identically"""
    p_res = client.get("/patients/1", headers=get_auth_headers(1, "nakes"))
    assert p_res.status_code == 200
    p_data = p_res.json()

    d_res = client.get("/patients/1/detail", headers=get_auth_headers(1, "nakes"))
    assert d_res.status_code == 200
    d_data = d_res.json()["patient"]

    assert p_data["full_name"] == d_data["full_name"] == "Gibral Haikal"
    assert p_data["nik"] == d_data["nik"] == "1234567891011123"
    assert p_data["phone"] == d_data["phone"] == "6285156366541"
    assert p_data["birth_date"] == d_data["birth_date"] == "2006-07-31"
    assert p_data["gender"] == d_data["gender"] == "male"


def test_05_update_patient_preserves_relationships_and_updates_all_views():
    """5. Updating patient name and occupation reflects across Patient, Treatment, and Video without breaking relations"""
    update_payload = {
        "full_name": "Gibral Haikal Al-Farizi",
        "occupation": "Software Engineer",
        "address": "Jl. Merdeka Baru No. 12",
        "pmo_name": "Ibu Ratna Sari",
        "pmo_phone": "6281298765432",
    }
    put_res = client.put("/patients/1", json=update_payload, headers=get_auth_headers(1, "nakes"))
    assert put_res.status_code == 200
    assert put_res.json()["full_name"] == "Gibral Haikal Al-Farizi"
    assert put_res.json()["occupation"] == "Software Engineer"

    # Verify Patient Detail reflects new name
    p_detail = client.get("/patients/1/detail", headers=get_auth_headers(1, "nakes")).json()
    assert p_detail["patient"]["full_name"] == "Gibral Haikal Al-Farizi"
    assert p_detail["patient"]["occupation"] == "Software Engineer"

    # Verify Treatment Detail reflects new name via relation
    t_detail = client.get("/treatments/1", headers=get_auth_headers(1, "nakes")).json()
    assert t_detail["patient"]["full_name"] == "Gibral Haikal Al-Farizi"
    assert t_detail["patient"]["occupation"] == "Software Engineer"

    # Verify Video Verification reflects new name via relation
    v_detail = client.get("/video-verifications/1", headers=get_auth_headers(1, "nakes")).json()
    assert v_detail["patient"]["full_name"] == "Gibral Haikal Al-Farizi"


def test_06_phone_and_user_username_remain_strictly_consistent():
    """6. Patient.phone and User.username consistency invariant"""
    db = TestingSessionLocal()
    patient = db.query(Patient).filter(Patient.id == 1).first()
    user = db.query(User).filter(User.id == patient.user_id).first()

    assert patient.phone == "6285156366541"
    assert user.username == "6285156366541"
    assert patient.phone == user.username
    db.close()


def test_07_approve_reject_video_uses_correct_id_and_returns_valid_status():
    """7. Video PUT approval and rejection updates state without 405 error"""
    approve_res = client.put(
        "/video-verifications/1",
        json={"status": "verified", "review_note": "Obat 4FDC tertelan dengan benar."},
        headers=get_auth_headers(1, "nakes"),
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "verified"
    assert approve_res.json()["review_note"] == "Obat 4FDC tertelan dengan benar."

    # Verify Video Detail reflects verified status
    v_detail = client.get("/video-verifications/1", headers=get_auth_headers(1, "nakes")).json()
    assert v_detail["status"] == "verified"
    assert v_detail["patient"]["full_name"] == "Gibral Haikal Al-Farizi"
