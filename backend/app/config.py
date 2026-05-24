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
    # Meta App Secret — used to verify X-Hub-Signature-256 on incoming webhooks.
    # Found in Meta Developer Console → App Settings → Basic → App Secret.
    # If empty, signature verification is SKIPPED (insecure, dev only!).
    whatsapp_app_secret: str = ""

    # ── Cost / safety limits ────────────────────────────────────────────────
    # Daily OpenAI spend cap (USD). When exceeded, bot returns a polite message
    # and stops calling OpenAI until midnight. 0 = no cap.
    openai_daily_limit_usd: float = 10.0
    # Pricing for gpt-4.1-mini ($/1M tokens). Override if you use another model.
    openai_input_price_per_1m: float = 0.40
    openai_output_price_per_1m: float = 1.60

    # ── Data retention (days) ───────────────────────────────────────────────
    log_retention_days: int = 90
    webhook_dedup_retention_hours: int = 24

    # ── Approved Meta template names for automated reminders ──────────────
    # Set these to the APPROVED template names (status=APPROVED in Meta).
    # If empty, the reminder falls back to plain text (works only inside
    # the 24-hour customer reply window).
    template_one_hour_reminder: str = ""   # body params: {{1}}=name, {{2}}=master, {{3}}=time
    template_revisit_reminder: str = ""    # body params: {{1}}=name, {{2}}=last_visit_date
    template_nps_request: str = ""         # body params: {{1}}=name, {{2}}=master
    template_language: str = "ru"          # language code of the templates above

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