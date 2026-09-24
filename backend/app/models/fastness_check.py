from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import REQUIRED_RETEST_COUNT
from app.database import Base

if TYPE_CHECKING:
    from app.models.dye_lot import DyeLot


class FastnessCheck(Base):
    __tablename__ = "fastness_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dye_lot_id: Mapped[int] = mapped_column(ForeignKey("dye_lots.id"), nullable=False, index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    wash_fastness: Mapped[int] = mapped_column(Integer, nullable=False)
    rub_fastness: Mapped[float] = mapped_column(Float, nullable=False)
    temp_c: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 复测次数：非负整数，默认 0（仅抽检、尚未复测）
    retest_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # 末次复测时刻：可空；retest_count > 0 时必填，且不得早于 checked_at
    last_retest_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    dye_lot: Mapped["DyeLot"] = relationship("DyeLot", back_populates="fastness_checks")

    @hybrid_property
    def retest_met(self) -> bool:
        """复测是否达标：复测次数达到规定次数。"""
        return self.retest_count >= REQUIRED_RETEST_COUNT
