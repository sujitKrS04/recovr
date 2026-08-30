from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://recovr:recovr_dev@localhost:5432/recovr"
    OPENROUTER_API_KEY: str = ""
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    SECRET_KEY: str = "dev-secret-change-in-production"
    ENVIRONMENT: str = "development"


settings = Settings()
