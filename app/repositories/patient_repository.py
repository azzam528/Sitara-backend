from sqlalchemy.orm import Session

from app.models.patient import Patient


class PatientRepository:

    def create(
        self,
        db: Session,
        patient: Patient
    ) -> Patient:

        db.add(patient)
        db.commit()
        db.refresh(patient)

        return patient


    def get_by_id(
        self,
        db: Session,
        patient_id: int
    ) -> Patient | None:

        return (
            db.query(Patient)
            .filter(Patient.id == patient_id)
            .first()
        )


    def get_by_user_id(
        self,
        db: Session,
        user_id: int
    ) -> Patient | None:

        return (
            db.query(Patient)
            .filter(Patient.user_id == user_id)
            .first()
        )


    def get_by_nik(
        self,
        db: Session,
        nik: str
    ) -> Patient | None:

        return (
            db.query(Patient)
            .filter(Patient.nik == nik)
            .first()
        )


    def get_by_medical_record_number(
        self,
        db: Session,
        mrn: str
    ) -> Patient | None:

        return (
            db.query(Patient)
            .filter(Patient.medical_record_number == mrn)
            .first()
        )


    def get_all(
        self,
        db: Session
    ) -> list[Patient]:

        return (
            db.query(Patient)
            .all()
        )


    def update(
        self,
        db: Session,
        patient: Patient
    ) -> Patient:

        db.commit()
        db.refresh(patient)

        return patient


    def delete(
        self,
        db: Session,
        patient: Patient
    ) -> None:

        db.delete(patient)
        db.commit()