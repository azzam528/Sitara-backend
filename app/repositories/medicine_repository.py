from sqlalchemy.orm import Session

from app.models.medicine import Medicine


class MedicineRepository:

    def create(
        self,
        db: Session,
        medicine: Medicine,
    ) -> Medicine:

        db.add(medicine)

        db.commit()

        db.refresh(medicine)

        return medicine

    def get_by_id(
        self,
        db: Session,
        medicine_id: int,
    ):

        return (
            db.query(Medicine)
            .filter(
                Medicine.id == medicine_id,
                Medicine.is_active == True,
            )
            .first()
        )

    def get_by_code(
        self,
        db: Session,
        code: str,
    ):

        return (
            db.query(Medicine)
            .filter(
                Medicine.code == code,
                Medicine.is_active == True,
            )
            .first()
        )

    def get_all(
        self,
        db: Session,
    ):

        return (
            db.query(Medicine)
            .filter(
                Medicine.is_active == True,
            )
            .all()
        )

    def update(
        self,
        db: Session,
        medicine: Medicine,
    ):

        db.commit()

        db.refresh(medicine)

        return medicine

    def delete(
        self,
        db: Session,
        medicine: Medicine,
    ):

        medicine.is_active = False

        db.commit()

        db.refresh(medicine)

        return medicine