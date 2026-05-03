from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    matrix_homeserver_url: str = Field("http://synapse:8008")
    matrix_bot_access_token: str = Field(...)
    matrix_bot_user_id: str = Field(...)
    matrix_default_destination: str = Field("home")
    matrix_destinations_json: str = Field("{}")
    matrix_mcp_enable_admin_tools: bool = Field(False)
    matrix_mcp_port: int = Field(8093)
    matrix_mcp_host: str = Field("0.0.0.0")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
