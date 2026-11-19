from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    prometheus_url: str
    ollama_url: str
    keycloak_url: str
    keycloak_realm: str

    class Config:
        env_file = ".env"

settings = Settings()