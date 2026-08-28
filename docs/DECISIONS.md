# Accepted Decisions

1. Python is the primary backend language.
2. aiogram 3 is used for Telegram.
3. PostgreSQL, SQLAlchemy 2, and Alembic are used for data storage and schema management.
4. React, Vite, and TypeScript are used for the simple admin panel.
5. shadcn/ui is the primary UI component system.
6. Open Dashboard is the source of ready-made dashboard patterns and components.
7. The architecture intentionally remains simple.
8. Future functionality is not implemented in advance.
9. Telegram business logic must not live directly in handlers.
10. External providers are selected only when their stage begins; OCR.space is used for Stage 2, while an LLM provider is not selected yet.
11. Stage 2 starts with OCR, basic field extraction, and manual correction only.
12. Legal analysis, cancellation probability, and complaint generation remain outside Stage 2.
13. Production runs on one small VPS with PostgreSQL bound to localhost.
14. Caddy serves the admin and proxies the API; Telegram uses polling.
15. OCR.space is the first OCR provider and is enabled only through environment configuration.
