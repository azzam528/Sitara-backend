from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.patient import router as patient_router
from app.api.treatment import router as treatment_router
from app.api.medicine import router as medicine_router
from app.api.medicine_schedule import router as medicine_schedule_router
app = FastAPI()

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(patient_router)
app.include_router(treatment_router)
app.include_router(medicine_router)
app.include_router(medicine_schedule_router)