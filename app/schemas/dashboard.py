from datetime import date

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    active_patients: int
    medication_adherence: float
    high_risk_patients: int
    today_complaints: int
    critical_stock_items: int


class RiskSummary(BaseModel):
    high: int
    medium: int
    low: int


class AdherenceTrendItem(BaseModel):
    date: date
    percentage: float


class RecentActivity(BaseModel):
    type: str
    title: str
    description: str
    created_at: str


class CriticalStockItem(BaseModel):
    medicine_id: int
    medicine_name: str
    quantity_remaining: int


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    risk: RiskSummary
    adherence_trend: list[AdherenceTrendItem]
    recent_activities: list[RecentActivity]
    critical_stock: list[CriticalStockItem]