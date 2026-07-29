from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "EmployeeMint"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://hrms:hrms@localhost:5432/hrms"
    database_url_sync: str = "postgresql+psycopg://hrms:hrms@localhost:5432/hrms"

    redis_url: str = "redis://localhost:6379/0"

    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "hrms-documents"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    platform_admin_email: str = "admin@employeemint.local"
    platform_admin_password: str = "changeme"

    tenant_routing_mode: str = "path"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
