from datetime import datetime
from typing import List, TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, and_, exists
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import REQUIRED_RETEST_COUNT
from app.database import Base

if TYPE_CHECKING:
    from app.models.vat import Vat
    from app.models.fastness_check import FastnessCheck


class DyeLot(Base):
    __tablename__ = "dye_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vat_id: Mapped[int] = mapped_column(ForeignKey("vats.id"), nullable=False, index=True)
    recipe_name: Mapped[str] = mapped_column(String(128), nullable=False)
    fabric_kg: Mapped[float] = mapped_column(Float, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    operator_name: Mapped[str] = mapped_column(String(64), nullable=False)
    # 关闭时刻：可空表示未关闭。关闭后禁止再追加色牢度记录。
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    vat: Mapped["Vat"] = relationship("Vat", back_populates="dye_lots")
    fastness_checks: Mapped[List["FastnessCheck"]] = relationship(
        "FastnessCheck", back_populates="dye_lot", cascade="all, delete-orphan"
    )

    @hybrid_property
    def is_open(self) -> bool:
        return self.closed_at is None

    @hybrid_property
    def retest_met(self) -> bool:
        """该染程下是否至少有一条色牢度复测达标（关闭的必要条件）。"""
        return any(c.retest_count >= REQUIRED_RETEST_COUNT for c in self.fastness_checks)

    @hybrid_property
    def retest_unmet(self) -> bool:
        """该染程下是否存在复测未达标的色牢度记录。"""
        return any(c.retest_count < REQUIRED_RETEST_COUNT for c in self.fastness_checks)

    @hybrid_property
    def retest_unmet_count(self) -> int:
        """该染程下复测未达标的色牢度条数（列表手数口径）。"""
        return sum(1 for c in self.fastness_checks if c.retest_count < REQUIRED_RETEST_COUNT)

    @classmethod
    def open_retest_unmet_criterion(cls):
        """未关闭且存在复测未达标色牢度 —— 看板计数与列表筛选共用此表达式。"""
        from app.models.fastness_check import FastnessCheck

        return and_(
            cls.closed_at.is_(None),
            exists().where(
                and_(
                    FastnessCheck.dye_lot_id == cls.id,
                    FastnessCheck.retest_count < REQUIRED_RETEST_COUNT,
                )
            ),
        )
