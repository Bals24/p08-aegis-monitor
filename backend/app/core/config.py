from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://aegis:aegis@postgres:5432/aegis"
    prometheus_url: str = "http://prometheus:9090"
    ollama_url: str = "http://ollama:11434"
    keycloak_url: str = "http://keycloak:8080"
    keycloak_realm: str = "aegis"

    class Config:
        env_file = ".env"


settings = Settings()