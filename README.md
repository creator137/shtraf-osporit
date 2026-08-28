# Shtraf.Osporit

Shtraf.Osporit is a Telegram-based service with a small web admin panel for working with traffic fine appeal cases.

The documented stack is Python 3.12, aiogram 3, PostgreSQL, SQLAlchemy 2, Alembic, Pydantic, and pytest for the backend; React, Vite, TypeScript, shadcn/ui, and Open Dashboard patterns for the admin; and Git, GitHub, Docker, and Docker Compose for infrastructure as needed.

The project is currently at **Stage 3 - Legal Questionnaire + Rules Engine**. The foundation, Telegram case flow, admin panel, and OCR workflow are initialized; the current work adds deterministic legal verification directions from factual user answers.

- Current scope: [`docs/CURRENT_STAGE.md`](docs/CURRENT_STAGE.md)
- Short roadmap: [`docs/ROADMAP.md`](docs/ROADMAP.md)
- Accepted decisions: [`docs/DECISIONS.md`](docs/DECISIONS.md)
- Codex instructions: [`AGENTS.md`](AGENTS.md)
- VPS deployment: [`deploy/README.md`](deploy/README.md)
- User guide: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)
