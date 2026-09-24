from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.constants import REQUIRED_RETEST_COUNT
from app.database import get_db
from app.models.dye_lot import DyeLot
from app.models.fastness_check import FastnessCheck
from app.models.user import User
from app.schemas.fastness_check import (
    FastnessCheckCreate,
    FastnessCheckOut,
    FastnessCheckRetest,
    FastnessCheckUpdate,
    validate_retest_fields,
)

router = APIRouter(prefix="/api/fastness-checks", tags=["fastness-checks"])


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("", response_model=List[FastnessCheckOut])
def list_checks(
    dye_lot_id: Optional[int] = Query(None, alias="dyeLotId"),
    retest_unmet: Optional[bool] = Query(None, alias="retestUnmet"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(FastnessCheck)
    if dye_lot_id is not None:
        q = q.filter(FastnessCheck.dye_lot_id == dye_lot_id)
    if retest_unmet is True:
        # 与看板/染程列表同一达标线：retest_count < REQUIRED_RETEST_COUNT
        q = q.filter(FastnessCheck.retest_count < REQUIRED_RETEST_COUNT)
    elif retest_unmet is False:
        q = q.filter(FastnessCheck.retest_count >= REQUIRED_RETEST_COUNT)
    return q.order_by(FastnessCheck.id.desc()).all()


def _get_open_lot(db: Session, lot_id: int) -> DyeLot:
    lot = db.query(DyeLot).filter(DyeLot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=400, detail="染程不存在")
    if lot.closed_at is not None:
        raise HTTPException(status_code=409, detail="染程已关闭，禁止再追加色牢度记录")
    return lot


@router.post("", response_model=FastnessCheckOut, status_code=status.HTTP_201_CREATED)
def create_check(
    payload: FastnessCheckCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _get_open_lot(db, payload.dye_lot_id)
    item = FastnessCheck(
        dye_lot_id=payload.dye_lot_id,
        checked_at=payload.checked_at,
        wash_fastness=payload.wash_fastness,
        rub_fastness=payload.rub_fastness,
        temp_c=payload.temp_c,
        notes=payload.notes,
        retest_count=payload.retest_count,
        last_retest_at=payload.last_retest_at,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{check_id}/retest", response_model=FastnessCheckOut)
def register_retest(
    check_id: int,
    payload: FastnessCheckRetest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """对一条色牢度登记一次复测：次数 +1，刷新末次复测时刻。"""
    item = db.query(FastnessCheck).filter(FastnessCheck.id == check_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="色牢度抽检不存在")
    lot = db.query(DyeLot).filter(DyeLot.id == item.dye_lot_id).first()
    if lot.closed_at is not None:
        raise HTTPException(status_code=409, detail="染程已关闭，禁止再追加复测")
    at = _aware(payload.last_retest_at or datetime.now(timezone.utc))
    if at < _aware(item.last_retest_at or item.checked_at):
        raise HTTPException(
            status_code=400,
            detail="末次复测时刻不得早于抽检时刻或上一次复测时刻",
        )
    item.retest_count += 1
    item.last_retest_at = at
    db.commit()
    db.refresh(item)
    return item


@router.get("/{check_id}", response_model=FastnessCheckOut)
def get_check(
    check_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(FastnessCheck).filter(FastnessCheck.id == check_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="色牢度抽检不存在")
    return item


@router.put("/{check_id}", response_model=FastnessCheckOut)
def update_check(
    check_id: int,
    payload: FastnessCheckUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(FastnessCheck).filter(FastnessCheck.id == check_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="色牢度抽检不存在")
    data = payload.model_dump(exclude_unset=True)
    if "dye_lot_id" in data and data["dye_lot_id"] != item.dye_lot_id:
        _get_open_lot(db, data["dye_lot_id"])
    # 合并后整体校验复测字段，违例返回 400 中文
    merged = {
        "retest_count": data.get("retest_count", item.retest_count),
        "last_retest_at": data.get("last_retest_at", item.last_retest_at),
        "checked_at": data.get("checked_at", item.checked_at),
    }
    try:
        validate_retest_fields(**merged)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_check(
    check_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(FastnessCheck).filter(FastnessCheck.id == check_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="色牢度抽检不存在")
    db.delete(item)
    db.commit()
