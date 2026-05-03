from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MatrixCommonSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    matrix_homeserver_url: str = Field("http://synapse:8008")
    matrix_bot_access_token: str = Field(...)
    matrix_bot_user_id: str = Field(...)
    matrix_default_destination: str = Field("home")
    matrix_destinations_json: str = Field("{}")
    matrix_rate_limit: str = Field("30/minute")
