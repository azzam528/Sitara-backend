# SITARA Backend

Backend API untuk **SITARA (Sistem Cerdas untuk Pemantauan dan Pengendalian Tuberkulosis Terintegrasi)**.

SITARA merupakan sistem pemantauan pengobatan pasien Tuberkulosis (TBC) yang menghubungkan pasien dan tenaga kesehatan dalam proses pengelolaan terapi, jadwal obat, pemantauan kepatuhan minum obat, serta verifikasi aktivitas minum obat berbasis AI.

Backend ini dibangun menggunakan **FastAPI** dan **PostgreSQL** dengan **SQLAlchemy ORM** sebagai database layer.

---

## 🚀 Tech Stack

### Backend
- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- PostgreSQL
- Alembic

### Authentication & Security
- JWT Authentication
- Password Hashing
- Activation Token
- Role-Based Access Control
- Facility-Based Access Control

### AI / Computer Vision
- OpenCV
- YuNet Face Detection
- SFace Face Recognition
- NumPy
- Ultralytics / YOLO
- Video Frame Sampling

### Testing
- Pytest
- HTTPX

---

## 🏗️ System Architecture

```text
                    SITARA APPLICATION
                           │
                           │ HTTP / REST API
                           ▼
                 ┌───────────────────┐
                 │    FastAPI API    │
                 └─────────┬─────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
     Authentication    Business Logic    AI Services
          │                │                │
          │                │                ├── Face Recognition
          │                │                ├── Medicine Detection
          │                │                └── Video Verification
          │                │
          ▼                ▼
       Security        Repositories
                           │
                           ▼
                    ┌──────────────┐
                    │  PostgreSQL  │
                    └──────────────┘
