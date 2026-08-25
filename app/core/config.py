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
    
    FRONTEND_BASE_URL: str

    # Public origin for patient HTTPS activation links.
    # Trailing slash is stripped when the URL is built.
    ACTIVATION_BASE_URL: str

    # Optional app download/install URL shown on the activation landing page.
    SITARA_APP_DOWNLOAD_URL: str | None = None

    # Face Recognition Configurations
    FACE_MODEL_VERSION: str = "opencv_yunet_sface_v1"
    FACE_SIMILARITY_THRESHOLD: float = 0.70
    FACE_DETECTION_THRESHOLD: float = 0.60
    FACE_MIN_SIZE: int = 40

    class Config:
        """
        Memberitahu Pydantic untuk membaca file .env
        """
        env_file = ".env"


# Membuat object settings agar bisa digunakan
# di seluruh project.
settings = Settings()