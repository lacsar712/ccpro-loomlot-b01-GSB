from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.dye_lot import DyeLot
from app.models.user import User
from app.models.vat import Vat
from app.schemas.dye_lot import DyeLotCreate, DyeLotUpdate, DyeLotOut

router = APIRouter(prefix="/api/dye-lots", tags=["dye-lots"])

ALLOWED_VAT_STATUSES = {"ready", "dyeing"}


def _base_query(db: Session) -> "Query":
    # selectinload 保证 DyeLotOut 内嵌色牢度与 retest_* 派生字段不产生 N+1 查询
    return db.query(DyeLot).options(selectinload(DyeLot.fastness_checks))


@router.get("", response_model=List[DyeLotOut])
def list_dye_lots(
    vat_id: Optional[int] = Query(None, alias="vatId"),
    closed: Optional[bool] = Query(None),
    retest_unmet: Optional[bool] = Query(None, alias="retestUnmet"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """染程列表。

    closed=false&retestUnmet=true 即看板「未关闭且复测未达标」的同一口径，
    手数该结果的行数必须等于看板 openRetestUnmetCount。
    """
    q = _base_query(db)
    if vat_id is not None:
        q = q.filter(DyeLot.vat_id == vat_id)
    if closed is not None:
        q = q.filter(DyeLot.closed_at.is_(None) if not closed else DyeLot.closed_at.is_not(None))
    if retest_unmet is True:
        # 与看板计数共用 DyeLot.open_retest_unmet_criterion()
        q = q.filter(DyeLot.open_retest_unmet_criterion())
    elif retest_unmet is False:
        q = q.filter(~DyeLot.open_retest_unmet_criterion())
    return q.order_by(DyeLot.id.desc()).all()


@router.post("", response_model=DyeLotOut, status_code=status.HTTP_201_CREATED)
def create_dye_lot(
    payload: DyeLotCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    vat = db.query(Vat).filter(Vat.id == payload.vat_id).first()
    if not vat:
        raise HTTPException(status_code=400, detail="染缸不存在")
    if vat.status not in ALLOWED_VAT_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"染缸状态为「{vat.status}」，仅 ready 或 dyeing 时可新建染程",
        )
    item = DyeLot(
        vat_id=payload.vat_id,
        recipe_name=payload.recipe_name,
        fabric_kg=payload.fabric_kg,
        started_at=payload.started_at,
        operator_name=payload.operator_name,
    )
    vat.status = "dyeing"
    db.add(item)
    db.commit()
    db.refresh(item)
    return _base_query(db).filter(DyeLot.id == item.id).first()


@router.post("/{lot_id}/close", response_model=DyeLotOut)
def close_dye_lot(
    lot_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """关闭染程：仅当其下至少一条色牢度复测次数达标（REQUIRED_RETEST_COUNT）。"""
    item = _base_query(db).filter(DyeLot.id == lot_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="染程不存在")
    if item.closed_at is not None:
        raise HTTPException(status_code=409, detail="该染程已关闭，无需重复关闭")
    if not item.retest_met:
        raise HTTPException(
            status_code=409,
            detail="该染程下没有复测次数达标的色牢度记录，不得关闭",
        )
    item.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{lot_id}", response_model=DyeLotOut)
def get_dye_lot(
    lot_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = _base_query(db).filter(DyeLot.id == lot_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="染程不存在")
    return item


@router.put("/{lot_id}", response_model=DyeLotOut)
def update_dye_lot(
    lot_id: int,
    payload: DyeLotUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(DyeLot).filter(DyeLot.id == lot_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="染程不存在")
    data = payload.model_dump(exclude_unset=True)
    if "vat_id" in data and data["vat_id"] != item.vat_id:
        vat = db.query(Vat).filter(Vat.id == data["vat_id"]).first()
        if not vat:
            raise HTTPException(status_code=400, detail="染缸不存在")
        if vat.status not in ALLOWED_VAT_STATUSES:
            raise HTTPException(
                status_code=409,
                detail=f"目标染缸状态为「{vat.status}」，无法改挂染程",
            )
        vat.status = "dyeing"
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    return _base_query(db).filter(DyeLot.id == item.id).first()


@router.delete("/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dye_lot(
    lot_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(DyeLot).filter(DyeLot.id == lot_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="染程不存在")
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="该染程仍有关联记录，无法删除")
