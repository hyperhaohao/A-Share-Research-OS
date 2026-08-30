# Deployment Preparation — PostgreSQL Compatibility Verified

Date: 2026-08-30
Method: disposable PostgreSQL 16 container + full migration chain + API smoke

## Results

- **Alembic**: all 12 migrations (PW0 → deep c) ran clean on PG 16
- **Read Models**: all 6 /views/* endpoints 200 OK on PG
- **Write path**: watchlist add → persisted → view read-back correct
- **Source health**: operational on PG
- **psycopg2-binary**: added to backend venv (production driver)

## SQLite-specific code (contained, no action needed)

- `db.py` pragma listener: gated by `url.startswith("sqlite")` — no-op on PG
- `config.py` default: `sqlite:///./asro_dev.db` — overridden by `ASRO_DATABASE_URL`
- No raw SQL, no SQLite-only functions, no JSON path queries in application code

## Production deployment checklist

1. `ASRO_DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/asro`
2. `alembic upgrade head` (idempotent)
3. TLS termination at reverse proxy (nginx/Caddy) — backend serves plain HTTP
4. Authentication: not yet implemented (next candidate)
5. `psycopg2-binary` must be in production requirements (already in venv)
