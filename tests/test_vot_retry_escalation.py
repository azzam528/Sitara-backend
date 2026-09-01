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
from app.models.face_verification import FaceVerification, FaceVerificationStatus
from app.models.health_facility import HealthFacility
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.notification import Notification, NotificationType
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

    user_nakes_a = User(username="nakes_a", email="nakes_a@test.com", password_hash="pw", role="nakes", facility_id=fac_a.id, is_active=True)
    user_nakes_b = User(username="nakes_b", email="nakes_b@test.com", password_hash="pw", role="nakes", facility_id=fac_b.id, is_active=True)
    user_patient_a = User(username="pat_a", email="pat_a@test.com", password_hash="pw", role="patient", facility_id=fac_a.id, is_active=True)
    db_session.add_all([user_nakes_a, user_nakes_b, user_patient_a])
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
    db_session.add(med_a)
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
    db_session.add(sched_a)
    db_session.commit()

    token_nakes_a = create_access_token({"sub": str(user_nakes_a.id), "role": "nakes", "facility_id": fac_a.id})
    token_nakes_b = create_access_token({"sub": str(user_nakes_b.id), "role": "nakes", "facility_id": fac_b.id})
    token_patient_a = create_access_token({"sub": str(user_patient_a.id), "role": "patient", "facility_id": fac_a.id})

    return {
        "fac_a": fac_a,
        "fac_b": fac_b,
        "user_nakes_a": user_nakes_a,
        "user_nakes_b": user_nakes_b,
        "user_patient_a": user_patient_a,
        "patient_a": patient_a,
        "sched_a": sched_a,
        "token_nakes_a": token_nakes_a,
        "token_nakes_b": token_nakes_b,
        "token_patient_a": token_patient_a,
    }


def test_face_failure_attempt_1_and_retry(client: TestClient, setup_data: dict, monkeypatch):
    headers = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    
    # 1. Start VOT
    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers)
    assert res_start.status_code == 200
    daily_id = res_start.json()["daily_medication_id"]
    assert res_start.json()["status"] == "in_progress"
    assert res_start.json()["vot_step"] == "waiting"

    # Mock face verify to fail (similarity < 0.70)
    from app.services.face_service import FaceService
    class MockFaceFail:
        face_verification_id = 99
        verified = False
        similarity_score = 0.45
        threshold = 0.70
        status = "failed"
        message = "Wajah tidak cocok."
    monkeypatch.setattr(FaceService, "verify_face", lambda *args, **kwargs: MockFaceFail())

    # Attempt 1: Face failure
    dummy_img = io.BytesIO(b"fake_image_bytes")
    res_face_1 = client.post(
        "/vot/face-verify",
        data={"daily_medication_id": daily_id},
        files={"image": ("face.jpg", dummy_img, "image/jpeg")},
        headers=headers,
    )
    assert res_face_1.status_code == 200
    data_1 = res_face_1.json()
    assert data_1["verified"] is False
    assert data_1["attempt_count"] == 1
    assert data_1["can_retry"] is True
    assert data_1["status"] == "failed"
    assert data_1["failure_reason"] == "FACE_VERIFICATION_FAILED"

    # Verify DailyMedication in DB/Session is still in_progress
    res_sess = client.get(f"/vot/{daily_id}", headers=headers)
    assert res_sess.status_code == 200
    assert res_sess.json()["status"] == "in_progress"
    assert res_sess.json()["attempt_count"] == 1


def test_medicine_failure_attempt_2(client: TestClient, setup_data: dict, monkeypatch):
    headers = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers)
    daily_id = res_start.json()["daily_medication_id"]

    # Face success
    from app.services.face_service import FaceService
    class MockFaceSuccess:
        face_verification_id = 101
        verified = True
        similarity_score = 0.95
        threshold = 0.70
        status = "verified"
        message = "Wajah cocok."
    monkeypatch.setattr(FaceService, "verify_face", lambda *args, **kwargs: MockFaceSuccess())

    dummy_img = io.BytesIO(b"fake_image_bytes")
    res_face = client.post(
        "/vot/face-verify",
        data={"daily_medication_id": daily_id},
        files={"image": ("face.jpg", dummy_img, "image/jpeg")},
        headers=headers,
    )
    assert res_face.status_code == 200
    assert res_face.json()["vot_step"] == "face_verified"

    # Mock medicine detect failure
    from app.services.medicine_detection_service import MedicineDetectionService
    monkeypatch.setattr(
        MedicineDetectionService,
        "detect_expected_medicine",
        lambda *args, **kwargs: {"medicine_match": False, "detected_medicine": None, "confidence": 0.0, "message": "Obat tidak terdeteksi."}
    )

    dummy_med_img = io.BytesIO(b"fake_med_bytes")
    res_med = client.post(
        "/vot/medicine-detect",
        data={"daily_medication_id": daily_id},
        files={"image": ("med.jpg", dummy_med_img, "image/jpeg")},
        headers=headers,
    )
    assert res_med.status_code == 200
    data_med = res_med.json()
    assert data_med["medicine_match"] is False
    assert data_med["attempt_count"] == 1
    assert data_med["can_retry"] is True
    assert data_med["status"] == "in_progress"
    assert data_med["failure_reason"] == "MEDICINE_DETECTION_FAILED"


