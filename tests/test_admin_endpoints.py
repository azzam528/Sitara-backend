import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.database import get_db, Base
from app.core.security import create_access_token, hash_password

from app.models.user import User
from app.models.health_facility import HealthFacility

# =========================================================
# TEST DATABASE SETUP
# =========================================================

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

# =========================================================
# FIXTURES
# =========================================================


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    return TestClient(app)


@pytest.fixture(scope="function")
def setup_data(db_session: Session):
    # Facilities
    facility_a = HealthFacility(
        name="Puskesmas Cimenyan",
        address="Jl. Cimenyan No. 1",
        phone="022-123456",
        latitude=-6.87,
        longitude=107.67,
    )
    facility_b = HealthFacility(
        name="Puskesmas Antapani",
        address="Jl. Antapani No. 2",
        phone="022-654321",
        latitude=-6.9,
        longitude=107.6,
    )
    db_session.add_all([facility_a, facility_b])
    db_session.commit()

    # Admin
    admin = User(
        username="admin_sitara",
        email="admin@sitara.id",
        password_hash=hash_password("adminpass123"),
        role="admin",
        facility_id=None,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Nakes
    nakes_a = User(
        username="nakes_cimenyan",
        email="nakes_a@sitara.id",
        password_hash=hash_password("nakespass123"),
        role="nakes",
        facility_id=facility_a.id,
        is_active=True,
    )
    nakes_b = User(
        username="nakes_antapani",
        email="nakes_b@sitara.id",
        password_hash=hash_password("nakespass123"),
        role="nakes",
        facility_id=facility_b.id,
        is_active=True,
    )
    db_session.add_all([nakes_a, nakes_b])
    db_session.commit()

    # Patient
    patient = User(
        username="patient_test",
        email="patient@test.id",
        password_hash=hash_password("patientpass123"),
        role="patient",
        facility_id=facility_a.id,
        is_active=True,
    )
    db_session.add(patient)
    db_session.commit()

    admin_token = create_access_token({"sub": str(admin.id)})
    nakes_token = create_access_token({"sub": str(nakes_a.id)})
    patient_token = create_access_token({"sub": str(patient.id)})

    return {
        "admin_token": admin_token,
        "nakes_token": nakes_token,
        "patient_token": patient_token,
        "admin_id": admin.id,
        "nakes_a_id": nakes_a.id,
        "nakes_b_id": nakes_b.id,
        "patient_id": patient.id,
        "facility_a_id": facility_a.id,
        "facility_b_id": facility_b.id,
    }


# =========================================================
# 1. Admin can GET /admin/facilities
# =========================================================


def test_admin_can_get_facilities(client: TestClient, setup_data: dict):
    res = client.get(
        "/admin/facilities",
        headers={"Authorization": f"Bearer {setup_data['admin_token']}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Ordered by id ascending
    assert data[0]["name"] == "Puskesmas Cimenyan"
    assert data[1]["name"] == "Puskesmas Antapani"
    # Verify fields present
    assert "id" in data[0]
    assert "address" in data[0]
    assert "phone" in data[0]
    assert "latitude" in data[0]
    assert "longitude" in data[0]
    assert "is_active" in data[0]


# =========================================================
# 2. Nakes cannot GET /admin/facilities
# =========================================================


def test_nakes_cannot_get_facilities(client: TestClient, setup_data: dict):
    res = client.get(
        "/admin/facilities",
        headers={"Authorization": f"Bearer {setup_data['nakes_token']}"},
    )
    assert res.status_code == 403


# =========================================================
# 3. Patient cannot GET /admin/facilities
# =========================================================


def test_patient_cannot_get_facilities(client: TestClient, setup_data: dict):
    res = client.get(
        "/admin/facilities",
        headers={"Authorization": f"Bearer {setup_data['patient_token']}"},
    )
    assert res.status_code == 403


# =========================================================
# 4. Admin can GET /admin/nakes
# =========================================================


def test_admin_can_get_nakes(client: TestClient, setup_data: dict):
    res = client.get(
        "/admin/nakes",
        headers={"Authorization": f"Bearer {setup_data['admin_token']}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Ordered by id ascending
    assert data[0]["username"] == "nakes_cimenyan"
    assert data[1]["username"] == "nakes_antapani"


# =========================================================
# 5. Nakes cannot GET /admin/nakes
# =========================================================


def test_nakes_cannot_get_nakes(client: TestClient, setup_data: dict):
    res = client.get(
        "/admin/nakes",
        headers={"Authorization": f"Bearer {setup_data['nakes_token']}"},
    )
    assert res.status_code == 403


# =========================================================
# 6. Patient cannot GET /admin/nakes
# =========================================================


def test_patient_cannot_get_nakes(client: TestClient, setup_data: dict):
    res = client.get(
        "/admin/nakes",
        headers={"Authorization": f"Bearer {setup_data['patient_token']}"},
    )
    assert res.status_code == 403


# =========================================================
# 7. Nakes response contains facility_id and facility_name
# =========================================================


def test_nakes_response_contains_facility_info(client: TestClient, setup_data: dict):
    res = client.get(
        "/admin/nakes",
        headers={"Authorization": f"Bearer {setup_data['admin_token']}"},
    )
    assert res.status_code == 200
    data = res.json()

    for nakes in data:
        assert "facility_id" in nakes
        assert "facility_name" in nakes
        assert nakes["facility_id"] is not None
        assert nakes["facility_name"] is not None

    # Verify correct mapping
    assert data[0]["facility_name"] == "Puskesmas Cimenyan"
    assert data[1]["facility_name"] == "Puskesmas Antapani"


# =========================================================
# 8. Password/password_hash never appears in response
# =========================================================


def test_no_password_in_facilities_response(client: TestClient, setup_data: dict):
    res = client.get(
        "/admin/facilities",
        headers={"Authorization": f"Bearer {setup_data['admin_token']}"},
    )
    assert res.status_code == 200
    raw = res.text
    assert "password" not in raw.lower()
    assert "password_hash" not in raw.lower()


def test_no_password_in_nakes_response(client: TestClient, setup_data: dict):
    res = client.get(
        "/admin/nakes",
        headers={"Authorization": f"Bearer {setup_data['admin_token']}"},
    )
    assert res.status_code == 200
    data = res.json()
    for nakes in data:
        assert "password" not in nakes
        assert "password_hash" not in nakes
    raw = res.text
    assert "password_hash" not in raw.lower()


# =========================================================
# 9. POST /auth/nakes still works
# =========================================================


def test_post_auth_nakes_still_works(client: TestClient, setup_data: dict):
    res = client.post(
        "/auth/nakes",
        json={
            "username": "new_nakes",
            "email": "new_nakes@test.id",
            "password": "newpass1234",
            "facility_id": setup_data["facility_a_id"],
        },
        headers={"Authorization": f"Bearer {setup_data['admin_token']}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "new_nakes"
    assert data["role"] == "nakes"
    assert "password" not in data
    assert "password_hash" not in data


# =========================================================
# 10. Unauthenticated requests are rejected
# =========================================================


def test_unauthenticated_cannot_get_facilities(client: TestClient, setup_data: dict):
    res = client.get("/admin/facilities")
    assert res.status_code in [401, 403]


def test_unauthenticated_cannot_get_nakes(client: TestClient, setup_data: dict):
    res = client.get("/admin/nakes")
    assert res.status_code in [401, 403]
