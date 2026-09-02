import io
import os
import pytest
from datetime import date, time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.daily_medication import DailyMedication, DailyMedicationStatus, VotStep
from app.models.health_facility import HealthFacility
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.patient import Patient, GenderEnum
from app.models.treatment import Treatment, TreatmentStatus, TreatmentPhase, RegimenEnum
from app.models.user import User
from app.models.video_verification import VideoVerification, VerificationStatus

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


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
def client():
    return TestClient(app)


@pytest.fixture(scope="function")
def setup_data(db_session: Session):
    fac_a = HealthFacility(name="Facility A", address="Address A")
    fac_b = HealthFacility(name="Facility B", address="Address B")
    db_session.add_all([fac_a, fac_b])
    db_session.commit()

    user_pat_a = User(
        username="6281234567801",
        email="pat_a@test.com",
        password_hash="pw",
        role="patient",
        facility_id=fac_a.id,
        is_active=True,
    )
    user_pat_b = User(
        username="6281234567802",
        email="pat_b@test.com",
        password_hash="pw",
        role="patient",
        facility_id=fac_b.id,
        is_active=True,
    )
    user_nakes = User(
        username="nakes_user",
        email="nakes@test.com",
        password_hash="pw",
        role="nakes",
        facility_id=fac_a.id,
        is_active=True,
    )
    db_session.add_all([user_pat_a, user_pat_b, user_nakes])
    db_session.commit()

    patient_a = Patient(
        user_id=user_pat_a.id,
        medical_record_number="MRN001",
        full_name="Patient A",
        nik="1111111111111111",
        birth_date=date(1990, 1, 1),
        gender=GenderEnum.MALE,
        phone="6281234567801",
        address="Address A",
        occupation="Worker",
        pmo_name="PMO A",
        pmo_phone="0822222222",
        is_active=True,
    )
    patient_b = Patient(
        user_id=user_pat_b.id,
        medical_record_number="MRN002",
        full_name="Patient B",
        nik="2222222222222222",
        birth_date=date(1992, 2, 2),
        gender=GenderEnum.FEMALE,
        phone="6281234567802",
        address="Address B",
        occupation="Worker",
        pmo_name="PMO B",
        pmo_phone="0833333333",
        is_active=True,
    )
    db_session.add_all([patient_a, patient_b])
    db_session.commit()

    treatment_a = Treatment(
        patient_id=patient_a.id,
        diagnosis_date=date.today(),
        therapy_start_date=date.today(),
        therapy_end_date=date.today(),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="Dr. Tester",
    )
    treatment_b = Treatment(
        patient_id=patient_b.id,
        diagnosis_date=date.today(),
        therapy_start_date=date.today(),
        therapy_end_date=date.today(),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="Dr. Tester",
    )
    db_session.add_all([treatment_a, treatment_b])
    db_session.commit()

    med = Medicine(
        code="MED001",
        name="Rifampisin",
        category="Antibiotik",
        strength="450mg",
        unit="tablet",
        is_active=True,
    )
    db_session.add(med)
    db_session.commit()

    sched_a = MedicineSchedule(
        treatment_id=treatment_a.id,
        medicine_id=med.id,
        drink_time=time(8, 0),
        dosage="1 tablet",
        quantity_initial=30,
        quantity_remaining=30,
        is_active=True,
    )
    sched_b = MedicineSchedule(
        treatment_id=treatment_b.id,
        medicine_id=med.id,
        drink_time=time(8, 0),
        dosage="1 tablet",
        quantity_initial=30,
        quantity_remaining=30,
        is_active=True,
    )
    db_session.add_all([sched_a, sched_b])
    db_session.commit()

    daily_a = DailyMedication(
        medicine_schedule_id=sched_a.id,
        scheduled_date=date.today(),
        scheduled_time=time(8, 0),
        status=DailyMedicationStatus.IN_PROGRESS,
        vot_step=VotStep.DRINKING,
        attempt_count=1,
    )
    daily_b = DailyMedication(
        medicine_schedule_id=sched_b.id,
        scheduled_date=date.today(),
        scheduled_time=time(8, 0),
        status=DailyMedicationStatus.IN_PROGRESS,
        vot_step=VotStep.DRINKING,
        attempt_count=1,
    )
    db_session.add_all([daily_a, daily_b])
    db_session.commit()

    return {
        "user_pat_a": user_pat_a,
        "user_pat_b": user_pat_b,
        "user_nakes": user_nakes,
        "daily_a": daily_a,
        "daily_b": daily_b,
    }