def test_failure_attempt_3_escalates_to_needs_review(client: TestClient, setup_data: dict, monkeypatch):
    headers = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers)
    daily_id = res_start.json()["daily_medication_id"]

    from app.services.face_service import FaceService
    class MockFaceFail:
        face_verification_id = 99
        verified = False
        similarity_score = 0.45
        threshold = 0.70
        status = "failed"
        message = "Wajah tidak cocok."
    monkeypatch.setattr(FaceService, "verify_face", lambda *args, **kwargs: MockFaceFail())

    dummy_img = io.BytesIO(b"fake_image_bytes")
    # Attempt 1
    res1 = client.post("/vot/face-verify", data={"daily_medication_id": daily_id}, files={"image": ("face.jpg", dummy_img, "image/jpeg")}, headers=headers)
    assert res1.json()["attempt_count"] == 1
    assert res1.json()["can_retry"] is True

    # Attempt 2
    dummy_img.seek(0)
    res2 = client.post("/vot/face-verify", data={"daily_medication_id": daily_id}, files={"image": ("face.jpg", dummy_img, "image/jpeg")}, headers=headers)
    assert res2.json()["attempt_count"] == 2
    assert res2.json()["can_retry"] is True

    # Attempt 3 -> Escalation
    dummy_img.seek(0)
    res3 = client.post("/vot/face-verify", data={"daily_medication_id": daily_id}, files={"image": ("face.jpg", dummy_img, "image/jpeg")}, headers=headers)
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["attempt_count"] == 3
    assert data3["can_retry"] is False
    assert data3["status"] == "failed"
    assert data3["failure_reason"] == "FACE_VERIFICATION_FAILED"

    # Verify DailyMedication escalated to needs_review
    res_sess = client.get(f"/vot/{daily_id}", headers=headers)
    assert res_sess.status_code == 200
    assert res_sess.json()["status"] == "needs_review"
    assert res_sess.json()["attempt_count"] == 3
    assert res_sess.json()["can_retry"] is False


def test_drinking_timeout_waiting_increments_attempt(client: TestClient, setup_data: dict, monkeypatch):
    headers = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers)
    daily_id = res_start.json()["daily_medication_id"]

    # Face & Med success
    from app.services.face_service import FaceService
    from app.services.medicine_detection_service import MedicineDetectionService
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

    # Drinking timeout with max_drinking_stage = "waiting"
    res_comp = client.post(
        "/vot/complete",
        json={"daily_medication_id": daily_id, "drinking_verified": False, "max_drinking_stage": "waiting"},
        headers=headers,
    )
    assert res_comp.status_code == 200
    data_comp = res_comp.json()
    assert data_comp["attempt_count"] == 1
    assert data_comp["can_retry"] is True
    assert data_comp["status"] == "in_progress"
    assert data_comp["failure_reason"] == "DRINKING_TIMEOUT"


def test_drinking_timeout_near_mouth_direct_needs_review_no_retry(client: TestClient, setup_data: dict, monkeypatch):
    headers = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers)
    daily_id = res_start.json()["daily_medication_id"]

    from app.services.face_service import FaceService
    from app.services.medicine_detection_service import MedicineDetectionService
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

    # Drinking ambiguous with nearMouth
    res_comp = client.post(
        "/vot/complete",
        json={"daily_medication_id": daily_id, "drinking_verified": False, "max_drinking_stage": "nearMouth"},
        headers=headers,
    )
    assert res_comp.status_code == 200
    data_comp = res_comp.json()
    # Must be directly NEEDS_REVIEW, NO RETRY, attempt_count stays 0 (not incremented)
    assert data_comp["status"] == "needs_review"
    assert data_comp["can_retry"] is False
    assert data_comp["failure_reason"] == "DRINKING_AMBIGUOUS"
    assert data_comp["max_drinking_stage"] == "nearMouth"
    assert data_comp["attempt_count"] == 0


