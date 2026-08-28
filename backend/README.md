# Backend

Python 3.12 backend with aiogram 3, FastAPI, async SQLAlchemy 2, PostgreSQL, Alembic, Pydantic, and pytest.

## Local Setup

1. Create the local environment file and fill in all values:

   ```bash
   cp .env.example .env
   ```

   `DATABASE_URL` may use a regular PostgreSQL URL or the async driver, for example:

   ```text
   postgresql+asyncpg://<user>:<password>@localhost:5432/<database>
   ```

   Set `BOT_TOKEN` to the test bot token. `ADMIN_ORIGIN` defaults to
   `http://localhost:5173`. Keep `.env` local and never commit it.

2. From the repository root, start PostgreSQL:

   ```bash
   docker compose up -d postgres
   ```

3. Install the backend dependencies:

   ```bash
   cd backend
   uv sync
   ```

4. Apply database migrations:

   ```bash
   uv run alembic upgrade head
   ```

5. Run tests:

   ```bash
   uv run pytest
   ```

6. Start the admin API at `http://localhost:8000`:

   ```bash
   uv run uvicorn app.api.main:app --reload --port 8000
   ```

7. Start the Telegram bot when needed:

   ```bash
   uv run python -m app.bot.main
   ```

Uploaded documents are stored under `backend/storage/cases/`. This directory is ignored by Git.

Production VPS commands and service templates are documented in
[`deploy/README.md`](../deploy/README.md).
