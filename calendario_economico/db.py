"""schema SQLAlchemy Core. mesmas colunas e indices do script legado."""

from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine

from calendario_economico.settings import Settings


metadata_obj = MetaData()

# dim eventos
events_table = Table(
    "economic_events",
    metadata_obj,
    Column("event_id", Integer, primary_key=True),
    Column("category", String(50)),
    Column("country_id", Integer),
    Column("currency", String(10)),
    Column("importance", String(10)),
    Column("short_name", String(200)),
    Column("long_name", String(500)),
    Column("event_translated", String(500)),
    Column("event_type", String(50)),
    Column("event_cycle_suffix", String(50)),
    Column("source", String(200)),
    Column("source_url", String(500)),
    Column("page_link", String(500)),
    Column("description", Text),
    Column("updated_at", DateTime),
)

# fact ocorrencias
occurrences_table = Table(
    "economic_occurrences",
    metadata_obj,
    Column("occurrence_id", Integer, primary_key=True),
    Column("event_id", Integer, index=True),
    Column("occurrence_time", DateTime, index=True),
    Column("actual", Float),
    Column("forecast", Float),
    Column("previous", Float),
    Column("actual_to_forecast", String(20)),
    Column("revised_to_previous", String(20)),
    Column("precision", Integer),
    Column("preliminary", Integer),
    Column("reference_period", String(50)),
    Column("unit", String(20)),
    Column("collected_at", DateTime),
)


def get_engine(settings: Settings) -> Engine:
    """cria pasta db_dir se nao existe, cria engine sqlite, cria tabelas."""
    settings.db_dir.mkdir(parents=True, exist_ok=True)
    db_path: Path = settings.db_path
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    metadata_obj.create_all(engine)
    return engine