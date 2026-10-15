# orchestra-opportunity-agent

An automated agent that tracks orchestra auditions (Concertmaster, Principal /
First / Tutti Violin), evaluates their relevance with Gemini Flash, and sends
notifications via Slack and email.

## How It Works

1. **Collectors** (`app/collectors/`) gather opportunities from multiple sources:
   - Muvac
   - Musical Chairs
   - A manually maintained list of Czech orchestras
   - A manually maintained list of Czech violin-teaching sources (conservatories,
     HAMU/JAMU, and portals listing music schools)
2. **Evaluator** (`app/agents/evaluator.py`) uses Gemini Flash (or Groq; see below)
   to extract the position, orchestra, city, country, and deadline, and assigns a
   relevance score from 0 to 100.
3. **Storage** (`app/storage/database.py`) saves results in SQLite and prevents
   duplicates based on URL.
4. **Notifications** (`app/notifications/`) send Slack and email notifications
   for opportunities with a score at or above `MIN_SCORE`.

## Local Setup

```bash
poetry install

cp .env.example .env
# Set GEMINI_API_KEY and, if needed, SMTP / Slack credentials.

poetry run python main.py
```

## GraphQL API

The API provides read-only GraphQL at `/graphql` and a health check at `/health`.
Set a non-empty `API_TOKEN` in `.env` before starting the server:

```bash
poetry run uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload
```

Send GraphQL requests with the `Authorization: Bearer <API_TOKEN>` header. The
`opportunities` query supports `limit` (1–100), `offset`, `minScore`, `source`,
`country`, and text search via `search`. Use `opportunity(id)` to fetch one record
and `weeklyReport(days)` to generate a text report.

`API_TOKEN` is a server-side bearer token intended for the initial version. Do not
embed it in a mobile app. Before a public mobile release, add user authentication
and short-lived tokens (for example, OAuth/OIDC). The API remains closed when the
token is empty.

## MCP Server

The local MCP server uses the same query service and provides tools to search for
opportunities, fetch an opportunity, and generate a weekly report. Start it over
stdio with:

```bash
poetry run python -m app.mcp_server
```

## Tests

```bash
poetry install --with dev
poetry run pytest
```

Run lint and type checks:

```bash
poetry run ruff check .
poetry run mypy app config.py main.py
```

Run all checks (lint, type checks, and tests) together:

```bash
poetry run poe check
```

## Configuration

Settings are loaded from environment variables or `.env`; see
[.env.example](.env.example) and [config.py](config.py):

| Variable | Description |
| --- | --- |
| `EVAL_PROVIDER` | Evaluator backend: `gemini` (default) or `groq` |
| `GEMINI_API_KEY` | Google Gemini API key (required when `EVAL_PROVIDER=gemini`) |
| `GEMINI_MODEL` | Model name; defaults to `gemini-flash-latest` |
| `GEMINI_FALLBACK_MODELS` | Comma-separated fallback models tried on 503/404 errors |
| `GEMINI_MIN_INTERVAL_SECONDS` | Minimum delay between Gemini requests in seconds; helps avoid free-tier 429 errors; defaults to `6.5` |
| `GROQ_API_KEY` | [Groq](https://console.groq.com) API key (required when `EVAL_PROVIDER=groq`) |
| `GROQ_MODEL` | Model name; defaults to `llama-3.3-70b-versatile` |
| `GROQ_FALLBACK_MODELS` | Comma-separated fallback models |
| `GROQ_MIN_INTERVAL_SECONDS` | Minimum delay between Groq requests in seconds; defaults to `0` (Groq has higher free-tier limits) |
| `DATABASE_URL` | SQLAlchemy URL; defaults to SQLite |
| `API_TOKEN` | Bearer token required by the GraphQL API; the API is closed when empty |
| `MIN_SCORE` | Minimum score required for a notification; defaults to `80` |
| `SLACK_WEBHOOK` | Slack Incoming Webhook URL |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | SMTP connection settings (SSL) |
| `EMAIL_RECIPIENT` | Email notification recipient |

## GitHub Actions

The workflow [.github/workflows/run.yml](.github/workflows/run.yml) runs the agent
every six hours. Add secrets under *Settings → Secrets and variables → Actions*.

## Collector Notes

The HTML selectors in `muvac.py` and `musicalchairs.py` are best-effort and may
need adjustment if those websites change their markup. If a collector fails, it
returns an empty list instead of crashing (see `BaseCollector.safe_collect`).

## Future Improvements

- Web dashboard using the FastAPI backend
- RSS feed for collected auditions
- Expand audition coverage to neighboring countries (SK, AT, DE)
