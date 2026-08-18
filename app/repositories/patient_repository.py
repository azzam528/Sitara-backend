from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.user import User


class PatientRepository:

    def create(self, db: Session, patient: Patient) -> Patient:

        db.add(patient)
        db.commit()
        db.refresh(patient)

        return patient

    def get_by_id(self, db: Session, patient_id: int):
        return (
            db.query(Patient)
            .filter(Patient.id == patient_id, Patient.is_active == True)
            .first()
        )

    def get_by_user_id(self, db: Session, user_id: int) -> Patient | None:

        return (
            db.query(Patient)
            .filter(
                Patient.user_id == user_id,
                Patient.is_active == True,
            )
            .first()
        )

    def get_by_nik(self, db: Session, nik: str) -> Patient | None:

        return db.query(Patient).filter(Patient.nik == nik).first()

    def get_by_medical_record_number(self, db: Session, mrn: str) -> Patient | None:

        return db.query(Patient).filter(Patient.medical_record_number == mrn).first()

    def get_all(self, db: Session):
        return db.query(Patient).filter(Patient.is_active == True).all()

    def update(self, db: Session, patient: Patient) -> Patient:

        db.commit()
        db.refresh(patient)

        return patient

    def delete(self, db: Session, patient: Patient):

        patient.is_active = False

        db.commit()

        db.refresh(patient)

        return patient

    def get_all_by_facility(
        self,
        db: Session,
        facility_id: int,
    ):
        return (
            db.query(Patient)
            .join(
                User,
                Patient.user_id == User.id,
            )
            .filter(
                User.facility_id == facility_id,
                Patient.is_active.is_(True),
            )
            .all()
        )

    def get_by_id_and_facility(
        self,
        db: Session,
        patient_id: int,
        facility_id: int,
    ):
        return (
            db.query(Patient)
            .join(
                User,
                Patient.user_id == User.id,
            )
            .filter(
                Patient.id == patient_id,
                User.facility_id == facility_id,
                Patient.is_active.is_(True),
            )
            .first()
        )
