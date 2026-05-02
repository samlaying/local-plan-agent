from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://local_plan:local_plan_password@localhost:5432/local_plan_agent"
    mock_data_dir: str = "data/mock"
    use_mock_poi: bool = True
    use_mock_restaurant: bool = True
    use_mock_execution: bool = True
    amap_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
