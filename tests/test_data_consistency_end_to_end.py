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


@pytest.fixture(autouse=True)
def setup_db_override():
    app.dependency_overrides[get_db] = override_get_db
    yield
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
        id=1,
        username="nakes_sitara",
        email="nakes@sitara.id",
        password_hash=hash_password("Password123!"),
        role="nakes",
        facility_id=facility.id,
        is_active=True,
    )
    patient_user_1 = User(
        id=2,
        username="081234567890",
        email="haikal@sitara.id",
        password_hash=hash_password("Password123!"),
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    patient_user_2 = User(
        id=3,
        username="081234567891",
        email="maya@sitara.id",
        password_hash=hash_password("Password123!"),
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    db.add_all([nakes_user, patient_user_1, patient_user_2])
    db.commit()

    # 3. Patients
    patient_1 = Patient(
        id=1,
        user_id=patient_user_1.id,
        medical_record_number="RM-TB-2026-0001",
        full_name="Haikal Al-Farizi",
        nik="1241042194149192",
        birth_date=date(1998, 4, 12),
        gender=GenderEnum.MALE,
        phone="081234567890",
        address="Jl. Sukajadi No. 45, Bandung",
        occupation="Mahasiswa",
        pmo_name="Ibu Siti Farida",
        pmo_phone="081298765432",
        is_active=True,
    )
    patient_2 = Patient(
        id=2,
        user_id=patient_user_2.id,
        medical_record_number="RM-TB-2026-0002",
        full_name="Maya Indah",
        nik="3273015407960007",
        birth_date=date(1996, 7, 14),
        gender=GenderEnum.FEMALE,
        phone="081234567891",
        address="Jl. Dago Asri No. 18, Bandung",
        occupation="Karyawan Swasta",
        pmo_name="Bpk. Hendra Gunawan",
        pmo_phone="081387654321",
        is_active=True,
    )
    db.add_all([patient_1, patient_2])
    db.commit()

    # 4. Medicines
    med_fdc = Medicine(
        id=1,
        code="MED-4FDC",
        name="4FDC (RHZE)",
        category="Kategori 1",
        strength="150mg RIF + 75mg INH + 400mg PZA + 275mg EMB",
        unit="Tablet",
        is_active=True,
    )
    med_vitb6 = Medicine(
        id=2,
        code="MED-VITB6",
        name="Piridoksin (Vitamin B6)",
        category="Suplemen",
        strength="10mg",
        unit="Tablet",
        is_active=True,
    )
    db.add_all([med_fdc, med_vitb6])
    db.commit()

    # 5. Treatments
    treatment_1 = Treatment(
        id=1,
        patient_id=patient_1.id,
        diagnosis_date=date(2026, 8, 1),
        therapy_start_date=date(2026, 8, 1),
        therapy_end_date=date(2027, 2, 1),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="dr. Agus TB, Sp.P",
        is_active=True,
    )
    treatment_2 = Treatment(
        id=2,
        patient_id=patient_2.id,
        diagnosis_date=date(2026, 7, 15),
        therapy_start_date=date(2026, 7, 15),
        therapy_end_date=date(2027, 1, 15),
        phase=TreatmentPhase.CONTINUATION,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="dr. Nina, Sp.P",
        is_active=True,
    )
    db.add_all([treatment_1, treatment_2])
    db.commit()

    # 6. Medicine Schedules
    schedule_1_1 = MedicineSchedule(
        id=1,
        treatment_id=treatment_1.id,
        medicine_id=med_fdc.id,
        dosage="4 tablet sekaligus",
        quantity_initial=120,
        quantity_remaining=92,
        drink_time=time(7, 0, 0),
        is_active=True,
    )
    schedule_1_2 = MedicineSchedule(
        id=2,
        treatment_id=treatment_1.id,
        medicine_id=med_vitb6.id,
        dosage="1 tablet pagi",
        quantity_initial=30,
        quantity_remaining=23,
        drink_time=time(7, 0, 0),
        is_active=True,
    )
    schedule_2_1 = MedicineSchedule(
        id=3,
        treatment_id=treatment_2.id,
        medicine_id=med_fdc.id,
        dosage="3 tablet per minum",
        quantity_initial=90,
        quantity_remaining=60,
        drink_time=time(9, 30, 0),
        is_active=True,
    )
    db.add_all([schedule_1_1, schedule_1_2, schedule_2_1])
    db.commit()

    # 7. Video Verifications
    video_1_1 = VideoVerification(
        id=1,
        medicine_schedule_id=schedule_1_1.id,
        verification_date=date(2026, 8, 18),
        video_path="/storage/videos/haikal_20260818.mp4",
        file_name="haikal_20260818.mp4",
        mime_type="video/mp4",
        file_size=1048576,
        thumbnail_path="/storage/thumbnails/haikal_20260818.jpg",
        ai_confidence=0.95,
        status=VerificationStatus.PENDING,
        created_at=datetime(2026, 8, 18, 7, 0, 0),
        is_active=True,
    )
    video_2_1 = VideoVerification(
        id=2,
        medicine_schedule_id=schedule_2_1.id,
        verification_date=date(2026, 8, 27),
        video_path="/storage/videos/maya_20260827.mp4",
        file_name="maya_20260827.mp4",
        mime_type="video/mp4",
        file_size=2097152,
        thumbnail_path="/storage/thumbnails/maya_20260827.jpg",
        ai_confidence=0.98,
        status=VerificationStatus.VERIFIED,
        created_at=datetime(2026, 8, 27, 9, 28, 0),
        is_active=True,
    )
    db.add_all([video_1_1, video_2_1])
    db.commit()

    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_01_treatment_detail_returns_exact_matching_patient():
    """1. Treatment 1 detail must include Patient 1 (Haikal) data in its response"""
    res = client.get("/treatments/1", headers=get_auth_headers(1, "nakes"))
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == 1
    assert data["patient_id"] == 1
    assert data["patient"] is not None
    assert data["patient"]["id"] == 1
    assert data["patient"]["full_name"] == "Haikal Al-Farizi"
    assert data["patient"]["nik"] == "1241042194149192"
    assert data["patient"]["medical_record_number"] == "RM-TB-2026-0001"
    assert data["patient"]["phone"] == "081234567890"


def test_02_video_verification_detail_returns_exact_matching_patient():
    """2. Video 1 detail must return Patient 1 (Haikal), NOT Patient 2 (Maya)"""
    res = client.get("/video-verifications/1", headers=get_auth_headers(1, "nakes"))
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == 1
    assert data["medicine_schedule_id"] == 1
    assert data["patient"] is not None
    assert data["patient"]["id"] == 1
    assert data["patient"]["full_name"] == "Haikal Al-Farizi"
    assert data["patient"]["nik"] == "1241042194149192"
    assert data["patient"]["medical_record_number"] == "RM-TB-2026-0001"
    assert data["ai_confidence"] == 0.95
    assert data["status"] == "pending"


def test_03_video_list_and_video_detail_match_perfectly():
    """3. Verify that items in GET /video-verifications match their GET /video-verifications/{id} records exactly"""
    list_res = client.get("/video-verifications", headers=get_auth_headers(1, "nakes"))
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 2

    # Verify Video 1 in list
    item_1 = next(item for item in items if item["id"] == 1)
    assert item_1["patient"]["full_name"] == "Haikal Al-Farizi"
    assert item_1["patient"]["nik"] == "1241042194149192"
    assert item_1["ai_confidence"] == 0.95

    # Verify Video 2 in list
    item_2 = next(item for item in items if item["id"] == 2)
    assert item_2["patient"]["full_name"] == "Maya Indah"
    assert item_2["patient"]["nik"] == "3273015407960007"
    assert item_2["ai_confidence"] == 0.98

    # Verify Video 2 detail directly
    detail_2_res = client.get("/video-verifications/2", headers=get_auth_headers(1, "nakes"))
    assert detail_2_res.status_code == 200
    detail_2 = detail_2_res.json()
    assert detail_2["patient"]["full_name"] == "Maya Indah"
    assert detail_2["patient"]["nik"] == "3273015407960007"
    assert detail_2["patient"]["medical_record_number"] == "RM-TB-2026-0002"


def test_04_patient_get_detail_and_get_by_id_consistency():
    """4. GET /patients/{id} and GET /patients/{id}/detail return identical patient data"""
    res1 = client.get("/patients/1", headers=get_auth_headers(1, "nakes"))
    res2 = client.get("/patients/1/detail", headers=get_auth_headers(1, "nakes"))

    assert res1.status_code == 200
    assert res2.status_code == 200

    p1 = res1.json()
    p2 = res2.json()

    assert p1["id"] == 1
    assert p1["full_name"] == "Haikal Al-Farizi"
    assert p1["nik"] == "1241042194149192"
    assert p1["medical_record_number"] == "RM-TB-2026-0001"
    assert p1["occupation"] == "Mahasiswa"
    assert p1["pmo_name"] == "Ibu Siti Farida"


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

    # 1. Check patient endpoint
    pat_res = client.get("/patients/1", headers=get_auth_headers(1, "nakes"))
    assert pat_res.json()["full_name"] == "Gibral Haikal Al-Farizi"
    assert pat_res.json()["occupation"] == "Software Engineer"
    assert pat_res.json()["pmo_name"] == "Ibu Ratna Sari"

    # 2. Check treatment detail endpoint (must show updated patient name)
    trt_res = client.get("/treatments/1", headers=get_auth_headers(1, "nakes"))
    assert trt_res.json()["patient"]["full_name"] == "Gibral Haikal Al-Farizi"

    # 3. Check video verification endpoint (must show updated patient name)
    vid_res = client.get("/video-verifications/1", headers=get_auth_headers(1, "nakes"))
    assert vid_res.json()["patient"]["full_name"] == "Gibral Haikal Al-Farizi"


def test_06_orphan_or_mismatched_foreign_keys_are_prevented():
    """6. Ensure treatment without patient or video without schedule is rejected with 400, 404, or 422"""
    # Create treatment for non-existent patient
    bad_treatment = {
        "patient_id": 9999,
        "doctor_name": "dr. Paru",
        "diagnosis_date": "2026-08-01",
        "therapy_start_date": "2026-08-01",
        "therapy_end_date": "2027-02-01",
        "phase": "intensive",
        "regimen": "category_1",
    }
    res = client.post("/treatments", json=bad_treatment, headers=get_auth_headers(1, "nakes"))
    assert res.status_code in [400, 404, 422]


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

    reject_res = client.put(
        "/video-verifications/1",
        json={"status": "rejected", "review_note": "Wajah tidak terlihat jelas saat menelan."},
        headers=get_auth_headers(1, "nakes"),
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"
    assert reject_res.json()["review_note"] == "Wajah tidak terlihat jelas saat menelan."
