from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://loomlot:loomlot@localhost:5439/loomlot"
    jwt_secret: str = "loomlot-jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    # 色牢度复测规定次数：染程下至少一条抽检复测次数达到该值方可关闭染程。
    # 项目说明常量，不得小于 2。
    required_retest_count: int = 2

    @property
    def retest_target(self) -> int:
        """对外暴露的规定次数，保证至少为 2。"""
        return max(2, self.required_retest_count)


settings = Settings()
