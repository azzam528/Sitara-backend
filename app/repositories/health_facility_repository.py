from sqlalchemy.orm import Session

from app.models.health_facility import HealthFacility


class HealthFacilityRepository:

    def get_all(
        self,
        db: Session,
    ):
        return (
            db.query(HealthFacility)
            .order_by(HealthFacility.id.asc())
            .all()
        )
