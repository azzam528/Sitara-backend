"""
Seed database SITARA dengan data dummy untuk testing.

Jalankan:
    python seed.py

Pastikan:
    1. .env sudah mengarah ke database dbsitara
    2. alembic upgrade head sudah dijalankan
"""

from datetime import date, datetime, time, timedelta

from app.core.database import SessionLocal
from app.core.security import hash_password

from app.models.health_facility import HealthFacility
from app.models.user import User
from app.models.patient import Patient, GenderEnum
from app.models.medicine import Medicine
from app.models.treatment import (
    Treatment,
    TreatmentPhase,
    TreatmentStatus,
    RegimenEnum,
)
from app.models.medicine_schedule import MedicineSchedule
from app.models.daily_medication import (
    DailyMedication,
    DailyMedicationStatus,
    VotStep,
)
from app.models.complaint import Complaint, ComplaintStatus
from app.models.control_schedule import (
    ControlSchedule,
    ControlScheduleStatus,
)
from app.models.refill_request import (
    RefillRequest,
    RefillRequestStatus,
)
from app.models.notification import (
    Notification,
    NotificationType,
    NotificationReferenceType,
)


# ============================================================
# KONFIGURASI
# ============================================================

PASSWORD = "Test12345!"


# ============================================================
# SEED
# ============================================================