def test_drinking_timeout_withdrawing_direct_needs_review_no_retry(client: TestClient, setup_data: dict, monkeypatch):
    headers = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers)
    daily_id = res_start.json()["daily_medication_id"]

    from app.services.face_service import FaceService
    from app.services.medicine_detection_service import MedicineDetectionService
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

    res_comp = client.post(
        "/vot/complete",
        json={"daily_medication_id": daily_id, "drinking_verified": False, "max_drinking_stage": "withdrawing"},
        headers=headers,
    )
    assert res_comp.status_code == 200
    data_comp = res_comp.json()
    assert data_comp["status"] == "needs_review"
    assert data_comp["can_retry"] is False
    assert data_comp["failure_reason"] == "DRINKING_AMBIGUOUS"


def test_drinking_completed_success(client: TestClient, setup_data: dict, monkeypatch):
    headers = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers)
    daily_id = res_start.json()["daily_medication_id"]

    from app.services.face_service import FaceService
    from app.services.medicine_detection_service import MedicineDetectionService
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

    res_comp = client.post(
        "/vot/complete",
        json={"daily_medication_id": daily_id, "drinking_verified": True, "max_drinking_stage": "completed"},
        headers=headers,
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "verified"
    assert res_comp.json()["vot_step"] == "verified"


def test_facility_isolation_and_nakes_review_sync_verified(client: TestClient, setup_data: dict, monkeypatch, db_session: Session):
    headers_pat = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    headers_nakes_a = {"Authorization": f"Bearer {setup_data['token_nakes_a']}"}
    headers_nakes_b = {"Authorization": f"Bearer {setup_data['token_nakes_b']}"}

    # Start & escalate
    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers_pat)
    daily_id = res_start.json()["daily_medication_id"]

    from app.services.face_service import FaceService
    from app.services.medicine_detection_service import MedicineDetectionService
    class MockFaceSuccess:
        face_verification_id = 101
        verified = True
        similarity_score = 0.95
        threshold = 0.70
        status = "verified"
        message = "Wajah cocok."
    monkeypatch.setattr(FaceService, "verify_face", lambda *args, **kwargs: MockFaceSuccess())
    monkeypatch.setattr(MedicineDetectionService, "detect_expected_medicine", lambda *args, **kwargs: {"medicine_match": True, "detected_medicine": "Rifampicin", "confidence": 0.98, "message": "Obat cocok."})

    client.post("/vot/face-verify", data={"daily_medication_id": daily_id}, files={"image": ("face.jpg", io.BytesIO(b"img"), "image/jpeg")}, headers=headers_pat)
    client.post("/vot/medicine-detect", data={"daily_medication_id": daily_id}, files={"image": ("med.jpg", io.BytesIO(b"img"), "image/jpeg")}, headers=headers_pat)
    client.post("/vot/complete", json={"daily_medication_id": daily_id, "drinking_verified": False, "max_drinking_stage": "nearMouth"}, headers=headers_pat)

    # Get DailyMedication to find video_verification_id
    dm = db_session.query(DailyMedication).filter(DailyMedication.id == daily_id).first()
    assert dm.status == DailyMedicationStatus.NEEDS_REVIEW
    assert dm.video_verification_id is not None
    video_id = dm.video_verification_id

    # Nakes B (Facility B) tries to review -> 404
    res_review_b = client.put(f"/video-verifications/{video_id}", json={"status": "verified"}, headers=headers_nakes_b)
    assert res_review_b.status_code == 404

    # Nakes A (Facility A) reviews -> 200
    res_review_a = client.put(f"/video-verifications/{video_id}", json={"status": "verified", "review_note": "Disetujui Nakes"}, headers=headers_nakes_a)
    assert res_review_a.status_code == 200

    # Sync verification: DailyMedication must now be VERIFIED!
    db_session.refresh(dm)
    assert dm.status == DailyMedicationStatus.VERIFIED
    assert dm.vot_step == VotStep.VERIFIED
    assert dm.completed_at is not None


