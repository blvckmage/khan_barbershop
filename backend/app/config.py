from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Alteegio API
    alteegio_bearer_token: str
    alteegio_user_token: str
    alteegio_company_id: str
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"
    
    # Google Sheets
    google_credentials_path: str = "./credentials.json"
    staff_spreadsheet_id: str
    services_spreadsheet_id: str
    
    # WhatsApp Business Cloud API
    whatsapp_api_url: str = "https://graph.facebook.com"
    whatsapp_api_version: str = "v17.0"
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_verify_token: str = ""
    # WhatsApp Business Account ID (needed for template management)
    whatsapp_waba_id: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    @property
    def alteegio_auth_header(self) -> str:
        return f"Bearer {self.alteegio_bearer_token}, User {self.alteegio_user_token}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()