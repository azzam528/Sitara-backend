import os
import io
import json
import pytest
import cv2
import numpy as np
from datetime import datetime, timedelta, time as datetime_time, timezone
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Environment setup
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforphase4validation"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:5173"
os.environ["ACTIVATION_BASE_URL"] = "https://activation.test.local"

from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.patient import Patient
from app.models.health_facility import HealthFacility
from app.models.treatment import Treatment, TreatmentPhase, TreatmentStatus, RegimenEnum
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.face_embedding import FaceEmbedding
from app.models.face_verification import FaceVerification, FaceVerificationStatus
from app.main import app

# In-memory test database
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


def create_test_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_sample_face_bytes(filename: str = "person_a_1.jpg") -> bytes:
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "tools",
        "face_benchmark",
        "dataset",
        filename,
    )
    if not os.path.exists(path):
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "tools",
            "face_benchmark",
            "dataset",
            "public_eval",
            "id01_obama_1.jpg",
        )
    with open(path, "rb") as f:
        return f.read()


def get_different_face_bytes() -> bytes:
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "tools",
        "face_benchmark",
        "dataset",
        "public_eval",
        "id02_biden_1.jpg",
    )
    if not os.path.exists(path):
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "tools",
            "face_benchmark",
            "dataset",
            "person_b_1.jpg",
        )
    with open(path, "rb") as f:
        return f.read()


def get_multi_face_bytes() -> bytes:
    face1_bytes = get_sample_face_bytes()
    img1 = cv2.imdecode(np.frombuffer(face1_bytes, np.uint8), cv2.IMREAD_COLOR)
    img_small = cv2.resize(img1, (300, 300))
    stitched = np.hstack([img_small, img_small])
    _, buf = cv2.imencode(".jpg", stitched)
    return buf.tobytes()


