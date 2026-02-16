# Backend quickstart (FastAPI)

## Recommended libraries (start pack)
- `fastapi` + `uvicorn` — API
- `pydantic`, `pydantic-settings` — schema + config
- `sqlalchemy` + `alembic` + `psycopg` — PostgreSQL ORM/migrations/driver
- `redis` — cache/locks/timers
- `pytest` + `httpx` — tests

## VS Code setup
Install extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Ruff (charliermarsh.ruff)
- PostgreSQL (ms-ossdata.vscode-postgresql)
- REST Client (humao.rest-client)

Recommended settings (`.vscode/settings.json`):
```json
{
  "python.analysis.typeCheckingMode": "basic",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true
}
```


## Storage backend mode
By default app runs in-memory mode.
Set PostgreSQL mode via env:
```bash
export STORAGE_BACKEND=postgres
```

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test
```bash
pytest -q
```

## Database migration (Alembic)
```bash
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/rpg"
alembic upgrade head
```

Alternative manual SQL:
```bash
psql "$DATABASE_URL" -f db/migrations/001_init.sql
```

## Dev helper script
```bash
DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/rpg" ./scripts/dev_migrate.sh
```
