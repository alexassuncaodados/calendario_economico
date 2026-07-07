"""modelos pydantic v2 para validar payload da API Investing.com.

extra="ignore" descarta campos desconhecidos.
datetime com suffix "Z" e parseado automaticamente por pydantic v2.
preliminary (bool na API) e coercido para int 0/1.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_naive_utc(dt: datetime) -> datetime:
    """despreza tzinfo. seAware, converte p/ UTC antes p/ nao deslocar o instante."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


class EventRaw(BaseModel):
    """dim economic_events. event_id obrigatorio, rest opcional."""

    model_config = ConfigDict(extra="ignore")

    event_id: int
    category: str | None = None
    country_id: int | None = None
    currency: str | None = None
    importance: str | None = None
    short_name: str | None = None
    long_name: str | None = None
    event_translated: str | None = None
    event_type: str | None = None
    event_cycle_suffix: str | None = None
    source: str | None = None
    source_url: str | None = None
    page_link: str | None = None
    description: str | None = None


class OccurrenceRaw(BaseModel):
    """fact economic_occurrences. occurrence_id e occurrence_time obrigatorios.

    preliminary bool -> int 0/1 via coerce.
    """

    model_config = ConfigDict(extra="ignore")

    occurrence_id: int
    event_id: int | None = None
    occurrence_time: datetime

    @field_validator("occurrence_time", mode="after")
    @classmethod
    def _strip_tz(cls, v: datetime) -> datetime:
        """ocorrencias salvas como naive UTC p/ bater schema legado."""
        return _to_naive_utc(v)
    actual: float | None = None
    forecast: float | None = None
    previous: float | None = None
    actual_to_forecast: str | None = None
    revised_to_previous: str | None = None
    precision: int | None = None
    preliminary: int = 0
    reference_period: str | None = None
    unit: str | None = None


class CalendarPayload(BaseModel):
    """payload raiz da API. so fields events e occurrences sao lidos."""

    model_config = ConfigDict(extra="ignore")

    events: list[EventRaw] = Field(default_factory=list)
    occurrences: list[OccurrenceRaw] = Field(default_factory=list)