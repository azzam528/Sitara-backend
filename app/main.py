from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError as SQLAlchemyOperationalError, DBAPIError

from app.core.database import get_db

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

app = FastAPI(title="SITARA API")


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Routers
# =========================

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
