from datetime import datetime, timezone
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError


def _aware(dt: datetime) -> datetime:
    """裸时间按 UTC 处理，便于与带时区时间比较。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_retest_fields(
    retest_count: Optional[int],
    last_retest_at: Optional[datetime],
    checked_at: datetime,
) -> None:
    """复测字段业务校验，违例抛 ValueError（中文消息，路由层转 400）。"""
    if retest_count is not None and retest_count < 0:
        raise ValueError("复测次数必须为非负整数")
    if retest_count == 0 and last_retest_at is not None:
        raise ValueError("复测次数为 0 时末次复测时刻必须为空")
    if (retest_count or 0) > 0 and last_retest_at is None:
        raise ValueError("复测次数大于 0 时，末次复测时刻必填")
    if last_retest_at is not None and _aware(last_retest_at) < _aware(checked_at):
        raise ValueError("末次复测时刻不得早于抽检时刻")


def _parse_retest_count(v) -> int:
    """复测次数必须是非负整数（拒绝字符串、小数、布尔）。"""
    if isinstance(v, bool) or not isinstance(v, int):
        raise PydanticCustomError("retest_count_int", "复测次数必须为非负整数")
    if v < 0:
        raise PydanticCustomError("retest_count_negative", "复测次数必须为非负整数")
    return v


class FastnessCheckCreate(BaseModel):
    dye_lot_id: int = Field(..., alias="dyeLotId")
    checked_at: datetime = Field(..., alias="checkedAt")
    wash_fastness: int = Field(..., ge=1, le=5, alias="washFastness")
    rub_fastness: float = Field(..., gt=0, alias="rubFastness")
    temp_c: float = Field(..., alias="tempC")
    notes: Optional[str] = None
    retest_count: int = Field(default=0, alias="retestCount")
    last_retest_at: Optional[datetime] = Field(default=None, alias="lastRetestAt")

    @field_validator("retest_count", mode="before")
    @classmethod
    def _check_retest_count(cls, v):
        return _parse_retest_count(v)

    @model_validator(mode="after")
    def _validate_retest(self):
        try:
            validate_retest_fields(self.retest_count, self.last_retest_at, self.checked_at)
        except ValueError as exc:
            raise PydanticCustomError("retest_fields", str(exc))
        return self

    model_config = ConfigDict(populate_by_name=True)


class FastnessCheckUpdate(BaseModel):
    dye_lot_id: Optional[int] = Field(None, alias="dyeLotId")
    checked_at: Optional[datetime] = Field(None, alias="checkedAt")
    wash_fastness: Optional[int] = Field(None, ge=1, le=5, alias="washFastness")
    rub_fastness: Optional[float] = Field(None, gt=0, alias="rubFastness")
    temp_c: Optional[float] = Field(None, alias="tempC")
    notes: Optional[str] = None
    retest_count: Optional[int] = Field(None, alias="retestCount")
    last_retest_at: Optional[datetime] = Field(None, alias="lastRetestAt")

    @field_validator("retest_count", mode="before")
    @classmethod
    def _check_retest_count(cls, v):
        return None if v is None else _parse_retest_count(v)

    model_config = ConfigDict(populate_by_name=True)


class FastnessCheckRetest(BaseModel):
    """登记复测：不传时刻则取当前 UTC 时刻。"""

    last_retest_at: Optional[datetime] = Field(default=None, alias="lastRetestAt")

    model_config = ConfigDict(populate_by_name=True)


class FastnessCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    dye_lot_id: int = Field(serialization_alias="dyeLotId")
    checked_at: datetime = Field(serialization_alias="checkedAt")
    wash_fastness: int = Field(serialization_alias="washFastness")
    rub_fastness: float = Field(serialization_alias="rubFastness")
    temp_c: float = Field(serialization_alias="tempC")
    notes: Optional[str] = None
    retest_count: int = Field(serialization_alias="retestCount")
    last_retest_at: Optional[datetime] = Field(None, serialization_alias="lastRetestAt")
    retest_met: bool = Field(serialization_alias="retestMet")


__all__ = [
    "FastnessCheckCreate",
    "FastnessCheckUpdate",
    "FastnessCheckRetest",
    "FastnessCheckOut",
    "validate_retest_fields",
]
