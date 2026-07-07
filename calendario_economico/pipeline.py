"""orquestracao: process_chunk + main() com deteccao automatica COLD/UPDATE."""

import logging
import time
from datetime import datetime, timedelta

import requests
from pydantic import ValidationError

from calendario_economico import chunks, client, repository
from calendario_economico.db import get_engine
from calendario_economico.logging_config import setup_logging
from calendario_economico.models import CalendarPayload
from calendario_economico.settings import Settings

log = logging.getLogger(__name__)


def process_chunk(
    engine,
    session: requests.Session,
    settings: Settings,
    start: datetime,
    end: datetime,
    upserter_fn,
    log_diff: bool = False,
) -> tuple[int, int, list[dict]]:
    """fetch + valida + upsert de um chunk (start, end).

    upserter_fn: repository.upsert_occurrences (COLD) ou
                 repository.upsert_occurrences_with_diff (UPDATE).
    log_diff: se True, loga revisoes em DEBUG.
    """
    label = f"{start.strftime('%Y-%m-%d')}->{end.strftime('%Y-%m-%d')}"

    data = client.fetch_data(session, settings, start, end)
    if data is None:
        log.error(f"[{label}] falhou fetch")
        return 0, 0, []

    try:
        payload = CalendarPayload.model_validate(data)
    except ValidationError as e:
        log.error(f"[{label}] payload invalido: {e}")
        return 0, 0, []

    repository.upsert_events(engine, payload.events)

    if upserter_fn is repository.upsert_occurrences_with_diff:
        ins, upd, chgs = upserter_fn(engine, payload.occurrences)
        if log_diff and chgs:
            for c in chgs:
                log.debug(
                    f"REV event={c['event_id']} occ={c['occurrence_id']} "
                    f"{c['field']}: {c['old']}->{c['new']} ({c['occurrence_time']})"
                )
        log.info(f"[{label}] +{ins} upd={upd} rev={len(chgs)} (api={len(payload.occurrences)})")
        return ins, upd, chgs
    else:
        n = upserter_fn(engine, payload.occurrences)
        log.info(f"[{label}] +{n}")
        return n, 0, []


def main() -> None:
    """entry point. detecta COLD x UPDATE automaticamente."""
    settings = Settings()
    setup_logging(settings.log_level)

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    log.info(f"iniciando | db={settings.db_path}")
    engine = get_engine(settings)
    session = requests.Session()

    total_inserted = 0
    total_updated = 0
    all_changes: list[dict] = []

    last_date = repository.get_last_occurrence_date(engine)

    if last_date is None:
        # COLD - DB vazio
        log.info(f"COLD | {settings.start_date.strftime('%Y-%m-%d')}->{today.strftime('%Y-%m-%d')}")
        chunk_list = chunks.generate_weekly_ranges(settings.start_date, today)
        upserter_fn = repository.upsert_occurrences
        log_diff = False

        for i, (cs, ce) in enumerate(chunk_list, 1):
            ins, upd, chgs = process_chunk(engine, session, settings, cs, ce, upserter_fn, log_diff)
            total_inserted += ins
            total_updated += upd
            all_changes.extend(chgs)
            if i < len(chunk_list):
                time.sleep(settings.request_delay)
    else:
        # UPDATE - DB populado
        last_day = last_date.replace(hour=0, minute=0, second=0, microsecond=0)
        log.info(f"UPDATE | ultimo={last_day.strftime('%Y-%m-%d')}")
        upserter_fn = repository.upsert_occurrences_with_diff
        log_diff = True

        # PASSO 1: re-check do ultimo dia (detecta revisoes)
        ins, upd, chgs = process_chunk(
            engine, session, settings, last_day, last_day, upserter_fn, log_diff
        )
        total_inserted += ins
        total_updated += upd
        all_changes.extend(chgs)

        # PASSO 2: coleta novos dias
        next_day = last_day + timedelta(days=1)
        gap = (today - last_day).days

        if next_day > today:
            log.info("sem dias novos")
        else:
            log.info(f"novos | {next_day.strftime('%Y-%m-%d')}->{today.strftime('%Y-%m-%d')} | gap={gap}d")
            if gap > settings.threshold_days:
                chunk_list = chunks.generate_weekly_ranges(next_day, today)
            else:
                chunk_list = chunks.generate_daily_blocks(next_day, today, block_size=7)

            for i, (cs, ce) in enumerate(chunk_list, 1):
                if i > 1:
                    time.sleep(settings.request_delay)
                ins, upd, chgs = process_chunk(
                    engine, session, settings, cs, ce, upserter_fn, log_diff
                )
                total_inserted += ins
                total_updated += upd
                all_changes.extend(chgs)

    # resumo
    ev_count = repository.count_events(engine)
    occ_count = repository.count_occurrences(engine)
    min_d, max_d = repository.min_max_occurrence_date(engine)

    log.info(
        f"fim | events={ev_count} occ={occ_count} "
        f"+ins={total_inserted} upd={total_updated} rev={len(all_changes)}"
    )
    if min_d and max_d:
        log.info(f"periodo | {min_d.strftime('%Y-%m-%d')}->{max_d.strftime('%Y-%m-%d %H:%M')}")