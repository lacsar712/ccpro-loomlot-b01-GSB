from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _validate_nonneg_int(value):
    if value is None:
        return value
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("复测次数必须为非负整数")
    return value


class FastnessCheckCreate(BaseModel):
    dye_lot_id: int = Field(..., alias="dyeLotId")
    checked_at: datetime = Field(..., alias="checkedAt")
    wash_fastness: int = Field(..., ge=1, le=5, alias="washFastness")
    rub_fastness: float = Field(..., gt=0, alias="rubFastness")
    temp_c: float = Field(..., alias="tempC")
    notes: Optional[str] = None
    retest_count: int = Field(0, ge=0, alias="retestCount")
    last_retest_at: Optional[datetime] = Field(None, alias="lastRetestAt")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("retest_count", mode="before")
    @classmethod
    def _retest_count_validator(cls, value):
        if value is None:
            return 0
        return _validate_nonneg_int(value)

    @model_validator(mode="after")
    def _validate_retest(self):
        if self.retest_count > 0 and self.last_retest_at is None:
            raise ValueError("复测次数大于 0 时，末次复测时刻必填")
        if self.last_retest_at is not None:
            if self.retest_count <= 0:
                raise ValueError("复测次数为 0 时不得填写末次复测时刻")
            checked_at = self.checked_at
            last = self.last_retest_at
            if (checked_at.tzinfo is None) != (last.tzinfo is None):
                checked_at = checked_at.replace(tzinfo=None)
                last = last.replace(tzinfo=None)
            if last < checked_at:
                raise ValueError("末次复测时刻不得早于抽检时刻")
        return self


class FastnessCheckUpdate(BaseModel):
    dye_lot_id: Optional[int] = Field(None, alias="dyeLotId")
    checked_at: Optional[datetime] = Field(None, alias="checkedAt")
    wash_fastness: Optional[int] = Field(None, ge=1, le=5, alias="washFastness")
    rub_fastness: Optional[float] = Field(None, gt=0, alias="rubFastness")
    temp_c: Optional[float] = Field(None, alias="tempC")
    notes: Optional[str] = None
    retest_count: Optional[int] = Field(None, ge=0, alias="retestCount")
    last_retest_at: Optional[datetime] = Field(None, alias="lastRetestAt")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("retest_count", mode="before")
    @classmethod
    def _retest_count_validator(cls, value):
        if value is None:
            return 0
        return _validate_nonneg_int(value)


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
