"""cliente HTTP da API Investing.com. retry com backoff exponencial."""

import logging
import time
from datetime import datetime

import requests

from calendario_economico.settings import Settings, HEADERS

log = logging.getLogger(__name__)


def format_date_param(dt: datetime, settings: Settings, is_end: bool = False) -> str:
    """formata datetime para o param start_date/end_date da API com offset de TZ."""
    if is_end:
        return f"{dt.strftime('%Y-%m-%d')}T23:59:59.999{settings.timezone_offset}"
    return f"{dt.strftime('%Y-%m-%d')}T00:00:00.000{settings.timezone_offset}"


def fetch_data(
    session: requests.Session,
    settings: Settings,
    start: datetime,
    end: datetime,
) -> dict | None:
    """GET na API para um intervalo. retry com backoff exponencial. retorna dict ou None."""
    params = {
        "domain_id": settings.domain_id,
        "limit": settings.limit,
        "start_date": format_date_param(start, settings, is_end=False),
        "end_date": format_date_param(end, settings, is_end=True),
        "country_ids": settings.country_ids,
    }

    last_status = 0
    for attempt in range(1, settings.max_retries + 1):
        try:
            resp = session.get(settings.base_url, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            last_status = resp.status_code
            if resp.status_code == 429:
                wait = settings.retry_backoff ** attempt * 5
                log.warning(f"429 rate limited. {wait}s (tentativa {attempt}/{settings.max_retries})")
            else:
                log.warning(f"HTTP {resp.status_code}: {e} (tentativa {attempt}/{settings.max_retries})")
            if attempt < settings.max_retries:
                time.sleep(settings.retry_backoff ** attempt)
        except requests.exceptions.RequestException as e:
            log.warning(f"request error: {e} (tentativa {attempt}/{settings.max_retries})")
            if attempt < settings.max_retries:
                time.sleep(settings.retry_backoff ** attempt)

    log.error(f"falhou apos {settings.max_retries} tentativas (ultimo status={last_status})")
    return None