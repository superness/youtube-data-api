from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    rapidapi_proxy_secret: str
    redis_url: str = "redis://redis:6379"
    webshare_proxy_username: str
    webshare_proxy_password: str
    request_timeout: int = 15
    # Official YouTube Data API v3 key — used only by /trending (chart=mostPopular).
    # Everything else uses the keyless InnerTube path.
    youtube_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
