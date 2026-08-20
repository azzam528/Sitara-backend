import os
import io
import json
import pytest
import cv2
import numpy as np
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup dummy environment variables for test execution
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyforphase3validation"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:5173"

from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.patient import Patient
from app.models.face_embedding import FaceEmbedding
from app.models.health_facility import HealthFacility
from app.main import app

# Setup isolated in-memory SQLite DB
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


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()



    # Create dummy health facility
    facility = HealthFacility(
        name="Puskesmas Uji Coba",
        address="Jl. Kesehatan No. 1",
        phone="08123456789",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)


    # 1. Create Patient User A
    user_a = User(
        username="patient_a",
        email="patient_a@sitara.test",
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
        medical_record_number="MRN-001",
        full_name="Pasien A",
        nik="3201010000000001",
        phone="08111111111",
        gender="male",
        birth_date=datetime(1990, 1, 1).date(),
        address="Alamat Pasien A",
        occupation="Wiraswasta",
        pmo_name="PMO A",
        pmo_phone="08111111112",
        is_active=True,
    )
    db.add(patient_a)

    # 2. Create Patient User B
    user_b = User(
        username="patient_b",
        email="patient_b@sitara.test",
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
        medical_record_number="MRN-002",
        full_name="Pasien B",
        nik="3201010000000002",
        phone="08222222222",
        gender="female",
        birth_date=datetime(1995, 5, 5).date(),
        address="Alamat Pasien B",
        occupation="Guru",
        pmo_name="PMO B",
        pmo_phone="08222222223",
        is_active=True,
    )
    db.add(patient_b)

    # 3. Create Nakes User (Non-Patient)
    user_nakes = User(
        username="nakes_user",
        email="nakes@sitara.test",
        password_hash="hashedpass",
        role="nakes",
        facility_id=facility.id,
        is_active=True,
    )
    db.add(user_nakes)

    db.commit()
    db.close()


    yield

    Base.metadata.drop_all(bind=engine)



# Helper to get sample image bytes
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
        # Fallback to public_eval path
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


def get_multi_face_bytes() -> bytes:
    """Stitches two faces horizontally to simulate multiple faces in one frame."""
    face1_bytes = get_sample_face_bytes()
    img1 = cv2.imdecode(np.frombuffer(face1_bytes, np.uint8), cv2.IMREAD_COLOR)
    # Resize and place side by side
    img_small = cv2.resize(img1, (300, 300))
    stitched = np.hstack([img_small, img_small])
    _, buf = cv2.imencode(".jpg", stitched)
    return buf.tobytes()


def get_no_face_bytes() -> bytes:
    """Generates blank solid gray image without face."""
    blank = np.full((300, 300, 3), 128, dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", blank)
    return buf.tobytes()


# =====================================================================
# PHASE 3 TEST SUITE: 10 MINIMAL TEST CASES
# =====================================================================


def test_01_register_face_with_valid_image():
    """1. Register face with valid image -> returns 200, model_version opencv_yunet_sface_v1"""
    token_a = create_test_token(1)  # Patient A user_id = 1
    image_bytes = get_sample_face_bytes()

    response = client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["model_version"] == "opencv_yunet_sface_v1"
    assert "berhasil didaftarkan" in data["message"]


def test_02_register_without_authentication():
    """2. Register without authentication -> returns 401 Unauthorized"""
    image_bytes = get_sample_face_bytes()

    response = client.post(
        "/face/register",
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    assert response.status_code == 401


def test_03_register_by_non_patient():
    """3. Register by non-patient (role nakes) -> returns 403 Forbidden"""
    token_nakes = create_test_token(3)  # Nakes user_id = 3
    image_bytes = get_sample_face_bytes()

    response = client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_nakes}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )

    assert response.status_code == 403
    assert "Only patient" in response.json()["detail"]


def test_04_register_invalid_corrupted_image():
    """4. Image invalid / corrupt bytes -> returns 400 Bad Request"""
    token_a = create_test_token(1)
    corrupted_bytes = b"CORRUPTED_NON_IMAGE_DATA_BYTES_12345"

    response = client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("corrupted.jpg", corrupted_bytes, "image/jpeg")},
    )

    assert response.status_code == 400
    assert "bukan gambar yang valid" in response.json()["detail"]


