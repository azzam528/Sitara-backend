from sqlalchemy.orm import Session, joinedload

from app.models.user import User
from app.repositories.health_facility_repository import (
    HealthFacilityRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminFacilityResponse,
    AdminNakesResponse,
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
                User.is_active.is_(True),
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
