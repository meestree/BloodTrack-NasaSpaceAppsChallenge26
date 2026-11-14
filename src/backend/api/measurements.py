"""Authenticated collection and history; user identity comes from the token."""
from datetime import date as Date, datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.api.auth import current_user
from backend.auth.schemas import UserResponse
from backend.measurements.schemas import MeasurementBatch
from backend.storage.measurements import MeasurementStore, UnknownBodyPart

router = APIRouter(tags=["measurements"])
User = Annotated[UserResponse, Depends(current_user)]
Days = Annotated[int, Query(ge=1, le=3650)]
Part = Annotated[int | None, Query(gt=0)]


def get_store(request: Request) -> MeasurementStore:
    return request.app.state.measurement_store


Store = Annotated[MeasurementStore, Depends(get_store)]


def window(days: int) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    start = end.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
    return start, end


@router.get("/body-parts")
def body_parts(user: User, store: Store) -> list[dict]:
    return store.body_parts()


@router.post("/measurements", status_code=201)
def collect(body: MeasurementBatch, user: User, store: Store) -> dict:
    try:
        ids = store.collect(user.id_usuario, body)
    except UnknownBodyPart:
        raise HTTPException(status_code=422, detail="Unknown id_parte; use /api/v1/body-parts") from None
    return {"created": len(ids), "ids": ids}


@router.get("/measurements")
def history(user: User, store: Store, days: Days = 7, id_parte: Part = None,
            limit: Annotated[int, Query(ge=1, le=1000)] = 100,
            offset: Annotated[int, Query(ge=0)] = 0) -> dict:
    start, end = window(days)
    return {"from": start, "to": end, **store.history(user.id_usuario, start, end, id_parte, limit, offset)}


@router.get("/measurements/daily")
def daily(user: User, store: Store, days: Days = 7, id_parte: Part = None) -> dict:
    start, end = window(days)
    return {"from": start, "to": end, "items": store.daily(user.id_usuario, start, end, id_parte)}


@router.get("/measurements/analytics")
def analytics(user: User, store: Store, days: Days = 7, id_parte: Part = None) -> dict:
    start, end = window(days)
    return {"from": start, "to": end, "days": days,
            "items": store.analytics(user.id_usuario, start, end, days, id_parte)}


@router.get("/measurements/latest")
def latest(user: User, store: Store, date: Date | None = None) -> dict:
    """Latest reading per region on a UTC date; defaults to the latest recorded day."""
    return store.latest(user.id_usuario, date)


@router.get('/measurements/movement')
def movement(user: User, store: Store, start_date: Date, end_date: Date,
             id_parte: Part = None) -> dict:
    """Counts of sensor samples marked as moving, grouped by UTC hour or day."""
    if end_date < start_date:
        raise HTTPException(status_code=422, detail='End date must be on or after start date')
    if end_date > datetime.now(timezone.utc).date():
        raise HTTPException(status_code=422, detail='Dates cannot be in the future')
    if (end_date - start_date).days >= 3650:
        raise HTTPException(status_code=422, detail='Select at most 3650 days')
    return store.movement(user.id_usuario, start_date, end_date, id_parte)


@router.get('/measurements/statistics')
def statistics(user: User, store: Store, start_date: Date, end_date: Date,
               metric: Literal['temperatura', 'caudal'] = 'temperatura') -> dict:
    if end_date < start_date or end_date > datetime.now(timezone.utc).date():
        raise HTTPException(status_code=422, detail='Select an ordered date range without future dates')
    if (end_date - start_date).days >= 3650:
        raise HTTPException(status_code=422, detail='Select at most 3650 days')
    return store.statistics(user.id_usuario, start_date, end_date, metric)
