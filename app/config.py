from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret: str
    database_url: str
    redis_host: str
    redis_port: int
    secret: str
    max_age_auth_links_days: int = 30


settings = Settings()