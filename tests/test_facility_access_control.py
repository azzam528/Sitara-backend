import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from datetime import date, time, datetime

from app.main import app
from app.core.database import get_db, Base
from app.core.security import create_access_token

from app.models.user import User
from app.models.health_facility import HealthFacility
from app.models.patient import Patient, GenderEnum
from app.models.treatment import Treatment, TreatmentPhase, RegimenEnum, TreatmentStatus
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.refill_request import RefillRequest, RefillRequestStatus
from app.models.complaint import Complaint, ComplaintStatus
from app.models.video_verification import VideoVerification, VerificationStatus
from app.models.control_schedule import ControlSchedule, ControlScheduleStatus
from app.models.face_verification import FaceVerification, FaceVerificationStatus
from app.models.notification import Notification, NotificationType, NotificationReferenceType

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
    patient_a = Patient(user_id=user_pa.id, full_name="PA", medical_record_number="M1", nik="1", birth_date=date(1990,1,1), gender=GenderEnum.MALE, phone="1", address="A", occupation="W", pmo_name="P", pmo_phone="1", is_active=True)
    patient_b = Patient(user_id=user_pb.id, full_name="PB", medical_record_number="M2", nik="2", birth_date=date(1990,1,1), gender=GenderEnum.MALE, phone="2", address="B", occupation="W", pmo_name="P", pmo_phone="2", is_active=True)
    db_session.add_all([patient_a, patient_b])
    db_session.commit()

    # Treatments A & B
    treatment_a = Treatment(patient_id=patient_a.id, diagnosis_date=date(2023,1,1), therapy_start_date=date(2023,1,2), therapy_end_date=date(2023,7,2), phase=TreatmentPhase.INTENSIVE, regimen=RegimenEnum.CATEGORY_1, status=TreatmentStatus.ACTIVE, doctor_name="Dr A", is_active=True)
    treatment_b = Treatment(patient_id=patient_b.id, diagnosis_date=date(2023,1,1), therapy_start_date=date(2023,1,2), therapy_end_date=date(2023,7,2), phase=TreatmentPhase.INTENSIVE, regimen=RegimenEnum.CATEGORY_1, status=TreatmentStatus.ACTIVE, doctor_name="Dr B", is_active=True)
    db_session.add_all([treatment_a, treatment_b])
    db_session.commit()

    # Medicine
    med = Medicine(code="M1", name="Med 1", category="Antibiotic", strength="500", unit="Tab", is_active=True)
    db_session.add(med)
    db_session.commit()

    # Schedules A & B
    schedule_a = MedicineSchedule(treatment_id=treatment_a.id, medicine_id=med.id, dosage="1x1", quantity_initial=30, quantity_remaining=30, drink_time=time(8,0))
    schedule_b = MedicineSchedule(treatment_id=treatment_b.id, medicine_id=med.id, dosage="1x1", quantity_initial=30, quantity_remaining=30, drink_time=time(8,0))
    db_session.add_all([schedule_a, schedule_b])
    db_session.commit()

    # Refills A & B
    refill_a = RefillRequest(treatment_id=treatment_a.id, medicine_id=med.id, quantity=30, reason="Almost empty", status=RefillRequestStatus.PENDING)
    refill_b = RefillRequest(treatment_id=treatment_b.id, medicine_id=med.id, quantity=30, reason="Almost empty", status=RefillRequestStatus.PENDING)
    db_session.add_all([refill_a, refill_b])
    db_session.commit()

    # Complaints A & B
    complaint_a = Complaint(treatment_id=treatment_a.id, category="G", description="Desc", status=ComplaintStatus.PENDING)
    complaint_b = Complaint(treatment_id=treatment_b.id, category="G", description="Desc", status=ComplaintStatus.PENDING)
    db_session.add_all([complaint_a, complaint_b])
    db_session.commit()

    # Face Verifications A & B
    face_a = FaceVerification(patient_id=patient_a.id, medicine_schedule_id=schedule_a.id, similarity_score=0.9, threshold=0.8, status=FaceVerificationStatus.VERIFIED, captured_at=datetime.utcnow())
    face_b = FaceVerification(patient_id=patient_b.id, medicine_schedule_id=schedule_b.id, similarity_score=0.9, threshold=0.8, status=FaceVerificationStatus.VERIFIED, captured_at=datetime.utcnow())
    db_session.add_all([face_a, face_b])
    db_session.commit()

    # Video Verifications A & B
    video_a = VideoVerification(medicine_schedule_id=schedule_a.id, face_verification_id=face_a.id, verification_date=date(2023,1,1), video_path="a.mp4", file_name="a.mp4", mime_type="video/mp4", file_size=10, thumbnail_path="t.jpg", status=VerificationStatus.PENDING)
    video_b = VideoVerification(medicine_schedule_id=schedule_b.id, face_verification_id=face_b.id, verification_date=date(2023,1,1), video_path="b.mp4", file_name="b.mp4", mime_type="video/mp4", file_size=10, thumbnail_path="t.jpg", status=VerificationStatus.PENDING)
    db_session.add_all([video_a, video_b])
    db_session.commit()

    # Control Schedules A & B
    control_a = ControlSchedule(treatment_id=treatment_a.id, control_date=date(2023,1,15), control_time=time(10,0), status=ControlScheduleStatus.PENDING)
    control_b = ControlSchedule(treatment_id=treatment_b.id, control_date=date(2023,1,15), control_time=time(10,0), status=ControlScheduleStatus.PENDING)
    db_session.add_all([control_a, control_b])
    db_session.commit()

    return {
        "nakes_a_token": create_access_token({"sub": str(nakes_a.id)}),
        "nakes_b_token": create_access_token({"sub": str(nakes_b.id)}),
        "patient_a_token": create_access_token({"sub": str(user_pa.id)}),
        "patient_b_token": create_access_token({"sub": str(user_pb.id)}),
        "nakes_a_id": nakes_a.id,
        "nakes_b_id": nakes_b.id,
        "patient_a_id": patient_a.id,
        "patient_b_id": patient_b.id,
        "treatment_a_id": treatment_a.id,
        "treatment_b_id": treatment_b.id,
        "medicine_id": med.id,
        "schedule_a_id": schedule_a.id,
        "schedule_b_id": schedule_b.id,
        "refill_a_id": refill_a.id,
        "refill_b_id": refill_b.id,
        "complaint_a_id": complaint_a.id,
        "complaint_b_id": complaint_b.id,
        "video_a_id": video_a.id,
        "video_b_id": video_b.id,
        "control_a_id": control_a.id,
        "control_b_id": control_b.id,
        "face_a_id": face_a.id,
        "face_b_id": face_b.id,
    }

