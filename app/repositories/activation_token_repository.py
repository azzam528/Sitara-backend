from datetime import datetime

from sqlalchemy.orm import Session

from app.models.activation_token import ActivationToken


class ActivationTokenRepository:

    def create(
        self,
        db: Session,
        activation_token: ActivationToken,
        commit: bool = True,
    ):
        db.add(activation_token)

        if commit:
            db.commit()
            db.refresh(activation_token)
        else:
            db.flush()

        return activation_token

    def get_by_token_hash(
        self,
        db: Session,
        token_hash: str,
    ):
        return (
            db.query(ActivationToken)
            .filter(
                ActivationToken.token_hash == token_hash
            )
            .first()
        )

    def invalidate_user_tokens(
        self,
        db: Session,
        user_id: int,
    ):
        tokens = (
            db.query(ActivationToken)
            .filter(
                ActivationToken.user_id == user_id,
                ActivationToken.used_at.is_(None),
            )
            .all()
        )

        for token in tokens:
            token.used_at = datetime.utcnow()

        db.commit()