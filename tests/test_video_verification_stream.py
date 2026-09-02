import os
import pytest
from datetime import date, time, datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models.user import User
from app.models.health_facility import HealthFacility
from app.models.patient import Patient, GenderEnum
from app.models.treatment import Treatment, TreatmentPhase, RegimenEnum, TreatmentStatus
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.video_verification import VideoVerification, VerificationStatus

# Setup In-Memory SQLite Engine
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
def setup_stream_data(db_session: Session):
    # Facility A & B
    facility_a = HealthFacility(name="Facility A", address="Jl. Cimenyan", latitude=-6.873, longitude=107.65)
    facility_b = HealthFacility(name="Facility B", address="Jl. Antapani", latitude=-6.9, longitude=107.6)
    db_session.add_all([facility_a, facility_b])
    db_session.commit()

    # Nakes A & B
    nakes_a = User(email="na@a.com", username="na", password_hash="hash", role="nakes", facility_id=facility_a.id, is_active=True)
    nakes_b = User(email="nb@b.com", username="nb", password_hash="hash", role="nakes", facility_id=facility_b.id, is_active=True)
    db_session.add_all([nakes_a, nakes_b])

    # Patient Users A & B
    user_pa = User(email="pa@a.com", username="pa", password_hash="hash", role="patient", facility_id=facility_a.id, is_active=True)
    user_pb = User(email="pb@b.com", username="pb", password_hash="hash", role="patient", facility_id=facility_b.id, is_active=True)
    db_session.add_all([user_pa, user_pb])
    db_session.commit()

    # Patients A & B
    patient_a = Patient(user_id=user_pa.id, full_name="PA", medical_record_number="M1", nik="1111222233334444", birth_date=date(1990, 1, 1), gender=GenderEnum.MALE, phone="0811111111", address="A", occupation="W", pmo_name="P", pmo_phone="1", is_active=True)
    patient_b = Patient(user_id=user_pb.id, full_name="PB", medical_record_number="M2", nik="2222333344445555", birth_date=date(1990, 1, 1), gender=GenderEnum.MALE, phone="0822222222", address="B", occupation="W", pmo_name="P", pmo_phone="2", is_active=True)
    db_session.add_all([patient_a, patient_b])
    db_session.commit()

    # Treatments A & B
    treatment_a = Treatment(patient_id=patient_a.id, diagnosis_date=date(2023, 1, 1), therapy_start_date=date(2023, 1, 2), therapy_end_date=date(2023, 7, 2), phase=TreatmentPhase.INTENSIVE, regimen=RegimenEnum.CATEGORY_1, status=TreatmentStatus.ACTIVE, doctor_name="Dr A", is_active=True)
    treatment_b = Treatment(patient_id=patient_b.id, diagnosis_date=date(2023, 1, 1), therapy_start_date=date(2023, 1, 2), therapy_end_date=date(2023, 7, 2), phase=TreatmentPhase.INTENSIVE, regimen=RegimenEnum.CATEGORY_1, status=TreatmentStatus.ACTIVE, doctor_name="Dr B", is_active=True)
    db_session.add_all([treatment_a, treatment_b])
    db_session.commit()

    # Medicine
    med = Medicine(code="M1", name="Med 1", category="Antibiotic", strength="500", unit="Tab", is_active=True)
    db_session.add(med)
    db_session.commit()

    # Schedules A & B
    schedule_a = MedicineSchedule(treatment_id=treatment_a.id, medicine_id=med.id, dosage="1x1", quantity_initial=30, quantity_remaining=30, drink_time=time(8, 0))
    schedule_b = MedicineSchedule(treatment_id=treatment_b.id, medicine_id=med.id, dosage="1x1", quantity_initial=30, quantity_remaining=30, drink_time=time(8, 0))
    db_session.add_all([schedule_a, schedule_b])
    db_session.commit()

    # Dummy file
    os.makedirs("uploads/test_videos", exist_ok=True)
    video_file_a = "uploads/test_videos/video_a.mp4"
    with open(video_file_a, "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")

    # Video A (Facility A)
    video_a = VideoVerification(
        id=101,
        medicine_schedule_id=schedule_a.id,
        verification_date=datetime.utcnow(),
        video_path=video_file_a,
        file_name="video_a.mp4",
        mime_type="video/mp4",
        file_size=len(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"),
        status=VerificationStatus.PENDING,
        is_active=True,
    )

    # Video B (Facility B)
    video_b = VideoVerification(
        id=102,
        medicine_schedule_id=schedule_b.id,
        verification_date=datetime.utcnow(),
        video_path=video_file_a,
        file_name="video_b.mp4",
        mime_type="video/mp4",
        file_size=len(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"),
        status=VerificationStatus.PENDING,
        is_active=True,
    )

    db_session.add_all([video_a, video_b])
    db_session.commit()

    token_nakes_a = create_access_token(data={"sub": str(nakes_a.id), "role": nakes_a.role})
    token_nakes_b = create_access_token(data={"sub": str(nakes_b.id), "role": nakes_b.role})
    token_patient = create_access_token(data={"sub": str(user_pa.id), "role": user_pa.role})

    yield {
        "token_nakes_a": token_nakes_a,
        "token_nakes_b": token_nakes_b,
        "token_patient": token_patient,
        "video_a_id": video_a.id,
        "video_b_id": video_b.id,
    }

    if os.path.exists(video_file_a):
        os.remove(video_file_a)
    if os.path.exists("uploads/test_videos"):
        try:
            os.rmdir("uploads/test_videos")
        except OSError:
            pass


def test_nakes_stream_own_facility_video_success(client, setup_stream_data):
    headers = {"Authorization": f"Bearer {setup_stream_data['token_nakes_a']}"}
    response = client.get(f"/video-verifications/{setup_stream_data['video_a_id']}/stream", headers=headers)
    assert response.status_code == 200
    assert "video/mp4" in response.headers.get("content-type", "")
    assert len(response.content) > 0


def test_nakes_stream_other_facility_video_forbidden(client, setup_stream_data):
    # Nakes A tries to stream Video B (from Facility B) -> 404
    headers = {"Authorization": f"Bearer {setup_stream_data['token_nakes_a']}"}
    response = client.get(f"/video-verifications/{setup_stream_data['video_b_id']}/stream", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Video verification not found"


def test_patient_stream_video_forbidden(client, setup_stream_data):
    # Patient role is forbidden from /video-verifications/{id}/stream
    headers = {"Authorization": f"Bearer {setup_stream_data['token_patient']}"}
    response = client.get(f"/video-verifications/{setup_stream_data['video_a_id']}/stream", headers=headers)
    assert response.status_code == 403


def test_stream_nonexistent_video_not_found(client, setup_stream_data):
    headers = {"Authorization": f"Bearer {setup_stream_data['token_nakes_a']}"}
    response = client.get("/video-verifications/9999/stream", headers=headers)
    assert response.status_code == 404


def test_stream_path_traversal_safe(client, setup_stream_data, db_session):
    # Create video with path traversal attempt in DB
    malicious_video = VideoVerification(
        id=103,
        medicine_schedule_id=1,
        verification_date=datetime.utcnow(),
        video_path="../../etc/passwd",
        file_name="malicious.mp4",
        mime_type="video/mp4",
        file_size=100,
        status=VerificationStatus.PENDING,
        is_active=True,
    )
    db_session.add(malicious_video)
    db_session.commit()

    headers = {"Authorization": f"Bearer {setup_stream_data['token_nakes_a']}"}
    response = client.get("/video-verifications/103/stream", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Berkas video tidak ditemukan"


def test_nakes_save_review_note_pending_status(client, setup_stream_data):
    headers = {"Authorization": f"Bearer {setup_stream_data['token_nakes_a']}"}
    payload = {
        "status": "pending",
        "review_note": "Perlu konfirmasi pasien melalui PMO."
    }
    response = client.put(f"/video-verifications/{setup_stream_data['video_a_id']}", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["review_note"] == "Perlu konfirmasi pasien melalui PMO."