def test_05_register_no_face_detected():
    """5. Tidak ada wajah terdeteksi (blank solid image) -> returns 400 Bad Request"""
    token_a = create_test_token(1)
    no_face_bytes = get_no_face_bytes()

    response = client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("no_face.jpg", no_face_bytes, "image/jpeg")},
    )

    assert response.status_code == 400
    assert "Tidak ada wajah yang terdeteksi" in response.json()["detail"]


def test_06_register_multiple_faces_detected():
    """6. Lebih dari satu wajah terdeteksi -> returns 400 Bad Request"""
    token_a = create_test_token(1)
    multi_face_bytes = get_multi_face_bytes()

    response = client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("multi_face.jpg", multi_face_bytes, "image/jpeg")},
    )

    assert response.status_code == 400
    assert "lebih dari satu wajah" in response.json()["detail"]


def test_07_get_face_status_before_registration():
    """7. GET /face/status sebelum register -> returns is_registered: false, model_version: null"""
    token_a = create_test_token(1)

    response = client.get(
        "/face/status",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_registered"] is False
    assert data["model_version"] is None
    assert data["registered_at"] is None


def test_08_get_face_status_after_registration():
    """8. GET /face/status setelah register -> returns is_registered: true, model_version: opencv_yunet_sface_v1"""
    token_a = create_test_token(1)
    image_bytes = get_sample_face_bytes()

    # Register first
    reg_resp = client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face.jpg", image_bytes, "image/jpeg")},
    )
    assert reg_resp.status_code == 200

    # Query status
    status_resp = client.get(
        "/face/status",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["is_registered"] is True
    assert data["model_version"] == "opencv_yunet_sface_v1"
    assert data["registered_at"] is not None


def test_09_reregister_face_deactivates_previous_embedding():
    """9. Register ulang wajah -> deactivates old embedding, creates new active embedding, exactly 1 active"""
    token_a = create_test_token(1)
    image_bytes = get_sample_face_bytes()

    # First registration
    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face_1.jpg", image_bytes, "image/jpeg")},
    )

    # Second registration (re-register)
    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face_2.jpg", image_bytes, "image/jpeg")},
    )

    # Verify directly in DB
    db = TestingSessionLocal()
    patient_a = db.query(Patient).filter(Patient.user_id == 1).first()
    all_embeddings = (
        db.query(FaceEmbedding)
        .filter(FaceEmbedding.patient_id == patient_a.id)
        .all()
    )
    active_embeddings = [e for e in all_embeddings if e.is_active]

    assert len(all_embeddings) == 2
    assert len(active_embeddings) == 1
    # Check 128-D embedding JSON format
    parsed_vector = json.loads(active_embeddings[0].embedding)
    assert len(parsed_vector) == 128
    assert active_embeddings[0].model_version == "opencv_yunet_sface_v1"
    db.close()


def test_10_patient_a_cannot_modify_or_see_patient_b_face_embedding():
    """10. Strict Scoping: Patient A registration does NOT affect or expose Patient B"""
    token_a = create_test_token(1)  # Patient A
    token_b = create_test_token(2)  # Patient B
    image_bytes = get_sample_face_bytes()

    # Patient A registers face
    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("face_a.jpg", image_bytes, "image/jpeg")},
    )

    # Check Patient B status (must still be false)
    status_b = client.get(
        "/face/status",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert status_b.status_code == 200
    assert status_b.json()["is_registered"] is False

    # Patient B registers face
    client.post(
        "/face/register",
        headers={"Authorization": f"Bearer {token_b}"},
        files={"image": ("face_b.jpg", image_bytes, "image/jpeg")},
    )

    # Verify each patient has their own distinct embedding record in DB
    db = TestingSessionLocal()
    patient_a = db.query(Patient).filter(Patient.user_id == 1).first()
    patient_b = db.query(Patient).filter(Patient.user_id == 2).first()

    emb_a = (
        db.query(FaceEmbedding)
        .filter(FaceEmbedding.patient_id == patient_a.id, FaceEmbedding.is_active == True)
        .first()
    )
    emb_b = (
        db.query(FaceEmbedding)
        .filter(FaceEmbedding.patient_id == patient_b.id, FaceEmbedding.is_active == True)
        .first()
    )

    assert emb_a is not None
    assert emb_b is not None
    assert emb_a.patient_id != emb_b.patient_id
    assert emb_a.id != emb_b.id
    db.close()
