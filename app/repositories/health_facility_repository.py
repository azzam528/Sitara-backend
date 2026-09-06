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

    def get_by_id(
        self,
        db: Session,
        facility_id: int,
    ):
        return (
            db.query(HealthFacility)
            .filter(HealthFacility.id == facility_id)
            .first()
        )

    def create(
        self,
        db: Session,
        facility: HealthFacility,
    ):
        db.add(facility)

        db.commit()

        db.refresh(facility)

        return facility

    def update(
        self,
        db: Session,
        facility: HealthFacility,
    ):
        db.commit()

        db.refresh(facility)

        return facility

