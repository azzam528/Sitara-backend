import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecretkeyfornotificationserialization"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:5173"
os.environ["ACTIVATION_BASE_URL"] = "https://activation.test.local"

from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.patient import Patient
from app.models.health_facility import HealthFacility
from app.models.notification import (
    Notification,
    NotificationType,
    NotificationReferenceType,
)
from app.models import (  # noqa: F401
    Treatment,
    Medicine,
    MedicineSchedule,
    VideoVerification,
    Complaint,
    RefillRequest,
    ControlSchedule,
    ActivationToken,
    FaceEmbedding,
    FaceVerification,
    DailyMedication,
)
from app.schemas.notification import NotificationResponse
from app.main import app

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
client = TestClient(app)


def create_test_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.fixture(autouse=True)
def setup_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    facility = HealthFacility(
        name="Puskesmas Tebet",
        address="Jl. Tebet No. 1",
        phone="021-1234567",
        is_active=True,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    patient_user = User(
        username="6281234567890",
        password_hash="hashedpass",
        role="patient",
        facility_id=facility.id,
        is_active=True,
        must_change_password=False,
    )
    db.add(patient_user)
    db.commit()
    db.refresh(patient_user)

    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def test_schema_created_at_naive_utc_serializes_with_z():
    naive_dt = datetime(2026, 8, 31, 1, 33, 55, 828871)
    nr = NotificationResponse(
        id=1,
        user_id=1,
        title="Test",
        message="Test Message",
        type=NotificationType.MEDICINE,
        is_read=False,
        is_active=True,
        created_at=naive_dt,
        updated_at=naive_dt,
    )
    json_str = nr.model_dump_json()
    assert '"created_at":"2026-08-31T01:33:55.828871Z"' in json_str


def test_schema_updated_at_naive_utc_serializes_with_z():
    naive_dt = datetime(2026, 8, 31, 1, 33, 55, 828871)
    nr = NotificationResponse(
        id=1,
        user_id=1,
        title="Test",
        message="Test Message",
        type=NotificationType.MEDICINE,
        is_read=False,
        is_active=True,
        created_at=naive_dt,
        updated_at=naive_dt,
    )
    json_str = nr.model_dump_json()
    assert '"updated_at":"2026-08-31T01:33:55.828871Z"' in json_str


def test_timezone_aware_normalizes_to_utc_without_double_conversion():
    wib_tz = timezone(timedelta(hours=7))
    aware_dt = datetime(2026, 8, 31, 8, 33, 55, 828871, tzinfo=wib_tz)
    nr = NotificationResponse(
        id=1,
        user_id=1,
        title="Test",
        message="Test Message",
        type=NotificationType.MEDICINE,
        is_read=False,
        is_active=True,
        created_at=aware_dt,
        updated_at=aware_dt,
    )
    json_str = nr.model_dump_json()
    assert '"created_at":"2026-08-31T01:33:55.828871Z"' in json_str
    assert '"updated_at":"2026-08-31T01:33:55.828871Z"' in json_str


def test_get_notifications_all_types_serialize_with_z():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "6281234567890").first()
    assert user is not None

    notifications_data = [
        (NotificationType.MEDICINE, NotificationReferenceType.MEDICINE_SCHEDULE, 101, "Waktunya Minum Obat"),
        (NotificationType.VIDEO, NotificationReferenceType.VIDEO_VERIFICATION, 202, "VOT Terverifikasi"),
        (NotificationType.COMPLAINT, NotificationReferenceType.COMPLAINT, 303, "Balasan Keluhan"),
        (NotificationType.REFILL, NotificationReferenceType.REFILL, 404, "Permintaan Isi Ulang"),
        (NotificationType.CONTROL, NotificationReferenceType.CONTROL_SCHEDULE, 505, "Jadwal Kontrol"),
    ]

    fixed_utc = datetime(2026, 8, 31, 1, 33, 55)

    user_id = user.id
    for notif_type, ref_type, ref_id, title in notifications_data:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=f"Message for {notif_type.value}",
            type=notif_type,
            reference_type=ref_type,
            reference_id=ref_id,
            is_read=False,
            is_active=True,
            created_at=fixed_utc,
            updated_at=fixed_utc,
        )
        db.add(notif)
    db.commit()
    db.close()

    token = create_test_token(user_id, "patient")
    response = client.get("/notifications", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    items = response.json()
    assert len(items) == 5

    type_to_item = {item["type"]: item for item in items}

    # 4. Medicine notification timestamp
    med_item = type_to_item["medicine"]
    assert med_item["created_at"] == "2026-08-31T01:33:55Z"
    assert med_item["updated_at"] == "2026-08-31T01:33:55Z"
    assert med_item["created_at"].endswith("Z")

    # 5. VOT notification timestamp
    vot_item = type_to_item["video"]
    assert vot_item["created_at"] == "2026-08-31T01:33:55Z"
    assert vot_item["updated_at"] == "2026-08-31T01:33:55Z"
    assert vot_item["created_at"].endswith("Z")

    # 6. Complaint notification timestamp
    comp_item = type_to_item["complaint"]
    assert comp_item["created_at"] == "2026-08-31T01:33:55Z"
    assert comp_item["updated_at"] == "2026-08-31T01:33:55Z"
    assert comp_item["created_at"].endswith("Z")

    # 7. Refill notification timestamp
    refill_item = type_to_item["refill"]
    assert refill_item["created_at"] == "2026-08-31T01:33:55Z"
    assert refill_item["updated_at"] == "2026-08-31T01:33:55Z"
    assert refill_item["created_at"].endswith("Z")

    # 8. Control notification timestamp
    ctrl_item = type_to_item["control"]
    assert ctrl_item["created_at"] == "2026-08-31T01:33:55Z"
    assert ctrl_item["updated_at"] == "2026-08-31T01:33:55Z"
    assert ctrl_item["created_at"].endswith("Z")


def test_get_single_notification_and_mark_read_serializes_with_z():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "6281234567890").first()
    user_id = user.id
    fixed_utc = datetime(2026, 8, 31, 1, 33, 55, 123456)
    notif = Notification(
        user_id=user_id,
        title="Single Notif",
        message="Detail test",
        type=NotificationType.MEDICINE,
        reference_type=NotificationReferenceType.MEDICINE_SCHEDULE,
        reference_id=1,
        is_read=False,
        is_active=True,
        created_at=fixed_utc,
        updated_at=fixed_utc,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    notif_id = notif.id
    db.close()

    token = create_test_token(user_id, "patient")
    headers = {"Authorization": f"Bearer {token}"}

    # GET /{id}
    res_get = client.get(f"/notifications/{notif_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["created_at"] == "2026-08-31T01:33:55.123456Z"
    assert res_get.json()["created_at"].endswith("Z")

    # PUT /{id}/read
    res_read = client.put(f"/notifications/{notif_id}/read", headers=headers)
    assert res_read.status_code == 200
    assert res_read.json()["created_at"].endswith("Z")
    assert res_read.json()["is_read"] is True

    # PUT /read-all (add an unread notification first)
    db = TestingSessionLocal()
    notif2 = Notification(
        user_id=user_id,
        title="Second Notif",
        message="Read all test",
        type=NotificationType.CONTROL,
        reference_type=NotificationReferenceType.CONTROL_SCHEDULE,
        reference_id=2,
        is_read=False,
        is_active=True,
        created_at=fixed_utc,
        updated_at=fixed_utc,
    )
    db.add(notif2)
    db.commit()
    db.close()

    res_read_all = client.put("/notifications/read-all", headers=headers)
    assert res_read_all.status_code == 200
    all_read = res_read_all.json()
    assert len(all_read) == 1
    assert all_read[0]["created_at"].endswith("Z")