def _auth_header(user: User):
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_upload_vot_video_success(client: TestClient, db_session: Session, setup_data: dict):
    user_a = setup_data["user_pat_a"]
    daily_a = setup_data["daily_a"]

    video_content = b"fake_mp4_video_bytes_for_testing"
    files = {"video": ("evidence.mp4", io.BytesIO(video_content), "video/mp4")}

    response = client.post(
        f"/vot/{daily_a.id}/video",
        files=files,
        headers=_auth_header(user_a),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["daily_medication_id"] == daily_a.id
    assert data["message"] == "Video evidence berhasil diunggah."
    assert "video_verification_id" in data
    assert data["video_verification_id"] is not None
    assert data["file_size"] == len(video_content)
    assert data["video_path"].endswith(".mp4")

    # Verify DB state
    db_session.refresh(daily_a)
    assert daily_a.video_verification_id == data["video_verification_id"]
    # Verify status is NOT changed to VERIFIED simply by uploading
    assert daily_a.status == DailyMedicationStatus.IN_PROGRESS

    video_rec = db_session.query(VideoVerification).filter(VideoVerification.id == daily_a.video_verification_id).first()
    assert video_rec is not None
    assert video_rec.status == VerificationStatus.PENDING
    assert video_rec.file_size == len(video_content)

    # Clean up file on disk if created
    if os.path.exists(video_rec.video_path):
        os.remove(video_rec.video_path)


def test_upload_vot_video_unauthenticated(client: TestClient, setup_data: dict):
    daily_a = setup_data["daily_a"]
    files = {"video": ("evidence.mp4", io.BytesIO(b"data"), "video/mp4")}
    response = client.post(f"/vot/{daily_a.id}/video", files=files)
    assert response.status_code == 401


def test_upload_vot_video_forbidden_for_nakes_role(client: TestClient, setup_data: dict):
    user_nakes = setup_data["user_nakes"]
    daily_a = setup_data["daily_a"]
    files = {"video": ("evidence.mp4", io.BytesIO(b"data"), "video/mp4")}
    response = client.post(
        f"/vot/{daily_a.id}/video",
        files=files,
        headers=_auth_header(user_nakes),
    )
    assert response.status_code == 403


def test_upload_vot_video_ownership_isolation(client: TestClient, setup_data: dict):
    user_b = setup_data["user_pat_b"]
    daily_a = setup_data["daily_a"]

    files = {"video": ("evidence.mp4", io.BytesIO(b"data"), "video/mp4")}
    # Patient B tries to upload to Patient A's daily medication
    response = client.post(
        f"/vot/{daily_a.id}/video",
        files=files,
        headers=_auth_header(user_b),
    )
    assert response.status_code == 404
    assert "Daily medication not found" in response.json()["detail"]


def test_upload_vot_video_empty_file_rejected(client: TestClient, setup_data: dict):
    user_a = setup_data["user_pat_a"]
    daily_a = setup_data["daily_a"]

    files = {"video": ("evidence.mp4", io.BytesIO(b""), "video/mp4")}
    response = client.post(
        f"/vot/{daily_a.id}/video",
        files=files,
        headers=_auth_header(user_a),
    )
    assert response.status_code == 400
    assert "kosong" in response.json()["detail"]


def test_upload_vot_video_invalid_mime_type_rejected(client: TestClient, setup_data: dict):
    user_a = setup_data["user_pat_a"]
    daily_a = setup_data["daily_a"]

    files = {"video": ("document.pdf", io.BytesIO(b"fake pdf content"), "application/pdf")}
    response = client.post(
        f"/vot/{daily_a.id}/video",
        files=files,
        headers=_auth_header(user_a),
    )
    assert response.status_code == 400
    assert "tidak didukung" in response.json()["detail"]


def test_upload_vot_video_file_size_exceeded(client: TestClient, setup_data: dict, monkeypatch):
    user_a = setup_data["user_pat_a"]
    daily_a = setup_data["daily_a"]

    monkeypatch.setattr(settings, "MAX_VOT_VIDEO_SIZE_MB", 1)
    # 2 MB content
    large_content = b"x" * (2 * 1024 * 1024)
    files = {"video": ("large.mp4", io.BytesIO(large_content), "video/mp4")}
    response = client.post(
        f"/vot/{daily_a.id}/video",
        files=files,
        headers=_auth_header(user_a),
    )
    assert response.status_code == 413
    assert "melebihi batas" in response.json()["detail"]


def test_upload_vot_video_idempotency(client: TestClient, db_session: Session, setup_data: dict):
    user_a = setup_data["user_pat_a"]
    daily_a = setup_data["daily_a"]

    # First upload
    video_1 = b"video_attempt_1"
    files_1 = {"video": ("evidence_1.mp4", io.BytesIO(video_1), "video/mp4")}
    res_1 = client.post(
        f"/vot/{daily_a.id}/video",
        files=files_1,
        headers=_auth_header(user_a),
    )
    assert res_1.status_code == 200
    id_1 = res_1.json()["video_verification_id"]

    # Second upload (same session retry/re-upload)
    video_2 = b"video_attempt_2_updated"
    files_2 = {"video": ("evidence_2.mp4", io.BytesIO(video_2), "video/mp4")}
    res_2 = client.post(
        f"/vot/{daily_a.id}/video",
        files=files_2,
        headers=_auth_header(user_a),
    )
    assert res_2.status_code == 200
    id_2 = res_2.json()["video_verification_id"]

    # Must update the existing record without creating duplicate VideoVerification row
    assert id_1 == id_2
    assert res_2.json()["file_size"] == len(video_2)

    count = db_session.query(VideoVerification).filter(VideoVerification.medicine_schedule_id == daily_a.medicine_schedule_id).count()
    assert count == 1

    # Cleanup
    v_rec = db_session.query(VideoVerification).filter(VideoVerification.id == id_1).first()
    if v_rec and os.path.exists(v_rec.video_path):
        os.remove(v_rec.video_path)
