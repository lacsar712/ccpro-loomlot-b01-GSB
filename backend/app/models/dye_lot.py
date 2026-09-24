from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
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
    # 染程关闭时刻：为空表示未关闭。未复测满规定次数的染程不得关闭。
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    vat: Mapped["Vat"] = relationship("Vat", back_populates="dye_lots")
    fastness_checks: Mapped[List["FastnessCheck"]] = relationship(
        "FastnessCheck", back_populates="dye_lot", cascade="all, delete-orphan"
    )

    @hybrid_property
    def is_closed(self) -> bool:
        return self.closed_at is not None

    @hybrid_property
    def retest_met(self) -> bool:
        """该染程下是否至少一条色牢度复测次数达标（规定次数见配置常量）。"""
        return any(c.retest_count >= settings.retest_target for c in self.fastness_checks)