def seed():
    db = SessionLocal()

    try:

        # ====================================================
        # 1. HEALTH FACILITIES
        # ====================================================

        facilities = [
            HealthFacility(
                name="Puskesmas Cimenyan",
                address="Jl. Cimenyan Raya No. 10, Bandung",
                phone="0227212345",
                latitude=-6.8785,
                longitude=107.6810,
                is_active=True,
            ),
            HealthFacility(
                name="Puskesmas Cibiru",
                address="Jl. Manisi No. 25, Bandung",
                phone="0227801234",
                latitude=-6.9140,
                longitude=107.7160,
                is_active=True,
            ),
            HealthFacility(
                name="Puskesmas Antapani",
                address="Jl. Terusan Jakarta No. 100, Bandung",
                phone="0227205678",
                latitude=-6.9148,
                longitude=107.6587,
                is_active=True,
            ),
        ]

        db.add_all(facilities)
        db.flush()


        # ====================================================
        # 2. ADMIN
        # ====================================================

        admin = User(
            username="admin",
            email="admin@sitara.test",
            password_hash=hash_password(PASSWORD),
            role="admin",
            is_active=True,
            must_change_password=False,
        )

        db.add(admin)
        db.flush()


        # ====================================================
        # 3. NAKES
        # ====================================================

        nakes_data = [
            (
                "nakes.cimenyan",
                "nakes.cimenyan@sitara.test",
                facilities[0],
            ),
            (
                "nakes.cibiru",
                "nakes.cibiru@sitara.test",
                facilities[1],
            ),
            (
                "nakes.antapani",
                "nakes.antapani@sitara.test",
                facilities[2],
            ),
            (
                "nakes.support",
                "nakes.support@sitara.test",
                facilities[0],
            ),
        ]

        nakes_users = []

        for username, email, facility in nakes_data:

            user = User(
                username=username,
                email=email,
                password_hash=hash_password(PASSWORD),
                role="nakes",
                facility_id=facility.id,
                is_active=True,
                must_change_password=False,
            )

            db.add(user)
            nakes_users.append(user)

        db.flush()


        # ====================================================
        # 4. PATIENT + PATIENT ACCOUNT
        # ====================================================

        patient_data = [
            (
                "pasien.andi",
                "Andi Setiawan",
                "3273010101900001",
                GenderEnum.MALE,
                facilities[0],
                date(1990, 1, 1),
                "Karyawan swasta",
            ),
            (
                "pasien.siti",
                "Siti Aminah",
                "3273010202920002",
                GenderEnum.FEMALE,
                facilities[0],
                date(1992, 2, 2),
                "Ibu rumah tangga",
            ),
            (
                "pasien.budi",
                "Budi Hartono",
                "3273010303880003",
                GenderEnum.MALE,
                facilities[1],
                date(1988, 3, 3),
                "Pedagang",
            ),
            (
                "pasien.dewi",
                "Dewi Lestari",
                "3273010401950004",
                GenderEnum.FEMALE,
                facilities[1],
                date(1995, 4, 4),
                "Mahasiswa",
            ),
            (
                "pasien.rizky",
                "Rizky Maulana",
                "3273010501970005",
                GenderEnum.MALE,
                facilities[2],
                date(1997, 5, 5),
                "Teknisi",
            ),
            (
                "pasien.nurul",
                "Nurul Hidayah",
                "3273010602940006",
                GenderEnum.FEMALE,
                facilities[2],
                date(1994, 6, 6),
                "Guru",
            ),
            (
                "pasien.fajar",
                "Fajar Nugraha",
                "3273010701890007",
                GenderEnum.MALE,
                facilities[0],
                date(1989, 7, 7),
                "Wiraswasta",
            ),
            (
                "pasien.lina",
                "Lina Marlina",
                "3273010802960008",
                GenderEnum.FEMALE,
                facilities[1],
                date(1996, 8, 8),
                "Karyawan swasta",
            ),
        ]

        patients = []

        for index, (
            username,
            full_name,
            nik,
            gender,
            facility,
            birth_date,
            occupation,
        ) in enumerate(patient_data, start=1):

            user = User(
                username=username,
                email=f"{username}@sitara.test",
                password_hash=hash_password(PASSWORD),
                role="patient",
                facility_id=facility.id,
                is_active=True,
                must_change_password=False,
            )

            db.add(user)
            db.flush()

            patient = Patient(
                user_id=user.id,
                medical_record_number=f"MRN-2026-{index:04d}",
                full_name=full_name,
                nik=nik,
                birth_date=birth_date,
                gender=gender,
                phone=f"0812345678{index:02d}",
                address=f"Jl. Contoh No. {index}, Bandung",
                occupation=occupation,
                pmo_name=f"PMO {full_name.split()[0]}",
                pmo_phone=f"0821123456{index:02d}",
                clinical_note="Data dummy untuk pengujian SITARA.",
                is_active=True,
            )

            db.add(patient)
            patients.append(patient)

        db.flush()


       # ====================================================
        # 5. MEDICINES
        # ====================================================

        medicines = [
            # =========================
            # OBAT TBC / OAT
            # =========================

            Medicine(
                code="RIF-600",
                name="Rifampisin",
                category="OAT",
                strength="600 mg",
                unit="tablet",
                description="Obat anti tuberkulosis - data dummy.",
                is_active=True,
            ),

            Medicine(
                code="INH-300",
                name="Isoniazid",
                category="OAT",
                strength="300 mg",
                unit="tablet",
                description="Obat anti tuberkulosis - data dummy.",
                is_active=True,
            ),

            Medicine(
                code="PZA-500",
                name="Pirazinamid",
                category="OAT",
                strength="500 mg",
                unit="tablet",
                description="Obat anti tuberkulosis - data dummy.",
                is_active=True,
            ),

            Medicine(
                code="EMB-400",
                name="Etambutol",
                category="OAT",
                strength="400 mg",
                unit="tablet",
                description="Obat anti tuberkulosis - data dummy.",
                is_active=True,
            ),

            # =========================
            # OBAT PENDUKUNG
            # =========================

            Medicine(
                code="PCM-500",
                name="Paracetamol",
                category="Obat Pendukung",
                strength="500 mg",
                unit="tablet",
                description="Obat pendukung untuk membantu meredakan demam dan nyeri.",
                is_active=True,
            ),

            Medicine(
                code="PMG-200",
                name="Promag",
                category="Obat Pendukung",
                strength="200 mg",
                unit="tablet",
                description="Obat pendukung untuk keluhan maag dan asam lambung.",
                is_active=True,
            ),
        ]

        db.add_all(medicines)
        db.flush()

        # ====================================================
        # 6. TREATMENTS
        # ====================================================

        today = date.today()

        treatments = []

        for index, patient in enumerate(patients, start=1):

            start_date = today - timedelta(
                days=20 + (index * 5)
            )

            treatment = Treatment(
                patient_id=patient.id,

                diagnosis_date=start_date - timedelta(days=5),

                therapy_start_date=start_date,

                therapy_end_date=start_date + timedelta(days=180),

                phase=(
                    TreatmentPhase.INTENSIVE
                    if index <= 5
                    else TreatmentPhase.CONTINUATION
                ),

                regimen=(
                    RegimenEnum.CATEGORY_1
                    if index <= 6
                    else RegimenEnum.CATEGORY_2
                ),

                status=TreatmentStatus.ACTIVE,

                doctor_name=(
                    "Dr. Rina Maharani"
                    if index % 2 == 1
                    else "Ns. Andi Pratama"
                ),

                doctor_note="Terapi aktif. Data dummy untuk pengujian.",

                is_active=True,
            )

            db.add(treatment)
            treatments.append(treatment)

        db.flush()


        # ====================================================
        # 7. MEDICINE SCHEDULES
        # ====================================================

        schedules = []

        medicine_pairs = [
            (medicines[0], medicines[1]),
            (medicines[0], medicines[2]),
            (medicines[0], medicines[3]),
            (medicines[1], medicines[2]),
        ]

        for index, treatment in enumerate(treatments):

            first_medicine, second_medicine = medicine_pairs[
                index % len(medicine_pairs)
            ]

            medicine_schedule_data = [
                (first_medicine, time(7, 0)),
                (second_medicine, time(7, 5)),
            ]

            for medicine, drink_time in medicine_schedule_data:

                schedule = MedicineSchedule(
                    treatment_id=treatment.id,
                    medicine_id=medicine.id,

                    dosage="1 tablet",

                    quantity_initial=30,

                    quantity_remaining=24,

                    drink_time=drink_time,

                    is_active=True,
                )

                db.add(schedule)
                schedules.append(schedule)

        db.flush()


        # ====================================================
        # 8. DAILY MEDICATION
        # ====================================================

        for schedule in schedules:

            # Buat data:
            # - 3 hari sebelumnya
            # - hari ini
            # - 3 hari berikutnya

            for day_offset in range(-3, 4):

                scheduled_date = (
                    today + timedelta(days=day_offset)
                )

                if day_offset < 0:

                    status = DailyMedicationStatus.VERIFIED

                    vot_step = VotStep.VERIFIED

                    completed_at = datetime.combine(
                        scheduled_date,
                        schedule.drink_time,
                    ) + timedelta(minutes=3)

                    attempt_count = 1

                else:

                    status = DailyMedicationStatus.PENDING

                    vot_step = VotStep.WAITING

                    completed_at = None

                    attempt_count = 0

                daily_medication = DailyMedication(

                    medicine_schedule_id=schedule.id,

                    scheduled_date=scheduled_date,

                    scheduled_time=schedule.drink_time,

                    status=status,

                    vot_step=vot_step,

                    attempt_count=attempt_count,

                    failure_reason=None,

                    max_drinking_stage=None,

                    completed_at=completed_at,

                    is_active=True,
                )

                db.add(daily_medication)


        # ====================================================
        # 9. COMPLAINTS
        # ====================================================

        complaints = [

            Complaint(
                treatment_id=treatments[0].id,

                handled_by=nakes_users[0].id,

                category="Efek samping obat",

                description=(
                    "Pasien mengeluhkan mual ringan "
                    "setelah minum obat."
                ),

                status=ComplaintStatus.RESOLVED,

                response=(
                    "Anjurkan minum setelah makan "
                    "sesuai arahan tenaga kesehatan."
                ),

                is_active=True,
            ),

            Complaint(
                treatment_id=treatments[2].id,

                handled_by=None,

                category="Keluhan kesehatan",

                description=(
                    "Pasien merasa pusing "
                    "sejak dua hari terakhir."
                ),

                status=ComplaintStatus.PENDING,

                response=None,

                is_active=True,
            ),
        ]

        db.add_all(complaints)


        # ====================================================
        # 10. CONTROL SCHEDULE
        # ====================================================

        control_schedules = [

            ControlSchedule(
                treatment_id=treatments[0].id,

                control_date=today - timedelta(days=2),

                control_time=time(9, 0),

                status=ControlScheduleStatus.COMPLETED,

                doctor_note="Kontrol rutin, kondisi stabil.",

                is_active=True,
            ),

            ControlSchedule(
                treatment_id=treatments[0].id,

                control_date=today + timedelta(days=7),

                control_time=time(9, 0),

                status=ControlScheduleStatus.PENDING,

                doctor_note=None,

                is_active=True,
            ),

            ControlSchedule(
                treatment_id=treatments[3].id,

                control_date=today + timedelta(days=10),

                control_time=time(10, 0),

                status=ControlScheduleStatus.PENDING,

                doctor_note=None,

                is_active=True,
            ),
        ]

        db.add_all(control_schedules)


        # ====================================================
        # 11. REFILL REQUEST
        # ====================================================

        refill_requests = [

            RefillRequest(
                treatment_id=treatments[0].id,

                medicine_id=medicines[0].id,

                quantity=30,

                reason="Persediaan obat hampir habis",

                description=(
                    "Permintaan refill untuk "
                    "siklus terapi berikutnya."
                ),

                status=RefillRequestStatus.PENDING,

                nurse_note=None,

                approved_by=None,

                approved_at=None,

                is_active=True,
            ),

            RefillRequest(
                treatment_id=treatments[1].id,

                medicine_id=medicines[1].id,

                quantity=30,

                reason="Jadwal pengambilan obat berikutnya",

                description=None,

                status=RefillRequestStatus.APPROVED,

                nurse_note=(
                    "Disetujui untuk pengambilan "
                    "sesuai jadwal."
                ),

                approved_by=nakes_users[0].id,

                approved_at=(
                    datetime.utcnow()
                    - timedelta(days=1)
                ),

                is_active=True,
            ),
        ]

        db.add_all(refill_requests)


        # ====================================================
        # 12. NOTIFICATIONS
        # ====================================================

        notifications = [

            Notification(
                user_id=patients[0].user_id,

                title="Jadwal minum obat",

                message=(
                    "Jangan lupa melakukan "
                    "verifikasi minum obat hari ini."
                ),

                type=NotificationType.MEDICINE,

                reference_type=(
                    NotificationReferenceType.MEDICINE_SCHEDULE
                ),

                reference_id=schedules[0].id,

                is_read=False,

                is_active=True,
            ),

            Notification(
                user_id=patients[0].user_id,

                title="Jadwal kontrol",

                message=(
                    "Anda memiliki jadwal kontrol "
                    "7 hari lagi."
                ),

                type=NotificationType.CONTROL,

                reference_type=(
                    NotificationReferenceType.CONTROL_SCHEDULE
                ),

                reference_id=None,

                is_read=True,

                is_active=True,
            ),

            Notification(
                user_id=nakes_users[0].id,

                title="Permintaan refill baru",

                message=(
                    "Terdapat permintaan refill obat "
                    "yang menunggu diproses."
                ),

                type=NotificationType.REFILL,

                reference_type=(
                    NotificationReferenceType.REFILL
                ),

                reference_id=None,

                is_read=False,

                is_active=True,
            ),
        ]

        db.add_all(notifications)


        # ====================================================
        # COMMIT
        # ====================================================

        db.commit()


        # ====================================================
        # SUCCESS
        # ====================================================

        print()
        print("=" * 50)
        print("SITARA TEST DATABASE SEED SUCCESS")
        print("=" * 50)

        print(f"Facilities : {len(facilities)}")
        print("Admin      : 1")
        print(f"Nakes      : {len(nakes_users)}")
        print(f"Patients   : {len(patients)}")
        print(f"Treatments : {len(treatments)}")
        print(f"Schedules  : {len(schedules)}")
        print("Daily meds : 7 hari per schedule")

        print()
        print("LOGIN TEST")
        print("-" * 50)
        print("Admin      : admin")
        print("Nakes      : nakes.cimenyan")
        print("Patient    : pasien.andi")
        print()
        print("Password   : Test12345!")
        print("=" * 50)
        print()


    except Exception as e:

        db.rollback()

        print()
        print("SEED FAILED")
        print("Error:", e)
        print()

        raise

    finally:

        db.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    seed()