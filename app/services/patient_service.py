from sqlalchemy.orm import Session

from app.models.user import User
from app.models.patient import Patient

from app.repositories.user_repository import UserRepository
from app.repositories.patient_repository import PatientRepository

from app.schemas.patient import PatientCreate, PatientUpdate

from app.core.security import hash_password
from fastapi import HTTPException

class PatientService:

    def __init__(self):

        self.user_repository = UserRepository()

        self.patient_repository = PatientRepository()
    
    def get_all(
        self,
        db: Session
    ):
        return self.patient_repository.get_all(db)
        
    def create_patient(
        self,
        db: Session,
        patient_data: PatientCreate
    ):
    
    
        existing_username = self.user_repository.get_by_username(
            db,
            patient_data.username
        )

        if existing_username:
            raise Exception("Username already exists")
        
        existing_email = self.user_repository.get_by_email(
            db,
            patient_data.email
        )

        if existing_email:
            raise Exception("Email already exists")
        
        existing_nik = self.patient_repository.get_by_nik(
            db,
            patient_data.nik
        )

        if existing_nik:
            raise Exception("NIK already exists")
        
        existing_mrn = self.patient_repository.get_by_medical_record_number(
            db,
            patient_data.medical_record_number
        )

        if existing_mrn:
            raise Exception("Medical record number already exists")
        
        user = User(

            username=patient_data.username,

            email=patient_data.email,

            password_hash=hash_password(
                patient_data.password
            ),

            role="patient"
        )
        
        user = self.user_repository.create(
            db,
            user
        )
        
        patient = Patient(

            user_id=user.id,

            medical_record_number=patient_data.medical_record_number,

            full_name=patient_data.full_name,

            nik=patient_data.nik,

            birth_date=patient_data.birth_date,

            gender=patient_data.gender,

            phone=patient_data.phone,

            address=patient_data.address,

            occupation=patient_data.occupation,

            pmo_name=patient_data.pmo_name,

            pmo_phone=patient_data.pmo_phone,

            clinical_note=patient_data.clinical_note
        )
        
        patient = self.patient_repository.create(
            db,
            patient
        )
        
        return patient
    
    def get_by_id(
        self,
        db: Session,
        patient_id: int
    ):

        patient = self.patient_repository.get_by_id(
            db,
            patient_id
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        return patient    
    
    def update_patient(
        self,
        db: Session,
        patient_id: int,
        patient_data: PatientUpdate
    ):

        patient = self.patient_repository.get_by_id(
            db,
            patient_id
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        update_data = patient_data.model_dump(
            exclude_unset=True
        )

        for key, value in update_data.items():
            setattr(
                patient,
                key,
                value
            )

        return self.patient_repository.update(
            db,
            patient
        )

    def delete_patient(
        self,
        db: Session,
        patient_id: int
    ):

        patient = self.patient_repository.get_by_id(
            db,
            patient_id
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        return self.patient_repository.delete(
            db,
            patient
        )
        
    def get_profile(
        self,
        db: Session,
        current_user: User,
    ):

        patient = self.patient_repository.get_by_user_id(
            db,
            current_user.id,
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient profile not found",
            )

        return patient