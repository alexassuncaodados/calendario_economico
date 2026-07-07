"""upserts no SQLite. eventos (dim) e ocorrencias (fact)."""

from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.engine import Engine

from calendario_economico.db import events_table, occurrences_table
from calendario_economico.models import EventRaw, OccurrenceRaw


def _event_dict(rec: EventRaw) -> dict:
    """converte EventRaw para dict do DB. updated_at settado aqui."""
    d = rec.model_dump()
    d["updated_at"] = datetime.now()
    return d


def _occurrence_dict(rec: OccurrenceRaw) -> dict:
    """converte OccurrenceRaw para dict do DB. collected_at settado aqui."""
    d = rec.model_dump()
    d["collected_at"] = datetime.now()
    return d


def upsert_events(engine: Engine, events: list[EventRaw]) -> int:
    """delete+insert por event_id. retorna qtd processada."""
    if not events:
        return 0

    records = [_event_dict(e) for e in events]
    with engine.begin() as conn:
        for rec in records:
            conn.execute(events_table.delete().where(events_table.c.event_id == rec["event_id"]))
            conn.execute(events_table.insert().values(**rec))
    return len(records)


def upsert_occurrences(engine: Engine, occurrences: list[OccurrenceRaw]) -> int:
    """upsert burro (delete+insert). usado em COLD. retorna qtd processada."""
    if not occurrences:
        return 0

    records = [_occurrence_dict(o) for o in occurrences]
    with engine.begin() as conn:
        for rec in records:
            conn.execute(
                occurrences_table.delete().where(
                    occurrences_table.c.occurrence_id == rec["occurrence_id"]
                )
            )
            conn.execute(occurrences_table.insert().values(**rec))
    return len(records)


def upsert_occurrences_with_diff(
    engine: Engine,
    occurrences: list[OccurrenceRaw],
) -> tuple[int, int, list[dict]]:
    """upsert com diff. usado em UPDATE.

    retorna (inserted, updated, changes).
    changes: [{occurrence_id, event_id, field, old, new, occurrence_time}, ...]
    """
    if not occurrences:
        return 0, 0, []

    inserted = 0
    updated = 0
    changes = []

    # campos que indicam mudanca de valor real
    value_fields = ["actual", "forecast", "previous"]

    with engine.begin() as conn:
        for occ in occurrences:
            new_rec = _occurrence_dict(occ)
            occ_id = new_rec["occurrence_id"]
            occ_time = new_rec["occurrence_time"]

            existing = conn.execute(
                select(occurrences_table).where(occurrences_table.c.occurrence_id == occ_id)
            ).fetchone()

            if existing is not None:
                existing_dict = existing._mapping
                changed = False
                for field in value_fields:
                    old_val = existing_dict.get(field)
                    new_val = new_rec.get(field)

                    # None vs None = igual
                    if old_val is None and new_val is None:
                        continue
                    if old_val != new_val:
                        changed = True
                        changes.append({
                            "occurrence_id": occ_id,
                            "event_id": new_rec["event_id"],
                            "field": field,
                            "old": old_val,
                            "new": new_val,
                            "occurrence_time": occ_time,
                        })

                if changed:
                    conn.execute(
                        occurrences_table.delete().where(
                            occurrences_table.c.occurrence_id == occ_id
                        )
                    )
                    conn.execute(occurrences_table.insert().values(**new_rec))
                    updated += 1
                # sem mudanca: preserva collected_at original
            else:
                conn.execute(occurrences_table.insert().values(**new_rec))
                inserted += 1

    return inserted, updated, changes


def get_last_occurrence_date(engine: Engine) -> datetime | None:
    """retorna MAX(occurrence_time) do DB ou None se vazio."""
    with engine.connect() as conn:
        result = conn.execute(select(func.max(occurrences_table.c.occurrence_time))).scalar()
    return result


def count_events(engine: Engine) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(events_table)).scalar() or 0


def count_occurrences(engine: Engine) -> int:
    with engine.connect() as conn:
        return (
            conn.execute(select(func.count()).select_from(occurrences_table)).scalar()
            or 0
        )


def min_max_occurrence_date(engine: Engine) -> tuple[datetime | None, datetime | None]:
    """retorna (min, max) de occurrence_time. usado no resumo final."""
    with engine.connect() as conn:
        min_d = conn.execute(select(func.min(occurrences_table.c.occurrence_time))).scalar()
        max_d = conn.execute(select(func.max(occurrences_table.c.occurrence_time))).scalar()
    return min_d, max_d