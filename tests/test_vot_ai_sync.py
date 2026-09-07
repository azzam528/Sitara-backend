import io
import pytest
from datetime import date, time, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

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
from app.services.face_service import FaceService
from app.services.medicine_detection_service import MedicineDetectionService

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
    db_session.add(fac_a)
    db_session.commit()

    user_nakes_a = User(username="nakes_a", email="nakes_a@test.com", password_hash="pw", role="nakes", facility_id=fac_a.id, is_active=True)
    user_patient_a = User(username="pat_a", email="pat_a@test.com", password_hash="pw", role="patient", facility_id=fac_a.id, is_active=True)
    db_session.add_all([user_nakes_a, user_patient_a])
    db_session.commit()

    patient_a = Patient(
        user_id=user_patient_a.id,
        medical_record_number="MRN001",
        full_name="Patient A",
        nik="1111111111111111",
        birth_date=date(1990, 1, 1),
        gender=GenderEnum.MALE,
        phone="0811111111",
        address="Address A",
        occupation="Worker",
        pmo_name="PMO A",
        pmo_phone="0822222222",
        is_active=True,
    )
    db_session.add(patient_a)
    db_session.commit()

    today = date.today()
    treatment_a = Treatment(
        patient_id=patient_a.id,
        diagnosis_date=today - timedelta(days=30),
        therapy_start_date=today - timedelta(days=30),
        therapy_end_date=today + timedelta(days=60),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="Dr. A",
        is_active=True,
    )
    db_session.add(treatment_a)
    db_session.commit()

    med_a = Medicine(code="R01", name="Rifampicin", category="Antibiotic", strength="450", unit="Tablet", is_active=True)
    med_b = Medicine(code="I01", name="Isoniazid", category="Antibiotic", strength="300", unit="Tablet", is_active=True)
    db_session.add_all([med_a, med_b])
    db_session.commit()

    sched_a = MedicineSchedule(
        treatment_id=treatment_a.id,
        medicine_id=med_a.id,
        dosage="450mg",
        quantity_initial=30,
        quantity_remaining=30,
        drink_time=time(8, 0),
        is_active=True,
    )
    sched_b = MedicineSchedule(
        treatment_id=treatment_a.id,
        medicine_id=med_b.id,
        dosage="300mg",
        quantity_initial=30,
        quantity_remaining=30,
        drink_time=time(12, 0),
        is_active=True,
    )
    db_session.add_all([sched_a, sched_b])
    db_session.commit()

    token_nakes_a = create_access_token({"sub": str(user_nakes_a.id), "role": "nakes", "facility_id": fac_a.id})
    token_patient_a = create_access_token({"sub": str(user_patient_a.id), "role": "patient", "facility_id": fac_a.id})

    return {
        "fac_a": fac_a,
        "user_nakes_a": user_nakes_a,
        "user_patient_a": user_patient_a,
        "patient_a": patient_a,
        "sched_a": sched_a,
        "sched_b": sched_b,
        "token_nakes_a": token_nakes_a,
        "token_patient_a": token_patient_a,
    }


