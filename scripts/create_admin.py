import sys
from pathlib import Path

# Tambahkan project root ke Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def create_admin():
    db = SessionLocal()

    try:
        username = "admin"

        existing = db.query(User).filter(User.username == username).first()

        if existing:
            print("Admin sudah ada.")
            return

        admin = User(
            username=username,
            email="admin@sitara.id",
            password_hash=hash_password("Admin12345"),
            role="admin",
            facility_id=None,
            must_change_password=False,
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("Admin berhasil dibuat.")
        print(f"Username : {admin.username}")
        print("Password : Admin12345")

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
