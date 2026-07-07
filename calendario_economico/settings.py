"""settings via pydantic-settings. le env vars com prefixo CALENDAR_. defaults no proprio modulo."""

from datetime import datetime
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# headers anti-block do Investing.com. mesmos do script legado.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://br.investing.com",
    "Referer": "https://br.investing.com/economic-calendar/",
}


class Settings(BaseSettings):
    """configuracao do pipeline."""

    model_config = SettingsConfigDict(
        env_prefix="CALENDAR_",
        extra="ignore",
    )

    # API
    base_url: str = "https://endpoints.investing.com/pd-instruments/v1/calendars/economic/events/occurrences"
    # 6=BR, 37=US, 39=EU, 35=UK, 4=DE, 5=FR, 72=JP
    country_ids: str = "6,37,39,35,4,5,72"
    domain_id: int = 30
    limit: int = 500

    # datas
    start_date: datetime = datetime(2026, 1, 1)
    timezone_offset: str = "-03:00"
    threshold_days: int = 7

    # rate limit / retry
    request_delay: float = 2.0
    max_retries: int = 3
    retry_backoff: int = 2

    # DB
    db_dir: Path = Path(__file__).resolve().parent.parent / "base"
    db_name: str = "economic_calendar.db"

    # logging
    log_level: str = "INFO"

    @property
    def db_path(self) -> Path:
        """caminho completo do sqlite."""
        return self.db_dir / self.db_name


def get_settings() -> Settings:
    """factory. instancia Settings lendo env."""
    return Settings()