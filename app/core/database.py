from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ======================================================
# ENGINE
# ======================================================
# Engine adalah penghubung utama antara aplikasi Python
# dan database PostgreSQL.
#
# DATABASE_URL diambil dari file .env melalui config.py.
#
# echo=True akan menampilkan semua SQL Query ke terminal.
# Saat production biasanya menggunakan echo=False.
# ======================================================

engine = create_engine(
    settings.DATABASE_URL,
    echo=True
)


# ======================================================
# SESSION
# ======================================================
# Session digunakan untuk melakukan operasi database
# seperti:
#
# - SELECT
# - INSERT
# - UPDATE
# - DELETE
#
# SessionLocal adalah "pabrik" untuk membuat Session baru.
# ======================================================

SessionLocal = sessionmaker(
    autocommit=False,   # perubahan harus disimpan dengan db.commit()
    autoflush=False,    # SQLAlchemy tidak flush otomatis
    bind=engine         # Session menggunakan Engine di atas
)


# ======================================================
# BASE MODEL
# ======================================================
# Semua model database harus mewarisi Base.
#
# Contoh:
#
# class User(Base):
#     __tablename__ = "users"
# ======================================================

class Base(DeclarativeBase):
    pass


# ======================================================
# DATABASE DEPENDENCY
# ======================================================
# Membuat Session baru untuk setiap request FastAPI.
#
# Setelah request selesai, Session akan otomatis ditutup
# agar koneksi database tidak bocor.
# ======================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()