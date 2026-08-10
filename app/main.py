from fastapi import FastAPI

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
from app.schemas import complaint
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(patient_router)
app.include_router(treatment_router)
app.include_router(medicine_router)
app.include_router(medicine_schedule_router)
app.include_router(video_verification_router)
app.include_router(complaint_router)
