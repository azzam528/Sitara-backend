from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError as SQLAlchemyOperationalError, DBAPIError

from app.core.database import get_db

from app.api.activation import router as activation_router
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.patient import router as patient_router
from app.api.treatment import router as treatment_router
from app.api.medicine import router as medicine_router
from app.api.medicine_schedule import router as medicine_schedule_router
from app.api.video_verification import (
    router as video_verification_router,
)
from app.api.complaint import router as complaint_router
from app.api.refill_requests import (
    router as refill_router,
)
from app.api.control_schedule import (
    router as control_schedule_router,
)
from app.api.notifications import (
    router as notification_router,
)
from app.api.dashboard import (
    router as dashboard_router,
)
from app.api.face import (
    router as face_router,
)
from app.api.medicine_detection import (
    router as medicine_detection_router,
)
from app.api.medication import router as medication_router
from app.api.vot import router as vot_router

app = FastAPI(title="SITARA API")


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Routers
# =========================

app.include_router(activation_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(patient_router)
app.include_router(treatment_router)
app.include_router(medicine_router)
app.include_router(medicine_schedule_router)
app.include_router(video_verification_router)
app.include_router(face_router)
app.include_router(complaint_router)
app.include_router(refill_router)
app.include_router(control_schedule_router)
app.include_router(notification_router)
app.include_router(dashboard_router)
app.include_router(medicine_detection_router)
app.include_router(medication_router)
app.include_router(vot_router)

# =========================
# Health Check Endpoint
# =========================


@app.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "message": "SITARA Backend & Database terhubung sempurna",
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Gagal terhubung ke database SITARA. Silakan periksa status PostgreSQL.",
        )


# =========================
# Database & Global Error Exception Handlers
# =========================


@app.exception_handler(SQLAlchemyOperationalError)
@app.exception_handler(DBAPIError)
async def db_exception_handler(request, exc):
    import traceback

    traceback.print_exc()
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Gagal terhubung ke database SITARA. Pastikan koneksi atau layanan PostgreSQL aktif."
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback

    traceback.print_exc()
    return JSONResponse(
        status_code=500, content={"detail": f"TERJADI KESALAHAN SERVER: {str(exc)}"}
    )