def test_vot_ai_sync_auto_verified(client: TestClient, setup_data: dict, monkeypatch, db_session: Session):
    headers = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    headers_nakes = {"Authorization": f"Bearer {setup_data['token_nakes_a']}"}

    # 1. Start VOT
    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers)
    assert res_start.status_code == 200
    daily_id = res_start.json()["daily_medication_id"]

    class MockFaceSuccess:
        face_verification_id = 101
        verified = True
        similarity_score = 0.95
        threshold = 0.70
        status = "verified"
        message = "Wajah cocok."
    monkeypatch.setattr(FaceService, "verify_face", lambda *args, **kwargs: MockFaceSuccess())
    monkeypatch.setattr(MedicineDetectionService, "detect_expected_medicine", lambda *args, **kwargs: {"medicine_match": True, "detected_medicine": "Rifampicin", "confidence": 0.98, "message": "Obat cocok."})

    client.post("/vot/face-verify", data={"daily_medication_id": daily_id}, files={"image": ("face.jpg", io.BytesIO(b"img"), "image/jpeg")}, headers=headers)
    client.post("/vot/medicine-detect", data={"daily_medication_id": daily_id}, files={"image": ("med.jpg", io.BytesIO(b"img"), "image/jpeg")}, headers=headers)

    # 2. Complete VOT with AI confidence 0.95
    payload = {
        "daily_medication_id": daily_id,
        "drinking_verified": True,
        "max_drinking_stage": "completed",
        "failure_reason": None,
        "ai_confidence": 0.95,
        "ai_details": {
            "level": "verified",
            "near_mouth_detected": True,
            "sequence_completed": True,
            "confidence_score": 95.0
        }
    }
    res_comp = client.post("/vot/complete", json=payload, headers=headers)
    assert res_comp.status_code == 200
    data_comp = res_comp.json()

    # Verification 1: Response data
    assert data_comp["status"] == "verified"
    assert data_comp["vot_step"] == "verified"
    assert data_comp["ai_confidence"] == 0.95
    assert data_comp["video_verification_id"] is not None
    v_id = data_comp["video_verification_id"]

    # Verification 2: Database state
    dm = db_session.query(DailyMedication).filter(DailyMedication.id == daily_id).first()
    assert dm.status == DailyMedicationStatus.VERIFIED
    assert dm.vot_step == VotStep.VERIFIED
    assert dm.video_verification_id == v_id

    vv = db_session.query(VideoVerification).filter(VideoVerification.id == v_id).first()
    assert vv is not None
    assert vv.status == VerificationStatus.VERIFIED
    assert vv.ai_confidence == 0.95

    # Verification 3: Upload after complete does not downgrade VERIFIED
    res_upload = client.post(
        f"/vot/{daily_id}/video",
        files={"video": ("test_vid.mp4", io.BytesIO(b"dummy mp4 video bytes"), "video/mp4")},
        headers=headers,
    )
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    assert upload_data["video_verification_id"] == v_id
    assert upload_data["status"] == "verified"

    # Verification 4: No duplicate VideoVerification
    all_vv = db_session.query(VideoVerification).filter(
        VideoVerification.medicine_schedule_id == dm.medicine_schedule_id,
        VideoVerification.verification_date == dm.scheduled_date
    ).all()
    assert len(all_vv) == 1

    # Verification 5: Pending endpoint does not return VERIFIED videos
    res_pending = client.get("/video-verifications/pending", headers=headers_nakes)
    assert res_pending.status_code == 200
    pending_list = res_pending.json()
    pending_ids = [p["id"] for p in pending_list]
    assert v_id not in pending_ids


def test_vot_ai_sync_non_auto_verified(client: TestClient, setup_data: dict, monkeypatch, db_session: Session):
    headers = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}

    # Start session for sched_b
    res_start_b = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_b"].id}, headers=headers)
    assert res_start_b.status_code == 200
    daily_id = res_start_b.json()["daily_medication_id"]

    class MockFaceSuccess:
        face_verification_id = 102
        verified = True
        similarity_score = 0.95
        threshold = 0.70
        status = "verified"
        message = "Wajah cocok."
    monkeypatch.setattr(FaceService, "verify_face", lambda *args, **kwargs: MockFaceSuccess())
    monkeypatch.setattr(MedicineDetectionService, "detect_expected_medicine", lambda *args, **kwargs: {"medicine_match": True, "detected_medicine": "Isoniazid", "confidence": 0.98, "message": "Obat cocok."})

    client.post("/vot/face-verify", data={"daily_medication_id": daily_id}, files={"image": ("face.jpg", io.BytesIO(b"img"), "image/jpeg")}, headers=headers)
    client.post("/vot/medicine-detect", data={"daily_medication_id": daily_id}, files={"image": ("med.jpg", io.BytesIO(b"img"), "image/jpeg")}, headers=headers)

    # Complete VOT with drinking_verified = False (e.g. max_drinking_stage = nearMouth, ambiguous)
    payload = {
        "daily_medication_id": daily_id,
        "drinking_verified": False,
        "max_drinking_stage": "nearMouth",
        "failure_reason": "AI_LOW_CONFIDENCE",
        "ai_confidence": 0.45,
    }
    res_comp = client.post("/vot/complete", json=payload, headers=headers)
    assert res_comp.status_code == 200
    data_comp = res_comp.json()

    # DailyMedication is NOT verified
    assert data_comp["status"] == "needs_review"
    assert data_comp["ai_confidence"] == 0.45
    v_id = data_comp["video_verification_id"]
    assert v_id is not None

    dm = db_session.query(DailyMedication).filter(DailyMedication.id == daily_id).first()
    assert dm.status != DailyMedicationStatus.VERIFIED

    vv = db_session.query(VideoVerification).filter(VideoVerification.id == v_id).first()
    assert vv.status != VerificationStatus.VERIFIED
    assert vv.ai_confidence == 0.45