def get_no_face_bytes() -> bytes:
    blank = np.full((300, 300, 3), 128, dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", blank)
    return buf.tobytes()


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()


    # Health facility
    facility = HealthFacility(
        name="Puskesmas Uji Coba Phase 4",
        address="Jl. Kesehatan No. 4",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    # 1. Patient User A
    user_a = User(
        username="patient_a_p4",
        email="patient_a_p4@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    db.add(user_a)
    db.commit()
    db.refresh(user_a)

    patient_a = Patient(
        user_id=user_a.id,
        medical_record_number="MRN-P4-001",
        full_name="Pasien A Phase 4",
        nik="3201010000000011",
        phone="08111111111",
        gender="male",
        birth_date=datetime(1990, 1, 1).date(),
        address="Alamat Pasien A",
        occupation="Swasta",
        pmo_name="PMO A",
        pmo_phone="08111111112",
        is_active=True,
    )
    db.add(patient_a)

    # 2. Patient User B
    user_b = User(
        username="patient_b_p4",
        email="patient_b_p4@sitara.test",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
    )
    db.add(user_b)
    db.commit()
    db.refresh(user_b)

    patient_b = Patient(
        user_id=user_b.id,
        medical_record_number="MRN-P4-002",
        full_name="Pasien B Phase 4",
        nik="3201010000000022",
        phone="08222222222",
        gender="female",
        birth_date=datetime(1995, 5, 5).date(),
        address="Alamat Pasien B",
        occupation="PNS",
        pmo_name="PMO B",
        pmo_phone="08222222223",
        is_active=True,
    )
    db.add(patient_b)

    # 3. Nakes User
    user_nakes = User(
        username="nakes_user_p4",
        email="nakes_p4@sitara.test",
        password_hash="hashedpass",
        role="nakes",
        facility_id=facility.id,
        is_active=True,
    )
    db.add(user_nakes)

    # 4. Medicine
    med = Medicine(
        code="MED-001",
        name="Rifampisin 450mg",
        category="OAT",
        strength="450mg",
        unit="mg",
        is_active=True,
    )

    db.add(med)
    db.commit()
    db.refresh(med)

    # 5. Treatment for Patient A
    treatment_a = Treatment(
        patient_id=patient_a.id,
        diagnosis_date=datetime(2026, 1, 1).date(),
        therapy_start_date=datetime(2026, 1, 1).date(),
        therapy_end_date=datetime(2026, 7, 1).date(),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="Dr. Spesialis Paru",
        is_active=True,
    )
    db.add(treatment_a)

    # 6. Treatment for Patient B
    treatment_b = Treatment(
        patient_id=patient_b.id,
        diagnosis_date=datetime(2026, 1, 1).date(),
        therapy_start_date=datetime(2026, 1, 1).date(),
        therapy_end_date=datetime(2026, 7, 1).date(),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="Dr. Spesialis Paru",
        is_active=True,
    )
    db.add(treatment_b)
    db.commit()

    # 7. Schedule for Patient A
    sched_a = MedicineSchedule(
        treatment_id=treatment_a.id,
        medicine_id=med.id,
        dosage="1 Tablet",
        quantity_initial=60,
        quantity_remaining=60,
        drink_time=datetime_time(8, 0),
        is_active=True,
    )
    db.add(sched_a)

    # 8. Schedule for Patient B
    sched_b = MedicineSchedule(
        treatment_id=treatment_b.id,
        medicine_id=med.id,
        dosage="1 Tablet",
        quantity_initial=60,
        quantity_remaining=60,
        drink_time=datetime_time(8, 0),
        is_active=True,
    )
    db.add(sched_b)

    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


# =====================================================================
# PHASE 4 TEST SUITE: 15 TEST CASES
# =====================================================================


def test_01_verify_valid_face_returns_verified():
    """1. Valid face matching registered embedding -> verified: true, status: verified"""
    token_a = create_test_token(1)  # Patient A
    image_bytes = get_sample_face_bytes("person_a_1.jpg")

    # Step A: Register face first
    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    # Step B: Verify face with Patient A's medicine schedule (id = 1)
    response = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("verify.jpg", image_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is True
    assert data["status"] == "verified"
    assert data["similarity_score"] >= 0.70
    assert data["threshold"] == 0.70
    assert data["face_verification_id"] > 0


def test_02_verify_wrong_face_returns_failed():
    """2. Wrong face (different identity) -> verified: false, status: failed"""
    token_a = create_test_token(1)
    registered_bytes = get_sample_face_bytes("person_a_1.jpg")
    impostor_bytes = get_different_face_bytes()

    # Register face A
    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", registered_bytes, "image/jpeg")},
    )

    # Verify with face of different person
    response = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("impostor.jpg", impostor_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is False
    assert data["status"] == "failed"
    assert data["similarity_score"] < 0.70
    assert data["face_verification_id"] > 0


def test_03_verify_without_registered_face():
    """3. Verify before face registration -> 400 Bad Request"""
    token_a = create_test_token(1)
    image_bytes = get_sample_face_bytes()

    response = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("verify.jpg", image_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    assert response.status_code == 400
    assert "belum terdaftar" in response.json()["detail"]


def test_04_verify_no_face_detected():
    """4. Verify with blank image (no face) -> 400 Bad Request"""
    token_a = create_test_token(1)
    image_bytes = get_sample_face_bytes()
    no_face_bytes = get_no_face_bytes()

    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    response = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("no_face.jpg", no_face_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    assert response.status_code == 400
    assert "Tidak ada wajah yang terdeteksi" in response.json()["detail"]


def test_05_verify_multiple_faces_detected():
    """5. Verify with image containing multiple faces -> 400 Bad Request"""
    token_a = create_test_token(1)
    image_bytes = get_sample_face_bytes()
    multi_face_bytes = get_multi_face_bytes()

    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    response = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("multi.jpg", multi_face_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    assert response.status_code == 400
    assert "lebih dari satu wajah" in response.json()["detail"]


def test_06_verify_invalid_corrupt_image():
    """6. Verify with corrupted image bytes -> 400 Bad Request"""
    token_a = create_test_token(1)
    image_bytes = get_sample_face_bytes()

    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    response = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("corrupt.jpg", b"INVALID_BYTES", "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    assert response.status_code == 400
    assert "bukan gambar yang valid" in response.json()["detail"]


def test_07_verify_unauthenticated():
    """7. Verify without Bearer token -> 401 Unauthorized"""
    image_bytes = get_sample_face_bytes()

    response = client.post(
        "/face/verify",
        files={"image": ("verify.jpg", image_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    assert response.status_code == 401


def test_08_verify_non_patient_role():
    """8. Verify by user with role nakes -> 403 Forbidden"""
    token_nakes = create_test_token(3)
    image_bytes = get_sample_face_bytes()

    response = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_nakes}"},
        files={"image": ("verify.jpg", image_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    assert response.status_code == 403
    assert "Only patient" in response.json()["detail"]


def test_09_verify_own_medicine_schedule_success():
    """9. Verify with medicine_schedule belonging to authenticated patient -> Passes ownership check"""
    token_a = create_test_token(1)
    image_bytes = get_sample_face_bytes()

    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    response = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("verify.jpg", image_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},  # Sched 1 belongs to Patient A
    )

    assert response.status_code == 200


def test_10_verify_other_patient_medicine_schedule_forbidden():
    """10. Verify with medicine_schedule belonging to another patient -> 403 Forbidden"""
    token_a = create_test_token(1)  # Patient A
    image_bytes = get_sample_face_bytes()

    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    # Patient A attempts to verify using Patient B's medicine schedule (id = 2)
    response = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("verify.jpg", image_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 2},  # Sched 2 belongs to Patient B
    )

    assert response.status_code == 403
    assert "bukan milik pasien yang sedang login" in response.json()["detail"]


def test_11_patient_a_cannot_use_patient_b_embedding():
    """11. Patient A verification uses ONLY Patient A's active embedding"""
    token_a = create_test_token(1)  # Patient A
    token_b = create_test_token(2)  # Patient B
    bytes_a = get_sample_face_bytes("person_a_1.jpg")
    bytes_b = get_different_face_bytes()

    # Patient B registers face B
    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_b}"},
        files={"image": ("face_b.jpg", bytes_b, "image/jpeg")},
    )

    # Patient A (unregistered) tries to verify with face B on Patient A's schedule 1
    response = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("verify.jpg", bytes_b, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    # Should be rejected because Patient A has no active registered embedding
    assert response.status_code == 400
    assert "belum terdaftar" in response.json()["detail"]


def test_12_similarity_score_persisted_in_db():
    """12. Verified similarity score is stored accurately in face_verifications database record"""
    token_a = create_test_token(1)
    image_bytes = get_sample_face_bytes()

    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    res = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("verify.jpg", image_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )
    verification_id = res.json()["face_verification_id"]

    db = TestingSessionLocal()
    rec = db.query(FaceVerification).filter(FaceVerification.id == verification_id).first()
    assert rec is not None
    assert rec.patient_id == 1
    assert rec.medicine_schedule_id == 1
    assert rec.similarity_score == res.json()["similarity_score"]
    assert rec.status == FaceVerificationStatus.VERIFIED
    db.close()


def test_13_face_verification_id_returned_in_response():
    """13. Response contains valid positive integer face_verification_id"""
    token_a = create_test_token(1)
    image_bytes = get_sample_face_bytes()

    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    res = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("verify.jpg", image_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    assert "face_verification_id" in res.json()
    assert isinstance(res.json()["face_verification_id"], int)
    assert res.json()["face_verification_id"] > 0


def test_14_failed_verification_creates_audit_record():
    """14. Failed verification attempt still creates an audit record in face_verifications with status failed"""
    token_a = create_test_token(1)
    bytes_a = get_sample_face_bytes()
    bytes_b = get_different_face_bytes()

    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face_a.jpg", bytes_a, "image/jpeg")},
    )

    res = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("verify_impostor.jpg", bytes_b, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    data = res.json()
    assert data["verified"] is False
    verification_id = data["face_verification_id"]

    db = TestingSessionLocal()
    rec = db.query(FaceVerification).filter(FaceVerification.id == verification_id).first()
    assert rec is not None
    assert rec.status == FaceVerificationStatus.FAILED
    assert rec.similarity_score < 0.70
    db.close()


def test_15_retry_generates_new_verification_record():
    """15. Multiple verification attempts create separate distinct FaceVerification records"""
    token_a = create_test_token(1)
    image_bytes = get_sample_face_bytes()

    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    # Attempt 1
    res1 = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("verify1.jpg", image_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    # Attempt 2 (Retry)
    res2 = client.post(
        "/face/verify",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("verify2.jpg", image_bytes, "image/jpeg")},
        data={"medicine_schedule_id": 1},
    )

    id1 = res1.json()["face_verification_id"]
    id2 = res2.json()["face_verification_id"]

    assert id1 != id2
    assert id2 > id1

    db = TestingSessionLocal()
    count = db.query(FaceVerification).filter(FaceVerification.patient_id == 1).count()
    assert count == 2
    db.close()
