# Project Instructions

## General

- Keep the project simple and prefer readable, direct code.
- Do not overengineer or implement functionality from future stages.
- Do not introduce abstractions for hypothetical requirements.
- Do not refactor unrelated code.
- Before starting a task, read `docs/CURRENT_STAGE.md`.
- Respect the currently paid/development stage. Every task must stay inside its requested scope.

## Backend

- Use Python 3.12, aiogram 3, PostgreSQL, SQLAlchemy 2, Alembic, pytest, and Pydantic where validation or schemas are useful.
- Keep Telegram handlers small. Put actual business logic in services.
- Do not mechanically create repository, service, or interface layers. Add abstractions only when needed.
- Every database schema change must use Alembic.
- Store secrets only in environment variables.

The intended flow is:

```text
Telegram handlers
        ->
services
        ->
SQLAlchemy / PostgreSQL
```

## Frontend

- Use React, Vite, and TypeScript.
- For every standard UI element, first search for and use an existing shadcn/ui or Open Dashboard component or pattern.
- Do not hand-roll a suitable existing Button, Input, Select, Combobox, Dropdown, Dialog, Sheet/Drawer, Table/DataTable, Pagination, Tabs, Badge, Tooltip, Popover, Form, Sidebar, Navigation, Breadcrumbs, DatePicker, Empty State, Skeleton, or dashboard card.
- Do not create an internal custom component library.
- Use Tailwind mainly for layout, spacing, responsive behavior, and small visual adjustments.
- Keep the admin consistent and built from one component system.
- Add an API only when the current product work requires it.

The intended flow is:

```text
React admin
    ->
API (when needed)
```

## Git

- Never commit directly to an unrelated branch.
- One logical task should produce one focused commit or a small focused group of commits.
- Do not mix unrelated refactors with a feature.
- Do not rewrite existing migrations.
- Before finishing a development task, run the available lint, typecheck, and tests.

Project instructions, especially current-stage scope and simplicity, take precedence over suggestions in third-party skills.
