from typing import List, Optional
from datetime import date
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    active_patients: int = 0
    active_treatments: int = 0
    completed_treatments: int = 0
    medication_adherence: Optional[float] = None
    today_verifications: int = 0
    today_complaints: int = 0
    critical_stock_items: int = 0
    high_risk_patients: int = 0
    tb_ro_patients: int = 0


class RiskDistribution(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0


class AdherenceTrendItem(BaseModel):
    date: date
    percentage: Optional[float] = None
    taken: int = 0
    expected: int = 0


class RecentActivityItem(BaseModel):
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
    risk: RiskDistribution
    adherence_trend: List[AdherenceTrendItem]
    recent_activities: List[RecentActivityItem]
    critical_stock: List[CriticalStockItem]
