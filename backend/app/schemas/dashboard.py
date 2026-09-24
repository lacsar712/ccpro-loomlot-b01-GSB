from pydantic import BaseModel, ConfigDict, Field


class DashboardStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dye_house_total: int = Field(serialization_alias="dyeHouseTotal")
    vat_ready_count: int = Field(serialization_alias="vatReadyCount")
    vat_dyeing_count: int = Field(serialization_alias="vatDyeingCount")
    lots_last_7d: int = Field(serialization_alias="lotsLast7d")
    checks_last_24h: int = Field(serialization_alias="checksLast24h")
    # 未关闭且复测未达标的染程数；与染程列表 retestUnmet=true 手数结果同一口径。
    lots_retest_pending: int = Field(serialization_alias="lotsRetestPending")
    # 色牢度复测规定次数（项目常量，至少 2）。
    required_retest_count: int = Field(serialization_alias="requiredRetestCount")
