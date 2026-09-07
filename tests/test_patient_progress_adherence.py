import os
import sys
import uuid
from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.daily_medication import (
    DailyMedication,
    DailyMedicationStatus,
    VotStep,
)
from app.models.health_facility import HealthFacility
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.patient import GenderEnum, Patient
from app.models.treatment import (
    RegimenEnum,
    Treatment,
    TreatmentPhase,
    TreatmentStatus,
)
from app.models.user import User
from app.models.video_verification import VerificationStatus, VideoVerification
from app.services.daily_medication_service import today_in_jakarta

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_tables():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db: Session):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def facility(db: Session):
    item = HealthFacility(name="Puskesmas Progress", address="Jl. Progress", is_active=True)
    db.add(item)
    db.commit()
    return item


def create_patient(
    db: Session,
    facility_id: int,
    schedule_times: list[time] | None = None,
    therapy_start_offset_days: int = 0,
    therapy_end_offset_days: int = 60,
):
    """Buat 1 pasien + treatment + schedule dan kembalikan konteksnya.

    therapy_start_offset_days = 0 membuat backfill occurrence menjadi no-op,
    sehingga test dapat mengontrol occurrence secara eksplisit.
    """
    if schedule_times is None:
        schedule_times = [time(8, 0)]

    today = today_in_jakarta()
    uid = uuid.uuid4().hex[:8]

    user = User(
        username=f"pat_{uid}",
        email=f"pat_{uid}@sitara.com",
        password_hash="fakehash",
        role="patient",
        facility_id=facility_id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    patient = Patient(
        user_id=user.id,
        medical_record_number=f"RM-{uid}",
        full_name=f"Pasien {uid}",
        nik=f"32{uid[:6]}00000000",
        birth_date=date(1990, 1, 1),
        gender=GenderEnum.MALE,
        phone="628111111111",
        address="Jl. Sehat",
        occupation="Karyawan",
        pmo_name="PMO",
        pmo_phone="628222222222",
        is_active=True,
    )
    db.add(patient)
    db.commit()

    treatment = Treatment(
        patient_id=patient.id,
        diagnosis_date=today - timedelta(days=1),
        therapy_start_date=today + timedelta(days=therapy_start_offset_days),
        therapy_end_date=today + timedelta(days=therapy_end_offset_days),
        phase=TreatmentPhase.INTENSIVE,
        regimen=RegimenEnum.CATEGORY_1,
        status=TreatmentStatus.ACTIVE,
        doctor_name="dr. Paru",
        is_active=True,
    )
    db.add(treatment)
    db.commit()

    medicine = Medicine(
        code=f"OAT-{uid}",
        name=f"FDC-{uid}",
        category="Kategori 1",
        strength="FDC",
        unit="Tablet",
        is_active=True,
    )
    db.add(medicine)
    db.commit()

    schedules = []
    for drink_time in schedule_times:
        schedule = MedicineSchedule(
            treatment_id=treatment.id,
            medicine_id=medicine.id,
            dosage="3 tablet",
            quantity_initial=60,
            quantity_remaining=60,
            drink_time=drink_time,
            is_active=True,
        )
        db.add(schedule)
        schedules.append(schedule)
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": "patient", "facility_id": facility_id})

    return {
        "user": user,
        "patient": patient,
        "treatment": treatment,
        "medicine": medicine,
        "schedules": schedules,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def create_nakes(db: Session, facility_id: int):
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"nakes_{uid}",
        email=f"nakes_{uid}@sitara.com",
        password_hash="fakehash",
        role="nakes",
        facility_id=facility_id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": "nakes", "facility_id": facility_id})
    return {"user": user, "headers": {"Authorization": f"Bearer {token}"}}


def add_occurrence(
    db: Session,
    schedule: MedicineSchedule,
    scheduled_date: date,
    status: DailyMedicationStatus,
    **kwargs,
) -> DailyMedication:
    occurrence = DailyMedication(
        medicine_schedule_id=schedule.id,
        scheduled_date=scheduled_date,
        scheduled_time=schedule.drink_time,
        status=status,
        is_active=True,
        **kwargs,
    )
    db.add(occurrence)
    db.commit()
    return occurrence


def get_progress(client: TestClient, context: dict):
    response = client.get("/medications/progress", headers=context["headers"])
    assert response.status_code == 200
    return response.json()


# =====================================================
# 1-3. FINAL OUTCOME PER OCCURRENCE
# =====================================================


def test_verified_occurrence_counts_as_success(client, db, facility):
    context = create_patient(db, facility.id)
    yesterday = today_in_jakarta() - timedelta(days=1)
    add_occurrence(db, context["schedules"][0], yesterday, DailyMedicationStatus.VERIFIED)

    body = get_progress(client, context)

    assert body["successful_occurrences"] == 1
    assert body["failed_occurrences"] == 0
    assert body["final_due_occurrences"] == 1
    assert body["adherence_percentage"] == 100.0


def test_rejected_occurrence_counts_as_failure(client, db, facility):
    context = create_patient(db, facility.id)
    yesterday = today_in_jakarta() - timedelta(days=1)
    add_occurrence(db, context["schedules"][0], yesterday, DailyMedicationStatus.REJECTED)

    body = get_progress(client, context)

    assert body["successful_occurrences"] == 0
    assert body["failed_occurrences"] == 1
    assert body["final_due_occurrences"] == 1
    assert body["adherence_percentage"] == 0.0


def test_missed_occurrence_counts_as_failure(client, db, facility):
    context = create_patient(db, facility.id)
    yesterday = today_in_jakarta() - timedelta(days=1)
    add_occurrence(db, context["schedules"][0], yesterday, DailyMedicationStatus.MISSED)

    body = get_progress(client, context)

    assert body["failed_occurrences"] == 1
    assert body["final_due_occurrences"] == 1
    assert body["adherence_percentage"] == 0.0


# =====================================================
# 4. NEEDS_REVIEW BELUM FINAL
# =====================================================


def test_needs_review_is_not_part_of_final_denominator(client, db, facility):
    context = create_patient(db, facility.id)
    schedule = context["schedules"][0]
    today = today_in_jakarta()

    for offset in range(1, 9):
        add_occurrence(
            db,
            schedule,
            today - timedelta(days=offset),
            DailyMedicationStatus.VERIFIED,
        )
    add_occurrence(db, schedule, today - timedelta(days=9), DailyMedicationStatus.REJECTED)
    add_occurrence(db, schedule, today - timedelta(days=10), DailyMedicationStatus.NEEDS_REVIEW)

    body = get_progress(client, context)

    assert body["successful_occurrences"] == 8
    assert body["failed_occurrences"] == 1
    assert body["pending_review_occurrences"] == 1
    assert body["final_due_occurrences"] == 9
    assert body["adherence_percentage"] == 88.9


# =====================================================
# 5-6. OCCURRENCE BELUM JATUH TEMPO
# =====================================================


def test_future_occurrence_is_not_counted(client, db, facility):
    context = create_patient(db, facility.id)
    schedule = context["schedules"][0]
    today = today_in_jakarta()

    add_occurrence(db, schedule, today - timedelta(days=1), DailyMedicationStatus.VERIFIED)
    add_occurrence(db, schedule, today + timedelta(days=1), DailyMedicationStatus.PENDING)
    add_occurrence(db, schedule, today + timedelta(days=2), DailyMedicationStatus.VERIFIED)

    body = get_progress(client, context)

    assert body["successful_occurrences"] == 1
    assert body["final_due_occurrences"] == 1
    assert body["adherence_percentage"] == 100.0


def test_in_progress_today_is_not_final(client, db, facility):
    context = create_patient(db, facility.id)
    schedule = context["schedules"][0]
    today = today_in_jakarta()

    add_occurrence(db, schedule, today, DailyMedicationStatus.IN_PROGRESS)

    body = get_progress(client, context)

    assert body["final_due_occurrences"] == 0
    assert body["adherence_percentage"] is None

    occurrence = (
        db.query(DailyMedication)
        .filter(DailyMedication.scheduled_date == today)
        .first()
    )
    assert occurrence.status == DailyMedicationStatus.IN_PROGRESS


# =====================================================
# 7-8. AUTOMATIC MISSED
# =====================================================


def test_pending_occurrence_past_due_becomes_missed(client, db, facility):
    context = create_patient(db, facility.id, therapy_start_offset_days=-1)
    schedule = context["schedules"][0]
    yesterday = today_in_jakarta() - timedelta(days=1)

    occurrence = add_occurrence(db, schedule, yesterday, DailyMedicationStatus.PENDING)

    body = get_progress(client, context)

    db.refresh(occurrence)
    assert occurrence.status == DailyMedicationStatus.MISSED
    assert body["failed_occurrences"] == 1
    assert body["adherence_percentage"] == 0.0


def test_occurrence_never_created_is_recorded_as_missed(client, db, facility):
    context = create_patient(db, facility.id, therapy_start_offset_days=-2)
    schedule = context["schedules"][0]
    today = today_in_jakarta()

    assert db.query(DailyMedication).count() == 0

    body = get_progress(client, context)

    occurrences = (
        db.query(DailyMedication)
        .filter(DailyMedication.medicine_schedule_id == schedule.id)
        .order_by(DailyMedication.scheduled_date)
        .all()
    )
    assert [item.scheduled_date for item in occurrences] == [
        today - timedelta(days=2),
        today - timedelta(days=1),
    ]
    assert all(item.status == DailyMedicationStatus.MISSED for item in occurrences)
    assert all(item.scheduled_time == schedule.drink_time for item in occurrences)

    assert body["failed_occurrences"] == 2
    assert body["final_due_occurrences"] == 2
    assert body["adherence_percentage"] == 0.0


def test_today_occurrence_is_never_backfilled_or_missed(client, db, facility):
    context = create_patient(db, facility.id, therapy_start_offset_days=-1)
    today = today_in_jakarta()

    get_progress(client, context)

    assert (
        db.query(DailyMedication)
        .filter(DailyMedication.scheduled_date >= today)
        .count()
        == 0
    )


def test_progress_call_is_idempotent(client, db, facility):
    context = create_patient(db, facility.id, therapy_start_offset_days=-3)

    first = get_progress(client, context)
    count_after_first = db.query(DailyMedication).count()

    second = get_progress(client, context)

    assert db.query(DailyMedication).count() == count_after_first
    assert first == second


# =====================================================
# 9-11. DATA INTEGRITY
# =====================================================


def test_verified_is_never_downgraded_to_missed(client, db, facility):
    context = create_patient(db, facility.id, therapy_start_offset_days=-1)
    yesterday = today_in_jakarta() - timedelta(days=1)
    occurrence = add_occurrence(
        db,
        context["schedules"][0],
        yesterday,
        DailyMedicationStatus.VERIFIED,
        vot_step=VotStep.VERIFIED,
        completed_at=None,
        attempt_count=2,
        failure_reason="DRINKING_TIMEOUT",
    )

    get_progress(client, context)

    db.refresh(occurrence)
    assert occurrence.status == DailyMedicationStatus.VERIFIED
    assert occurrence.vot_step == VotStep.VERIFIED
    assert occurrence.attempt_count == 2
    assert occurrence.failure_reason == "DRINKING_TIMEOUT"


def test_rejected_is_never_changed_to_missed(client, db, facility):
    context = create_patient(db, facility.id, therapy_start_offset_days=-1)
    yesterday = today_in_jakarta() - timedelta(days=1)
    occurrence = add_occurrence(
        db,
        context["schedules"][0],
        yesterday,
        DailyMedicationStatus.REJECTED,
        attempt_count=3,
        failure_reason="DRINKING_AMBIGUOUS",
    )

    get_progress(client, context)

    db.refresh(occurrence)
    assert occurrence.status == DailyMedicationStatus.REJECTED
    assert occurrence.attempt_count == 3
    assert occurrence.failure_reason == "DRINKING_AMBIGUOUS"


def test_needs_review_is_never_changed_to_missed(client, db, facility):
    context = create_patient(db, facility.id, therapy_start_offset_days=-1)
    yesterday = today_in_jakarta() - timedelta(days=1)

    video = VideoVerification(
        medicine_schedule_id=context["schedules"][0].id,
        verification_date=yesterday,
        video_path="uploads/vot_videos/dummy.mp4",
        file_name="dummy.mp4",
        mime_type="video/mp4",
        file_size=1024,
        status=VerificationStatus.PENDING,
        is_active=True,
    )
    db.add(video)
    db.commit()

    occurrence = add_occurrence(
        db,
        context["schedules"][0],
        yesterday,
        DailyMedicationStatus.NEEDS_REVIEW,
        attempt_count=3,
        failure_reason="FACE_VERIFICATION_FAILED",
        video_verification_id=video.id,
    )

    body = get_progress(client, context)

    db.refresh(occurrence)
    assert occurrence.status == DailyMedicationStatus.NEEDS_REVIEW
    assert occurrence.video_verification_id == video.id
    assert occurrence.attempt_count == 3
    assert occurrence.failure_reason == "FACE_VERIFICATION_FAILED"
    assert body["pending_review_occurrences"] == 1
    assert body["final_due_occurrences"] == 0
    assert body["adherence_percentage"] is None


# =====================================================
# 12-13. KEPUTUSAN NAKES
# =====================================================


def setup_review_case(db: Session, facility_id: int):
    context = create_patient(db, facility_id)
    schedule = context["schedules"][0]
    today = today_in_jakarta()

    add_occurrence(db, schedule, today - timedelta(days=1), DailyMedicationStatus.VERIFIED)

    review_date = today - timedelta(days=2)
    video = VideoVerification(
        medicine_schedule_id=schedule.id,
        verification_date=review_date,
        video_path="uploads/vot_videos/review.mp4",
        file_name="review.mp4",
        mime_type="video/mp4",
        file_size=2048,
        status=VerificationStatus.PENDING,
        is_active=True,
    )
    db.add(video)
    db.commit()

    occurrence = add_occurrence(
        db,
        schedule,
        review_date,
        DailyMedicationStatus.NEEDS_REVIEW,
        attempt_count=3,
        failure_reason="DRINKING_AMBIGUOUS",
        video_verification_id=video.id,
    )

    return context, occurrence, video


def test_nakes_approve_review_increases_adherence(client, db, facility):
    context, occurrence, video = setup_review_case(db, facility.id)
    nakes = create_nakes(db, facility.id)

    before = get_progress(client, context)
    assert before["adherence_percentage"] == 100.0
    assert before["final_due_occurrences"] == 1

    response = client.put(
        f"/video-verifications/{video.id}",
        json={"status": "verified", "review_note": "Disetujui"},
        headers=nakes["headers"],
    )
    assert response.status_code == 200

    db.refresh(occurrence)
    assert occurrence.status == DailyMedicationStatus.VERIFIED

    after = get_progress(client, context)
    assert after["successful_occurrences"] == 2
    assert after["final_due_occurrences"] == 2
    assert after["pending_review_occurrences"] == 0
    assert after["adherence_percentage"] == 100.0


def test_nakes_reject_review_decreases_adherence(client, db, facility):
    context, occurrence, video = setup_review_case(db, facility.id)
    nakes = create_nakes(db, facility.id)

    response = client.put(
        f"/video-verifications/{video.id}",
        json={"status": "rejected", "review_note": "Tidak terlihat menelan"},
        headers=nakes["headers"],
    )
    assert response.status_code == 200

    db.refresh(occurrence)
    assert occurrence.status == DailyMedicationStatus.REJECTED

    after = get_progress(client, context)
    assert after["successful_occurrences"] == 1
    assert after["failed_occurrences"] == 1
    assert after["final_due_occurrences"] == 2
    assert after["pending_review_occurrences"] == 0
    assert after["adherence_percentage"] == 50.0


# =====================================================
# 14-19. STREAK HARIAN & MULTI SCHEDULE
# =====================================================


def test_day_with_all_schedules_verified_is_compliant(client, db, facility):
    context = create_patient(db, facility.id, schedule_times=[time(8, 0), time(18, 0)])
    yesterday = today_in_jakarta() - timedelta(days=1)

    for schedule in context["schedules"]:
        add_occurrence(db, schedule, yesterday, DailyMedicationStatus.VERIFIED)

    body = get_progress(client, context)

    assert body["successful_occurrences"] == 2
    assert body["final_due_occurrences"] == 2
    assert body["streak_days"] == 1


def test_day_with_one_verified_and_one_rejected_is_not_compliant(client, db, facility):
    context = create_patient(db, facility.id, schedule_times=[time(8, 0), time(18, 0)])
    yesterday = today_in_jakarta() - timedelta(days=1)

    add_occurrence(db, context["schedules"][0], yesterday, DailyMedicationStatus.VERIFIED)
    add_occurrence(db, context["schedules"][1], yesterday, DailyMedicationStatus.REJECTED)

    body = get_progress(client, context)

    assert body["streak_days"] == 0
    assert body["adherence_percentage"] == 50.0


def test_day_with_one_verified_and_one_missed_is_not_compliant(client, db, facility):
    context = create_patient(db, facility.id, schedule_times=[time(8, 0), time(18, 0)])
    yesterday = today_in_jakarta() - timedelta(days=1)

    add_occurrence(db, context["schedules"][0], yesterday, DailyMedicationStatus.VERIFIED)
    add_occurrence(db, context["schedules"][1], yesterday, DailyMedicationStatus.MISSED)

    body = get_progress(client, context)

    assert body["streak_days"] == 0
    assert body["adherence_percentage"] == 50.0


def test_streak_counts_consecutive_fully_verified_days(client, db, facility):
    context = create_patient(db, facility.id, schedule_times=[time(8, 0), time(18, 0)])
    today = today_in_jakarta()

    for offset in (1, 2, 3):
        for schedule in context["schedules"]:
            add_occurrence(
                db,
                schedule,
                today - timedelta(days=offset),
                DailyMedicationStatus.VERIFIED,
            )

    body = get_progress(client, context)

    assert body["streak_days"] == 3


def test_streak_resets_after_final_failed_day(client, db, facility):
    context = create_patient(db, facility.id)
    schedule = context["schedules"][0]
    today = today_in_jakarta()

    add_occurrence(db, schedule, today - timedelta(days=3), DailyMedicationStatus.VERIFIED)
    add_occurrence(db, schedule, today - timedelta(days=2), DailyMedicationStatus.VERIFIED)
    add_occurrence(db, schedule, today - timedelta(days=1), DailyMedicationStatus.MISSED)

    body = get_progress(client, context)

    assert body["streak_days"] == 0


def test_streak_does_not_judge_day_that_still_needs_review(client, db, facility):
    context = create_patient(db, facility.id, schedule_times=[time(8, 0), time(18, 0)])
    today = today_in_jakarta()

    for schedule in context["schedules"]:
        add_occurrence(
            db,
            schedule,
            today - timedelta(days=2),
            DailyMedicationStatus.VERIFIED,
        )

    add_occurrence(
        db,
        context["schedules"][0],
        today - timedelta(days=1),
        DailyMedicationStatus.VERIFIED,
    )
    add_occurrence(
        db,
        context["schedules"][1],
        today - timedelta(days=1),
        DailyMedicationStatus.NEEDS_REVIEW,
    )

    body = get_progress(client, context)

    assert body["pending_review_occurrences"] == 1
    assert body["streak_days"] == 1


# =====================================================
# 20-21. ISOLASI ANTAR PASIEN
# =====================================================


def test_patient_progress_only_counts_own_occurrences(client, db, facility):
    patient_a = create_patient(db, facility.id)
    patient_b = create_patient(db, facility.id)
    yesterday = today_in_jakarta() - timedelta(days=1)

    add_occurrence(db, patient_a["schedules"][0], yesterday, DailyMedicationStatus.VERIFIED)
    add_occurrence(db, patient_b["schedules"][0], yesterday, DailyMedicationStatus.MISSED)

    body_a = get_progress(client, patient_a)
    body_b = get_progress(client, patient_b)

    assert body_a["successful_occurrences"] == 1
    assert body_a["failed_occurrences"] == 0
    assert body_a["adherence_percentage"] == 100.0

    assert body_b["successful_occurrences"] == 0
    assert body_b["failed_occurrences"] == 1
    assert body_b["adherence_percentage"] == 0.0


def test_patient_without_occurrence_not_affected_by_other_patient(client, db, facility):
    patient_a = create_patient(db, facility.id)
    patient_b = create_patient(db, facility.id)
    yesterday = today_in_jakarta() - timedelta(days=1)

    add_occurrence(db, patient_b["schedules"][0], yesterday, DailyMedicationStatus.VERIFIED)

    body_a = get_progress(client, patient_a)

    assert body_a["final_due_occurrences"] == 0
    assert body_a["successful_occurrences"] == 0
    assert body_a["adherence_percentage"] is None


# =====================================================
# 22-23. CONTRACT ENDPOINT
# =====================================================


def test_progress_response_matches_schema(client, db, facility):
    context = create_patient(db, facility.id)
    yesterday = today_in_jakarta() - timedelta(days=1)
    add_occurrence(db, context["schedules"][0], yesterday, DailyMedicationStatus.VERIFIED)

    body = get_progress(client, context)

    assert set(body.keys()) == {
        "adherence_percentage",
        "successful_occurrences",
        "failed_occurrences",
        "pending_review_occurrences",
        "final_due_occurrences",
        "streak_days",
    }
    assert isinstance(body["adherence_percentage"], float)
    assert isinstance(body["successful_occurrences"], int)
    assert isinstance(body["failed_occurrences"], int)
    assert isinstance(body["pending_review_occurrences"], int)
    assert isinstance(body["final_due_occurrences"], int)
    assert isinstance(body["streak_days"], int)


def test_no_final_due_occurrence_returns_null_not_fake_100(client, db, facility):
    context = create_patient(db, facility.id)

    body = get_progress(client, context)

    assert body["adherence_percentage"] is None
    assert body["successful_occurrences"] == 0
    assert body["failed_occurrences"] == 0
    assert body["pending_review_occurrences"] == 0
    assert body["final_due_occurrences"] == 0
    assert body["streak_days"] == 0


def test_progress_requires_authentication(client):
    response = client.get("/medications/progress")
    assert response.status_code in (401, 403)


def test_progress_forbidden_for_nakes(client, db, facility):
    nakes = create_nakes(db, facility.id)

    response = client.get("/medications/progress", headers=nakes["headers"])

    assert response.status_code == 403
