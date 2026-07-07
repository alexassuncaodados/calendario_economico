# Calendário econômico

Coleta o calendário econômico do Investing.com e persiste em SQLite local. Detecção automática e update incremental (com diff de revisões). Validação de payload via pydantic v2 e configuração (pydantic-settings).

## Instalação

```bash
git clone <repo>
cd calendario_economico
pip install -r requirements.txt
```

## Uso

```bash
# pelo modulo
python -m calendario_economico

# ou pelo script
python run.py
```

Os dois entry points são equivalentes. O script roda em no primeiro uso (DB vazio) e UPDATE nas execuções seguintes.

## Variaveis de Ambiente

Todas opcionais. Defaults já cobrem o uso padrão.

| Variável                   | Default                                                                                   | Descrição                                                  |
| -------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `CALENDAR_BASE_URL`        | `https://endpoints.investing.com/pd-instruments/v1/calendars/economic/events/occurrences` | Endpoint da API                                            |
| `CALENDAR_START_DATE`      | `2026-01-01`                                                                              | Data inicial do cold start (YYYY-MM-DD)                    |
| `CALENDAR_TIMEZONE_OFFSET` | `-03:00`                                                                                  | Offset de TZ nos params start_date/end_date enviados a API |
| `CALENDAR_COUNTRY_IDS`     | `6,37,39,35,4,5,72`                                                                       | IDs de países (comma separated)                            |
| `CALENDAR_DOMAIN_ID`       | `30`                                                                                      | Domain ID da API                                           |
| `CALENDAR_LIMIT`           | `500`                                                                                     | Limite de resultados por request                           |
| `CALENDAR_THRESHOLD_DAYS`  | `7`                                                                                       | Gap em dias que alterna estrategia de chunking em UPDATE   |
| `CALENDAR_REQUEST_DELAY`   | `2.0`                                                                                     | Segundos entre requests                                    |
| `CALENDAR_MAX_RETRIES`     | `3`                                                                                       | Tentativas de retry                                        |
| `CALENDAR_RETRY_BACKOFF`   | `2`                                                                                       | Fator do backoff exponencial                               |
| `CALENDAR_DB_NAME`         | `economic_calendar.db`                                                                    | Nome do arquivo SQLite                                     |
| `CALENDAR_LOG_LEVEL`       | `INFO`                                                                                    | Nivel de log (`INFO` ou `DEBUG`)                           |

## Modos de Operação

```
                   get_last_occurrence_date()
                            |
              +-------------+-------------+
              |                           |
            None                      datetime
            COLD                       UPDATE
              |                           |
   start_date -> today         PASSO 1: re-check last_day
   weekly chunks               upsert_occurrences_with_diff
   upsert burro (delete+insert)        |
   sem diff                   PASSO 2: next_day -> today
                              gap > threshold -> weekly
                              gap <= threshold -> 7d blocks
                              upsert_occurrences_with_diff
                              (detecta revisoes actual/forecast/previous)
```

- **COLD**: banco vazio. Coleta `START_DATE -> today` em chunks semanais. Upsert (delete+insert por `occurrence_id`).
- **UPDATE**: banco populado. Re-check do último dia (detecta revisoes), depois coleta `last_day+1 -> today`. Upsert com diff de `actual`/`forecast`/`previous`.

## Estrutura do Projeto

```
calendario_economico/
├── README.md
├── requirements.txt
├── .gitignore
├── run.py                          # entry point: python run.py
├── base/                           # SQLite criado aqui
│   └── .gitkeep
└── calendario_economico/           # pacote python
    ├── __init__.py
    ├── __main__.py                 # entry point: python -m calendario_economico
    ├── settings.py                 # Settings (pydantic-settings)
    ├── models.py                   # EventRaw, OccurrenceRaw, CalendarPayload (pydantic v2)
    ├── db.py                       # SQLAlchemy Core: tables + get_engine
    ├── client.py                   # requests Session + fetch_data + retry/backoff
    ├── chunks.py                   # generate_weekly_ranges, generate_daily_blocks
    ├── repository.py               # upserts (events, occurrences, occurrences_with_diff)
    ├── logging_config.py           # basicConfig
    └── pipeline.py                 # process_chunk + main (mode detection)
```

| Modulo              | Responsabilidade                                                   |
| ------------------- | ------------------------------------------------------------------ |
| `settings.py`       | Defaults do pipeline.                                              |
| `models.py`         | Modelos pydantic v2 que validam payload da API.                    |
| `db.py`             | Schema SQLAlchemy Core e `get_engine()`.                           |
| `client.py`         | GET na API com retry/backoff em 429 e outros erros.                |
| `chunks.py`         | Particiona ranges de datas em chunks semanais ou blocos de N dias. |
| `repository.py`     | Upserts no SQLite (delete+insert ou diff de revisoes).             |
| `logging_config.py` | `basicConfig` com nivel configuravel.                              |
| `pipeline.py`       | Orquestra fetch -> valida -> upsert. Detecta COLD/UPDATE.          |

## Banco de Dados

SQLite em `base/economic_calendar.db` (criado automaticamente no primeiro run). Schema:

- `economic_events` (dim) - um row por evento (CPI, NFP, etc). PK `event_id`.
- `economic_occurrences` (fact) - um row por data de ocorrencia com `actual`/`forecast`/`previous`. PK `occurrence_id`. FK logico `event_id`. Indices em `event_id` e `occurrence_time`.

## Notas

- API Investing.com pode rate-limit (429). Cliente aguarda `RETRY_BACKOFF^attempt * 5s` e tenta de novo.
- Payloads com campos desconhecidos sao aceitos (`extra="ignore"`). Campos obrigatorios ausentes rejeitam o chunk inteiro.
