from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.dye_lot import DyeLot
from app.models.fastness_check import FastnessCheck
from app.models.user import User
from app.retest_rules import required_retest_count
from app.schemas.fastness_check import FastnessCheckCreate, FastnessCheckUpdate, FastnessCheckOut

router = APIRouter(prefix="/api/fastness-checks", tags=["fastness-checks"])


def _retest_field_error(retest_count: int, last_retest_at: Optional[datetime], checked_at: datetime) -> Optional[str]:
    """复测字段组合校验，返回中文错误信息；通过返回 None。"""
    if retest_count > 0 and last_retest_at is None:
        return "复测次数大于 0 时，末次复测时刻必填"
    if retest_count <= 0 and last_retest_at is not None:
        return "复测次数为 0 时不得填写末次复测时刻"
    if last_retest_at is not None:
        checked = checked_at.replace(tzinfo=None) if checked_at.tzinfo else checked_at
        last = last_retest_at.replace(tzinfo=None) if last_retest_at.tzinfo else last_retest_at
        if last < checked:
            return "末次复测时刻不得早于抽检时刻"
    return None


@router.get("", response_model=List[FastnessCheckOut])
def list_checks(
    dye_lot_id: Optional[int] = Query(None, alias="dyeLotId"),
    retest_unmet: bool = Query(False, alias="retestUnmet"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(FastnessCheck)
    if dye_lot_id is not None:
        q = q.filter(FastnessCheck.dye_lot_id == dye_lot_id)
    if retest_unmet:
        q = q.filter(FastnessCheck.retest_count < required_retest_count())
    return q.order_by(FastnessCheck.id.desc()).all()


@router.post("", response_model=FastnessCheckOut, status_code=status.HTTP_201_CREATED)
def create_check(
    payload: FastnessCheckCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    lot = db.query(DyeLot).filter(DyeLot.id == payload.dye_lot_id).first()
    if not lot:
        raise HTTPException(status_code=400, detail="染程不存在")
    if lot.closed_at is not None:
        raise HTTPException(status_code=409, detail="染程已关闭，禁止再追加色牢度抽检")
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
    target_lot_id = data.get("dye_lot_id", item.dye_lot_id)
    target_lot = db.query(DyeLot).filter(DyeLot.id == target_lot_id).first()
    if not target_lot:
        raise HTTPException(status_code=400, detail="染程不存在")
    if target_lot.closed_at is not None:
        raise HTTPException(status_code=409, detail="染程已关闭，禁止追加或修改色牢度抽检")
    for k, v in data.items():
        setattr(item, k, v)
    # partial 更新后按合并后的最终值复核复测字段组合
    err = _retest_field_error(item.retest_count, item.last_retest_at, item.checked_at)
    if err:
        raise HTTPException(status_code=400, detail=err)
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
    lot = db.query(DyeLot).filter(DyeLot.id == item.dye_lot_id).first()
    if lot is not None and lot.closed_at is not None:
        raise HTTPException(status_code=409, detail="染程已关闭，禁止删除色牢度抽检")
    db.delete(item)
    db.commit()
