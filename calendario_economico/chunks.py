"""helpers de particao de datas em chunks para coleta em batches."""

from datetime import datetime, timedelta


def generate_weekly_ranges(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """intervalos semanais (segunda -> domingo).

    primeira semana pode comecar antes da segunda se start nao e segunda.
    """
    weeks = []
    current = start

    while current <= end:
        # fim da semana: domingo ou end, o que vier primeiro
        week_end = current + timedelta(days=6 - current.weekday())
        if week_end > end:
            week_end = end

        weeks.append((current, week_end))

        # proxima segunda
        current = week_end + timedelta(days=1)
        while current.weekday() != 0 and current <= end:
            current += timedelta(days=1)

    return weeks


def generate_daily_blocks(
    start: datetime,
    end: datetime,
    block_size: int = 7,
) -> list[tuple[datetime, datetime]]:
    """blocos contiguos de block_size dias. ultimo bloco truncado em end."""
    blocks = []
    cur = start
    while cur <= end:
        block_end = min(cur + timedelta(days=block_size - 1), end)
        blocks.append((cur, block_end))
        cur = block_end + timedelta(days=1)
    return blocks