# VPS Deployment

The production layout stays deliberately small:

```text
Caddy :443 -> static admin + FastAPI :8000
Telegram bot -> polling
FastAPI and bot -> PostgreSQL on 127.0.0.1:5432
```

Caddy protects both the admin and `/api/*` with HTTP Basic Auth. FastAPI and
PostgreSQL must not listen on a public interface.

## Server Setup

1. Install Git, Docker Engine with Compose, Caddy, Node.js 20+, and `uv`.
2. Create the `shtraf` system user and clone the repository to
   `/opt/shtraf-osporit`.
3. Create `/opt/shtraf-osporit/.env` from `.env.example`. Use generated database
   credentials and the current Telegram bot token. Keep mode `0600`.
4. Start PostgreSQL and prepare the backend:

   ```bash
   docker compose up -d postgres
   cd backend
   uv sync --frozen
   uv run alembic upgrade head
   ```

5. Build the admin against the same-origin API:

   ```bash
   cd admin
   npm ci
   VITE_API_URL=/api npm run build
   ```

6. Copy `deploy/shtraf-api.service` and `deploy/shtraf-bot.service` to
   `/etc/systemd/system/`, then enable both units.
7. Copy `deploy/Caddyfile` to `/etc/caddy/Caddyfile`. Put these values in
   `/etc/shtraf-osporit/caddy.env`:

   ```text
   SERVER_ADDRESS=<public IPv4 or domain>
   ADMIN_USERNAME=<admin username>
   ADMIN_PASSWORD_HASH=<output of caddy hash-password>
   ```

   Add `/etc/systemd/system/caddy.service.d/shtraf.conf`:

   ```ini
   [Service]
   EnvironmentFile=/etc/shtraf-osporit/caddy.env
   ```

8. Allow inbound SSH, HTTP, and HTTPS only. Do not expose ports `5432` or `8000`.

## Updating

Pull only committed changes, repeat `uv sync --frozen`, migrations, and the
admin build, then restart `shtraf-api`, `shtraf-bot`, and reload Caddy.
