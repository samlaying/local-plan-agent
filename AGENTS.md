# Repository Guidelines

## Project Structure & Module Organization

Local activity planning agent with a Next.js frontend and FastAPI backend.

- `apps/web`: Next.js frontend. App routes live in `src/app`, utilities in `src/lib`, planning types in `src/types`.
- `services/api`: FastAPI backend. Routes are in `app/routes`, schemas in `app/schemas`, workflow logic in `app/services`, and data access in `app/repositories`.
- `data/mock`: Mock POI, activity, restaurant, queue, and scenario data.
- `data/migrations`: PostgreSQL migration SQL.
- `docs`: product, architecture, and API notes.
- `infra/docker`: Dockerfiles for local runtime.
- `packages`: reserved for shared types and scoring logic.

## Build, Test, and Development Commands

From `apps/web`:

- `npm run dev`: run the frontend development server.
- `npm run build`: build the Next.js app.
- `npm run typecheck`: run TypeScript checks.
- `npm run lint`: run frontend linting when supported.

From `services/api`:

- `uv run uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000 --reload`: run the API from the repository root.
- `uv run python -m py_compile <files>`: compile-check Python modules.

From repository root:

- `docker compose up --build`: start PostgreSQL, API, and web services together.

## Coding Style & Naming Conventions

Use TypeScript types for frontend contracts and Pydantic models for backend API contracts. Keep workflow steps as small named functions, such as `parse_intent`, `search_candidates`, and `generate_actions`.

Python files use `snake_case.py`; React components use `PascalCase.tsx`. Prefer explicit schemas over untyped dictionaries except for provider payloads and trace metadata. Keep mock adapters isolated from real API adapters.

## Testing Guidelines

Formal test suites are not yet scaffolded. Add backend tests under `services/api/tests` using `pytest`, named `test_<module>.py`. Add frontend tests under `apps/web/src/__tests__` once a runner is introduced.

At minimum, validate both MVP scenarios: family with a 5-year-old child and weight-loss dining needs, and four friends with mixed gender.

## Commit & Pull Request Guidelines

Existing commits use short imperative summaries, often in Chinese, such as "implement workflow" or "create scaffold." Keep commits focused and describe the completed change.

Pull requests should include purpose, affected modules, commands run, screenshots for UI changes, and notes on mock versus real API behavior. Do not include editor config, private agent config, or generated caches.

## Security & Configuration Tips

Use `.env.example` as the source of required variables. Do not commit `.env`, API keys, real user locations, booking credentials, or execution tokens. Initial POI, restaurant, and action execution providers are mock-only unless explicitly marked otherwise.
