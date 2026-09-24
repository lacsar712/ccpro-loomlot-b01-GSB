from pydantic import BaseModel, ConfigDict, Field


class DashboardStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dye_house_total: int = Field(serialization_alias="dyeHouseTotal")
    vat_ready_count: int = Field(serialization_alias="vatReadyCount")
    vat_dyeing_count: int = Field(serialization_alias="vatDyeingCount")
    lots_last_7d: int = Field(serialization_alias="lotsLast7d")
    checks_last_24h: int = Field(serialization_alias="checksLast24h")
    # 未关闭且复测未达标的染程数；与 GET /api/dye-lots?closed=false&retestUnmet=true
    # 返回的行数严格一致（共用 DyeLot.open_retest_unmet_criterion）
    open_retest_unmet_count: int = Field(serialization_alias="openRetestUnmetCount")
    required_retest_count: int = Field(serialization_alias="requiredRetestCount")
