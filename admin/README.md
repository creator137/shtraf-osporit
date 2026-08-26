# Admin

Read-only Stage 1 admin panel built with React, Vite, TypeScript, shadcn/ui, and Open Dashboard patterns.

## Local Setup

Use Node.js 20 or newer.

1. Copy the environment example:

   ```bash
   cp .env.example .env
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start the backend API from `backend/`:

   ```bash
   uv run uvicorn app.api.main:app --reload --port 8000
   ```

4. Start the admin from `admin/`:

   ```bash
   npm run dev
   ```

The admin opens at `http://localhost:5173`.
