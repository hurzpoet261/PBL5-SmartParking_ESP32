from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundException
from app.models import Alert, StaffUser
from app.models.enums import AlertStatus, AlertType
from app.schemas.business import AlertCreate, AlertResponse
from app.services.business import create_alert, update_model

router = APIRouter()


@router.get("/gas/unresolved", response_model=list[AlertResponse])
def unresolved_gas_alerts(db: Session = Depends(get_db), _: StaffUser = Depends(get_current_user)):
    stmt = select(Alert).where(Alert.alert_type == AlertType.GAS, Alert.status == AlertStatus.OPEN)
    return db.execute(stmt).scalars().all()


@router.get("/", response_model=list[AlertResponse])
def list_alerts(
    status: AlertStatus | None = None,
    alert_type: AlertType | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    stmt = select(Alert)
    if status:
        stmt = stmt.where(Alert.status == status)
    if alert_type:
        stmt = stmt.where(Alert.alert_type == alert_type)
    stmt = stmt.order_by(Alert.detected_at.desc()).offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


@router.post("/", response_model=AlertResponse)
def create_alert_api(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    return create_alert(db, payload.model_dump())


@router.put("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise NotFoundException("Alert not found")
    return update_model(
        db,
        alert,
        {"status": AlertStatus.ACKNOWLEDGED, "acknowledged_at": datetime.utcnow()},
    )


@router.put("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise NotFoundException("Alert not found")
    return update_model(
        db,
        alert,
        {"status": AlertStatus.RESOLVED, "resolved_at": datetime.utcnow(), "resolved_by": current_user.user_id},
    )
