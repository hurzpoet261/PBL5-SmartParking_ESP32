from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import StaffUser
from app.schemas.business import DashboardSummaryResponse
from app.services.business import get_dashboard_summary

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(db: Session = Depends(get_db), _: StaffUser = Depends(get_current_user)):
    return get_dashboard_summary(db)
