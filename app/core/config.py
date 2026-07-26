from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Class untuk menyimpan seluruh konfigurasi aplikasi.

    Semua nilai akan diambil dari file .env
    sehingga kita tidak perlu menuliskan password
    atau konfigurasi langsung di source code.
    """

    # URL koneksi PostgreSQL
    DATABASE_URL: str

    # Secret key untuk JWT
    SECRET_KEY: str

    # Algoritma JWT
    ALGORITHM: str

    # Masa berlaku access token (menit)
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    class Config:
        """
        Memberitahu Pydantic untuk membaca file .env
        """
        env_file = ".env"


# Membuat object settings agar bisa digunakan
# di seluruh project.
settings = Settings()