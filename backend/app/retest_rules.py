"""色牢度复测与染程关闭的统一业务口径。

看板统计与染程列表筛选必须共用本模块的查询，禁止各算各的。
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.dye_lot import DyeLot
from app.models.fastness_check import FastnessCheck


def required_retest_count() -> int:
    """色牢度复测规定次数（常量，至少 2）。"""
    return settings.retest_target


def retest_pending_lot_ids(db: Session) -> set[int]:
    """未关闭且复测未达标的染程 id 集合。

    判定规则：染程 closed_at 为空（未关闭），且其名下没有任何一条色牢度
    抽检的 retest_count 达到规定次数（含一条抽检都没有的染程）。
    看板计数与列表「复测未达标」筛选都以本函数结果为准。
    """
    rows = (
        db.query(DyeLot.id)
        .outerjoin(FastnessCheck, FastnessCheck.dye_lot_id == DyeLot.id)
        .filter(DyeLot.closed_at.is_(None))
        .group_by(DyeLot.id)
        .having(func.coalesce(func.max(FastnessCheck.retest_count), 0) < required_retest_count())
        .all()
    )
    return {row[0] for row in rows}


def lot_retest_met(db: Session, lot_id: int) -> bool:
    """该染程下是否至少有一条色牢度复测次数达标。"""
    return (
        db.query(func.count(FastnessCheck.id))
        .filter(
            FastnessCheck.dye_lot_id == lot_id,
            FastnessCheck.retest_count >= required_retest_count(),
        )
        .scalar()
        or 0
    ) > 0