# =========================================================
# TESTS (GET - READ OPERATIONS)
# =========================================================

def test_facility_isolation_treatment(client: TestClient, setup_data: dict):
    res_a = client.get(f"/treatments/{setup_data['treatment_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_a_token']}"})
    assert res_a.status_code == 200
    res_b = client.get(f"/treatments/{setup_data['treatment_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_b.status_code == 404

def test_facility_isolation_medicine_schedule(client: TestClient, setup_data: dict):
    res_a = client.get(f"/medicine-schedules/{setup_data['schedule_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_a_token']}"})
    assert res_a.status_code == 200
    res_b = client.get(f"/medicine-schedules/{setup_data['schedule_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_b.status_code == 404

def test_facility_isolation_refill(client: TestClient, setup_data: dict):
    res_a = client.get(f"/refills/{setup_data['refill_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_a_token']}"})
    assert res_a.status_code == 200
    res_b = client.get(f"/refills/{setup_data['refill_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_b.status_code == 404

def test_facility_isolation_complaint(client: TestClient, setup_data: dict):
    res_a = client.get(f"/complaints/{setup_data['complaint_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_a_token']}"})
    assert res_a.status_code == 200
    res_b = client.get(f"/complaints/{setup_data['complaint_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_b.status_code == 404

def test_facility_isolation_control_schedule(client: TestClient, setup_data: dict):
    res_a = client.get(f"/control-schedules/{setup_data['control_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_a_token']}"})
    assert res_a.status_code == 200
    res_b = client.get(f"/control-schedules/{setup_data['control_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_b.status_code == 404

def test_facility_isolation_dashboard(client: TestClient, setup_data: dict):
    res_a = client.get("/dashboard", headers={"Authorization": f"Bearer {setup_data['nakes_a_token']}"})
    assert res_a.status_code == 200
    assert res_a.json()["summary"]["active_patients"] == 1 
    res_b = client.get("/dashboard", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_b.status_code == 200
    assert res_b.json()["summary"]["active_patients"] == 1 

# =========================================================
# TESTS (WRITE OPERATIONS - ISOLATION)
# =========================================================

def test_facility_isolation_treatment_write(client: TestClient, setup_data: dict):
    # Nakes B cannot POST treatment using patient_id from Facility A.
    res_post = client.post(
        "/treatments",
        json={"patient_id": setup_data["patient_a_id"], "diagnosis_date": "2023-01-01", "therapy_start_date": "2023-01-02", "therapy_end_date": "2023-07-02", "phase": "intensive", "regimen": "category_1", "doctor_name": "Dr A"},
        headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"}
    )
    assert res_post.status_code in [403, 404]

    # Nakes B cannot PUT Treatment A.
    res_put = client.put(
        f"/treatments/{setup_data['treatment_a_id']}",
        json={"diagnosis_date": "2023-01-01", "therapy_start_date": "2023-01-02", "therapy_end_date": "2023-07-02", "phase": "intensive", "regimen": "category_1", "status": "active", "doctor_name": "Dr B"},
        headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"}
    )
    assert res_put.status_code in [403, 404]

    # Nakes B cannot DELETE Treatment A.
    res_del = client.delete(f"/treatments/{setup_data['treatment_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_del.status_code in [403, 404]

def test_facility_isolation_medicine_schedule_write(client: TestClient, setup_data: dict):
    # Nakes B cannot POST a schedule using Treatment A.
    res_post = client.post(
        "/medicine-schedules",
        json={"treatment_id": setup_data["treatment_a_id"], "medicine_id": setup_data["medicine_id"], "dosage": "1x1", "quantity_initial": 30, "quantity_remaining": 30, "drink_time": "08:00"},
        headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"}
    )
    assert res_post.status_code in [403, 404]

    # Nakes B cannot PUT Schedule A.
    res_put = client.put(
        f"/medicine-schedules/{setup_data['schedule_a_id']}",
        json={"dosage": "2x1", "quantity_initial": 30, "quantity_remaining": 30, "drink_time": "08:00"},
        headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"}
    )
    assert res_put.status_code in [403, 404]

    # Nakes B cannot DELETE Schedule A.
    res_del = client.delete(f"/medicine-schedules/{setup_data['schedule_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_del.status_code in [403, 404]

def test_facility_isolation_refill_write(client: TestClient, setup_data: dict):
    # Nakes B cannot PUT Refill A.
    res_put = client.put(
        f"/refills/{setup_data['refill_a_id']}",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"}
    )
    assert res_put.status_code in [403, 404]

    # Nakes B cannot DELETE Refill A.
    res_del = client.delete(f"/refills/{setup_data['refill_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_del.status_code in [403, 404]

def test_facility_isolation_complaint_write(client: TestClient, setup_data: dict):
    # Nakes B cannot PUT Complaint A.
    res_put = client.put(
        f"/complaints/{setup_data['complaint_a_id']}",
        json={"status": "resolved"},
        headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"}
    )
    assert res_put.status_code in [403, 404]

    # Nakes B cannot DELETE Complaint A.
    res_del = client.delete(f"/complaints/{setup_data['complaint_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_del.status_code in [403, 404]

def test_facility_isolation_video_verification_write(client: TestClient, setup_data: dict):
    # Nakes B cannot PUT Video A.
    res_put = client.put(
        f"/video-verifications/{setup_data['video_a_id']}",
        json={"status": "verified"},
        headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"}
    )
    assert res_put.status_code in [403, 404]

    # Nakes B cannot DELETE Video A.
    res_del = client.delete(f"/video-verifications/{setup_data['video_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_del.status_code in [403, 404]

def test_facility_isolation_control_schedule_write(client: TestClient, setup_data: dict):
    # Nakes B cannot PUT Control Schedule A.
    res_put = client.put(
        f"/control-schedules/{setup_data['control_a_id']}",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"}
    )
    assert res_put.status_code in [403, 404]

    # Nakes B cannot DELETE Control Schedule A.
    res_del = client.delete(f"/control-schedules/{setup_data['control_a_id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_del.status_code in [403, 404]

# =========================================================
# TESTS (PATIENT OWNERSHIP ISOLATION)
# =========================================================

def test_patient_ownership_isolation(client: TestClient, setup_data: dict):
    # Patient A cannot access Patient B's treatment
    res = client.get(f"/treatments/{setup_data['treatment_b_id']}", headers={"Authorization": f"Bearer {setup_data['patient_a_token']}"})
    assert res.status_code in [403, 404]

    # Patient A cannot access Patient B's refill
    res = client.get(f"/refills/my", headers={"Authorization": f"Bearer {setup_data['patient_a_token']}"})
    # This just returns my refills, which is secure. Let's explicitly test posting a refill on Treatment B
    res = client.post("/refills/my", json={"treatment_id": setup_data['treatment_b_id'], "medicine_id": setup_data["medicine_id"], "quantity": 10, "reason": "empty"}, headers={"Authorization": f"Bearer {setup_data['patient_a_token']}"})
    assert res.status_code in [403, 404]

    # Patient A cannot perform face verification using medicine_schedule_id belonging to Patient B.
    res = client.post("/face-verification", json={"medicine_schedule_id": setup_data['schedule_b_id'], "image_base64": "dummy"}, headers={"Authorization": f"Bearer {setup_data['patient_a_token']}"})
    assert res.status_code in [403, 404]

def test_facility_isolation_notification_routing(client: TestClient, db_session: Session, setup_data: dict):
    # Patient A creates complaint
    client.post(
        "/complaints/my",
        json={"treatment_id": setup_data["treatment_a_id"], "category": "General", "description": "Desc"},
        headers={"Authorization": f"Bearer {setup_data['patient_a_token']}"}
    )

    # Nakes A receives it
    na = db_session.query(Notification).filter(Notification.user_id == setup_data["nakes_a_id"]).all()
    assert len(na) == 1

    # Nakes B DOES NOT receive it
    nb = db_session.query(Notification).filter(Notification.user_id == setup_data["nakes_b_id"]).all()
    assert len(nb) == 0

def test_patient_refill_pickup_facility(client: TestClient, setup_data: dict):
    # Patient A creates a refill request
    res_create = client.post("/refills/my", json={
        "treatment_id": setup_data["treatment_a_id"],
        "medicine_id": setup_data["medicine_id"],
        "quantity": 10,
        "reason": "Test"
    }, headers={"Authorization": f"Bearer {setup_data['patient_a_token']}"})
    assert res_create.status_code == 200

    # Patient A gets their refills
    res_a = client.get("/refills/my", headers={"Authorization": f"Bearer {setup_data['patient_a_token']}"})
    assert res_a.status_code == 200
    data_a = res_a.json()
    print("DEBUG DATA_A:", data_a)
    assert len(data_a) > 0
    # pickup facility should be Facility A
    assert data_a[0]["pickup_facility"]["name"] == "Facility A"
    assert data_a[0]["pickup_facility"]["latitude"] == -6.873
    assert data_a[0]["pickup_facility"]["longitude"] == 107.65

    # Patient B gets their refills
    res_b = client.get("/refills/my", headers={"Authorization": f"Bearer {setup_data['patient_b_token']}"})
    assert res_b.status_code == 200
    data_b = res_b.json()
    # pickup facility should be Facility B
    assert data_b[0]["pickup_facility"]["name"] == "Facility B"
    assert data_b[0]["pickup_facility"]["latitude"] == -6.9

    # Nakes A gets refill of Patient A, should have Facility A
    res_nakes_a = client.get(f"/refills/{data_a[0]['id']}", headers={"Authorization": f"Bearer {setup_data['nakes_a_token']}"})
    assert res_nakes_a.status_code == 200
    assert res_nakes_a.json()["pickup_facility"]["name"] == "Facility A"

    # Nakes B tries to get refill of Patient A, should be forbidden
    res_nakes_b = client.get(f"/refills/{data_a[0]['id']}", headers={"Authorization": f"Bearer {setup_data['nakes_b_token']}"})
    assert res_nakes_b.status_code == 404
