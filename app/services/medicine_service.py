from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.medicine import Medicine

from app.repositories.medicine_repository import MedicineRepository

from app.schemas.medicine import (
    MedicineCreate,
    MedicineUpdate,
)


class MedicineService:

    def __init__(self):

        self.medicine_repository = MedicineRepository()

    def get_all(
        self,
        db: Session,
    ):

        return self.medicine_repository.get_all(db)

    def create_medicine(
        self,
        db: Session,
        medicine_data: MedicineCreate,
    ):

        existing = self.medicine_repository.get_by_code(
            db,
            medicine_data.code,
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Medicine code already exists",
            )

        medicine = Medicine(
            code=medicine_data.code,
            name=medicine_data.name,
            category=medicine_data.category,
            strength=medicine_data.strength,
            unit=medicine_data.unit,
            description=medicine_data.description,
        )

        return self.medicine_repository.create(
            db,
            medicine,
        )

    def get_by_id(
        self,
        db: Session,
        medicine_id: int,
    ):

        medicine = self.medicine_repository.get_by_id(
            db,
            medicine_id,
        )

        if medicine is None:
            raise HTTPException(
                status_code=404,
                detail="Medicine not found",
            )

        return medicine

    def update_medicine(
        self,
        db: Session,
        medicine_id: int,
        medicine_data: MedicineUpdate,
    ):

        medicine = self.medicine_repository.get_by_id(
            db,
            medicine_id,
        )

        if medicine is None:
            raise HTTPException(
                status_code=404,
                detail="Medicine not found",
            )

        update_data = medicine_data.model_dump(
            exclude_unset=True,
        )

        for key, value in update_data.items():

            setattr(
                medicine,
                key,
                value,
            )

        return self.medicine_repository.update(
            db,
            medicine,
        )

    def delete_medicine(
        self,
        db: Session,
        medicine_id: int,
    ):

        medicine = self.medicine_repository.get_by_id(
            db,
            medicine_id,
        )

        if medicine is None:
            raise HTTPException(
                status_code=404,
                detail="Medicine not found",
            )

        return self.medicine_repository.delete(
            db,
            medicine,
        )