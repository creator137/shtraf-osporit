# Backend

Python 3.12 backend foundation with async SQLAlchemy 2, PostgreSQL, Alembic, Pydantic, and pytest.

## Local Setup

1. Create the local environment file and fill in all values:

   ```bash
   cp .env.example .env
   ```

   `DATABASE_URL` must use the async driver, for example:

   ```text
   postgresql+asyncpg://<user>:<password>@localhost:5432/<database>
   ```

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
