from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.user import User
from app.models.health_facility import HealthFacility
from app.repositories.health_facility_repository import (
    HealthFacilityRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminFacilityResponse,
    AdminNakesResponse,
    FacilityCreate,
    FacilityUpdate,
    NakesUpdate,
)


class AdminService:

    def __init__(self):
        self.facility_repository = HealthFacilityRepository()
        self.user_repository = UserRepository()

    # =====================================================
    # GET ALL FACILITIES
    # =====================================================

    def get_all_facilities(
        self,
        db: Session,
    ) -> list[AdminFacilityResponse]:

        facilities = self.facility_repository.get_all(db)

        return [
            AdminFacilityResponse.model_validate(f)
            for f in facilities
        ]

    # =====================================================
    # CREATE FACILITY
    # =====================================================

    def create_facility(
        self,
        db: Session,
        facility_data: FacilityCreate,
    ) -> AdminFacilityResponse:

        facility = HealthFacility(
            name=facility_data.name,
            address=facility_data.address,
            phone=facility_data.phone,
            latitude=facility_data.latitude,
            longitude=facility_data.longitude,
            is_active=True,
        )

        facility = self.facility_repository.create(db, facility)

        return AdminFacilityResponse.model_validate(facility)

    # =====================================================
    # UPDATE FACILITY
    # =====================================================

    def update_facility(
        self,
        db: Session,
        facility_id: int,
        facility_data: FacilityUpdate,
    ) -> AdminFacilityResponse:

        facility = self.facility_repository.get_by_id(
            db, facility_id,
        )

        if facility is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fasilitas kesehatan tidak ditemukan.",
            )

        update_data = facility_data.model_dump(
            exclude_unset=True,
        )

        for key, value in update_data.items():
            if hasattr(facility, key):
                setattr(facility, key, value)

        facility = self.facility_repository.update(db, facility)

        return AdminFacilityResponse.model_validate(facility)

    # =====================================================
    # DEACTIVATE FACILITY (SOFT DELETE)
    # =====================================================

    def deactivate_facility(
        self,
        db: Session,
        facility_id: int,
    ) -> AdminFacilityResponse:

        facility = self.facility_repository.get_by_id(
            db, facility_id,
        )

        if facility is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fasilitas kesehatan tidak ditemukan.",
            )

        if not facility.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fasilitas sudah nonaktif.",
            )

        # =================================================
        # CHECK ACTIVE USERS ON THIS FACILITY
        # =================================================

        active_users_count = (
            db.query(User)
            .filter(
                User.facility_id == facility_id,
                User.is_active.is_(True),
            )
            .count()
        )

        if active_users_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Fasilitas tidak dapat dinonaktifkan karena "
                    "masih memiliki user aktif yang terhubung."
                ),
            )

        facility.is_active = False

        facility = self.facility_repository.update(db, facility)

        return AdminFacilityResponse.model_validate(facility)

    # =====================================================
    # GET ALL NAKES
    # =====================================================

    def get_all_nakes(
        self,
        db: Session,
    ) -> list[AdminNakesResponse]:

        # Eager-load facility to avoid N+1 queries
        nakes_list = (
            db.query(User)
            .options(joinedload(User.facility))
            .filter(
                User.role == "nakes",
            )
            .order_by(User.id.asc())
            .all()
        )

        return [
            AdminNakesResponse(
                id=n.id,
                username=n.username,
                email=n.email,
                role=n.role,
                is_active=n.is_active,
                facility_id=n.facility_id,
                facility_name=(
                    n.facility.name if n.facility else None
                ),
            )
            for n in nakes_list
        ]

    # =====================================================
    # UPDATE NAKES
    # =====================================================

    def update_nakes(
        self,
        db: Session,
        nakes_id: int,
        nakes_data: NakesUpdate,
    ) -> AdminNakesResponse:

        nakes = self.user_repository.get_nakes_by_id(
            db, nakes_id,
        )

        if nakes is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nakes tidak ditemukan.",
            )

        update_data = nakes_data.model_dump(
            exclude_unset=True,
        )

        # =================================================
        # VALIDATE USERNAME UNIQUENESS
        # =================================================

        if "username" in update_data and update_data["username"] is not None:
            new_username = update_data["username"].strip()

            if not new_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username tidak boleh kosong.",
                )

            if new_username != nakes.username:
                existing = self.user_repository.get_by_username(
                    db, new_username,
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Username sudah digunakan.",
                    )

            update_data["username"] = new_username

        # =================================================
        # VALIDATE EMAIL UNIQUENESS
        # =================================================

        if "email" in update_data and update_data["email"] is not None:
            new_email = update_data["email"].strip()

            if new_email and new_email != nakes.email:
                existing = self.user_repository.get_by_email(
                    db, new_email,
                )
                if existing and existing.id != nakes.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Email sudah digunakan.",
                    )

            update_data["email"] = new_email if new_email else None

        # =================================================
        # VALIDATE FACILITY
        # =================================================

        if "facility_id" in update_data and update_data["facility_id"] is not None:
            facility = self.facility_repository.get_by_id(
                db, update_data["facility_id"],
            )

            if facility is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Fasilitas kesehatan tidak ditemukan.",
                )

            if not facility.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tidak dapat memilih fasilitas yang sudah nonaktif.",
                )

        # =================================================
        # APPLY UPDATES
        # =================================================

        for key, value in update_data.items():
            if hasattr(nakes, key):
                setattr(nakes, key, value)

        nakes = self.user_repository.update(db, nakes)

        # Reload facility relationship
        db.refresh(nakes)

        facility_name = None
        if nakes.facility_id:
            facility = self.facility_repository.get_by_id(
                db, nakes.facility_id,
            )
            if facility:
                facility_name = facility.name

        return AdminNakesResponse(
            id=nakes.id,
            username=nakes.username,
            email=nakes.email,
            role=nakes.role,
            is_active=nakes.is_active,
            facility_id=nakes.facility_id,
            facility_name=facility_name,
        )

    # =====================================================
    # DEACTIVATE NAKES (SOFT DELETE)
    # =====================================================

    def deactivate_nakes(
        self,
        db: Session,
        nakes_id: int,
    ) -> AdminNakesResponse:

        nakes = self.user_repository.get_nakes_by_id(
            db, nakes_id,
        )

        if nakes is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nakes tidak ditemukan.",
            )

        if not nakes.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nakes sudah nonaktif.",
            )

        nakes.is_active = False

        nakes = self.user_repository.update(db, nakes)

        facility_name = None
        if nakes.facility_id:
            facility = self.facility_repository.get_by_id(
                db, nakes.facility_id,
            )
            if facility:
                facility_name = facility.name

        return AdminNakesResponse(
            id=nakes.id,
            username=nakes.username,
            email=nakes.email,
            role=nakes.role,
            is_active=nakes.is_active,
            facility_id=nakes.facility_id,
            facility_name=facility_name,
        )
