from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://local_plan:local_plan_password@localhost:5432/local_plan_agent"
    mock_data_dir: str = "data/mock"
    use_mock_poi: bool = True
    use_mock_restaurant: bool = True
    use_mock_execution: bool = True
    amap_api_key: str = ""

    # LLM
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