def test_nakes_review_sync_rejected(client: TestClient, setup_data: dict, monkeypatch, db_session: Session):
    headers_pat = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    headers_nakes_a = {"Authorization": f"Bearer {setup_data['token_nakes_a']}"}

    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers_pat)
    daily_id = res_start.json()["daily_medication_id"]

    from app.services.face_service import FaceService
    from app.services.medicine_detection_service import MedicineDetectionService
    class MockFaceSuccess:
        face_verification_id = 101
        verified = True
        similarity_score = 0.95
        threshold = 0.70
        status = "verified"
        message = "Wajah cocok."
    monkeypatch.setattr(FaceService, "verify_face", lambda *args, **kwargs: MockFaceSuccess())
    monkeypatch.setattr(MedicineDetectionService, "detect_expected_medicine", lambda *args, **kwargs: {"medicine_match": True, "detected_medicine": "Rifampicin", "confidence": 0.98, "message": "Obat cocok."})

    client.post("/vot/face-verify", data={"daily_medication_id": daily_id}, files={"image": ("face.jpg", io.BytesIO(b"img"), "image/jpeg")}, headers=headers_pat)
    client.post("/vot/medicine-detect", data={"daily_medication_id": daily_id}, files={"image": ("med.jpg", io.BytesIO(b"img"), "image/jpeg")}, headers=headers_pat)
    client.post("/vot/complete", json={"daily_medication_id": daily_id, "drinking_verified": False, "max_drinking_stage": "nearMouth"}, headers=headers_pat)

    dm = db_session.query(DailyMedication).filter(DailyMedication.id == daily_id).first()
    video_id = dm.video_verification_id

    # Nakes A rejects video
    res_review = client.put(f"/video-verifications/{video_id}", json={"status": "rejected", "review_note": "Gerakan tidak jelas"}, headers=headers_nakes_a)
    assert res_review.status_code == 200

    # Sync verification: DailyMedication must now be REJECTED!
    db_session.refresh(dm)
    assert dm.status == DailyMedicationStatus.REJECTED


def test_notification_routing_facility_isolation(client: TestClient, setup_data: dict, monkeypatch, db_session: Session):
    headers_pat = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}

    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers_pat)
    daily_id = res_start.json()["daily_medication_id"]

    from app.services.face_service import FaceService
    class MockFaceFail:
        face_verification_id = 99
        verified = False
        similarity_score = 0.45
        threshold = 0.70
        status = "failed"
        message = "Wajah tidak cocok."
    monkeypatch.setattr(FaceService, "verify_face", lambda *args, **kwargs: MockFaceFail())

    dummy_img = io.BytesIO(b"fake_image_bytes")
    client.post("/vot/face-verify", data={"daily_medication_id": daily_id}, files={"image": ("face.jpg", dummy_img, "image/jpeg")}, headers=headers_pat)
    dummy_img.seek(0)
    client.post("/vot/face-verify", data={"daily_medication_id": daily_id}, files={"image": ("face.jpg", dummy_img, "image/jpeg")}, headers=headers_pat)
    dummy_img.seek(0)
    client.post("/vot/face-verify", data={"daily_medication_id": daily_id}, files={"image": ("face.jpg", dummy_img, "image/jpeg")}, headers=headers_pat)

    # Check notifications
    notifs_nakes_a = db_session.query(Notification).filter(Notification.user_id == setup_data["user_nakes_a"].id).all()
    notifs_nakes_b = db_session.query(Notification).filter(Notification.user_id == setup_data["user_nakes_b"].id).all()

    assert len(notifs_nakes_a) >= 1
    assert notifs_nakes_a[0].title == "Eskalasi Verifikasi Obat"
    assert len(notifs_nakes_b) == 0

def test_drinking_timeout_attempt_3_escalates_to_needs_review(client: TestClient, setup_data: dict, monkeypatch):
    headers = {"Authorization": f"Bearer {setup_data['token_patient_a']}"}
    res_start = client.post("/vot/start", json={"medicine_schedule_id": setup_data["sched_a"].id}, headers=headers)
    daily_id = res_start.json()["daily_medication_id"]

    from app.services.face_service import FaceService
    from app.services.medicine_detection_service import MedicineDetectionService
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

    # Drinking timeout attempt 1
    res1 = client.post("/vot/complete", json={"daily_medication_id": daily_id, "drinking_verified": False, "max_drinking_stage": "waiting"}, headers=headers)
    assert res1.json()["attempt_count"] == 1
    assert res1.json()["can_retry"] is True

    # Drinking timeout attempt 2
    res2 = client.post("/vot/complete", json={"daily_medication_id": daily_id, "drinking_verified": False, "max_drinking_stage": "waiting"}, headers=headers)
    assert res2.json()["attempt_count"] == 2
    assert res2.json()["can_retry"] is True

    # Drinking timeout attempt 3 -> Escalates to needs_review
    res3 = client.post("/vot/complete", json={"daily_medication_id": daily_id, "drinking_verified": False, "max_drinking_stage": "waiting"}, headers=headers)
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["attempt_count"] == 3
    assert data3["can_retry"] is False
    assert data3["status"] == "needs_review"
    assert data3["failure_reason"] == "DRINKING_TIMEOUT"
