# Engineering Scaffold

## Complete Directory Structure

```text
local-plan-agent/
  apps/
    web/
      src/
        app/
        components/
        features/planner/
        lib/
        types/
  services/
    api/
      app/
        routes/
        core/
        schemas/
        services/
        repositories/
        db/
    agent/
      workflow/
      prompts/
      nodes/
      state/
    domain/
      poi/
      route/
      restaurant/
      itinerary/
      execution/
    tools/
      amap/
      mock/
  data/
    mock/
    migrations/
  packages/
    shared-types/
    scoring/
  docs/
    architecture/
    product/
    api/
  infra/
    docker/
```

## Directory Responsibilities

- `apps/web`: Next.js user interface.
- `apps/web/src/app`: App Router pages and layouts.
- `apps/web/src/features/planner`: planning workflow UI, state and page-level components.
- `apps/web/src/lib`: API client, utility functions and client-side config.
- `services/api`: FastAPI service and HTTP boundary.
- `services/api/app/routes`: route handlers only.
- `services/api/app/services`: application services that coordinate domain and agent calls.
- `services/api/app/repositories`: persistence access.
- `services/agent`: custom workflow state machine and node orchestration.
- `services/domain`: business logic independent of HTTP and third-party APIs.
- `services/tools`: adapters for real APIs and Mock tools.
- `data/mock`: first-stage POI, restaurant, activity, queue and execution data.
- `data/migrations`: PostgreSQL schema migrations.
- `packages/shared-types`: shared schema definitions and generated TypeScript types.
- `packages/scoring`: reusable scoring constants and ranking rules.
- `docs`: product, API and architecture docs.
- `infra/docker`: Dockerfiles and runtime infra.

## Frontend and Backend Communication

The frontend talks only to FastAPI over HTTP JSON.

Initial API shape:

- `GET /api/health`
- `POST /api/plans/preview`
- `GET /api/plans/{plan_id}`
- `POST /api/plans/{plan_id}/actions`
- `POST /api/actions/{action_id}/execute`

Request flow:

```text
Next.js page
  -> apps/web/src/lib/api-client.ts
  -> FastAPI /api/plans/preview
  -> Application service
  -> Agent workflow
  -> Domain services
  -> Mock JSON tools
  -> PostgreSQL logs and saved plan
```

Use Pydantic models as the backend source of truth. Generate or manually mirror TypeScript types in `packages/shared-types` during MVP.

## Environment Variables

- `APP_ENV`: development, test, production.
- `API_HOST`, `API_PORT`: FastAPI bind address.
- `FRONTEND_URL`: allowed frontend origin.
- `NEXT_PUBLIC_API_BASE_URL`: browser-visible API base URL.
- `DATABASE_URL`: SQLAlchemy/PostgreSQL connection string.
- `MOCK_DATA_DIR`: path to JSON fixtures.
- `USE_MOCK_POI`: use Mock POI instead of real map provider.
- `USE_MOCK_RESTAURANT`: use Mock restaurant details, queue and reservation.
- `USE_MOCK_EXECUTION`: use Mock booking, ticketing and ordering actions.
- `AGENT_BACKEND`: `custom_workflow` now, `langgraph` later.
- `AGENT_MAX_STEPS`: workflow guardrail.
- `AGENT_ENABLE_VALIDATOR`: enable critic/validator node.
- `AMAP_API_KEY`: real GaoDe API key, empty during pure Mock MVP.
- `LOG_LEVEL`: runtime log level.
- `ENABLE_TOOL_CALL_LOG`: persist tool call logs.

## Docker Compose Design

Services:

- `postgres`: PostgreSQL 16, persisted with `postgres_data`.
- `api`: FastAPI service, mounts `services`, `data` and `packages` for local development.
- `web`: Next.js dev server, talks to `api`.

Ports:

- Frontend: `localhost:3000`
- Backend: `localhost:8000`
- PostgreSQL: `localhost:5432`

## First-Stage Files To Implement

Backend:

- `services/api/app/routes/plans.py`
- `services/api/app/schemas/planning.py`
- `services/api/app/services/planning_service.py`
- `services/agent/workflow/engine.py`
- `services/agent/state/planning_state.py`
- `services/agent/nodes/intent_parser.py`
- `services/agent/nodes/candidate_search.py`
- `services/agent/nodes/ranking.py`
- `services/agent/nodes/itinerary_composer.py`
- `services/agent/nodes/validator.py`
- `services/agent/nodes/execution_planner.py`
- `services/domain/poi/mock_poi_service.py`
- `services/domain/restaurant/fit_service.py`
- `services/domain/itinerary/itinerary_service.py`
- `services/tools/mock/json_loader.py`

Frontend:

- `apps/web/src/app/page.tsx`
- `apps/web/src/features/planner/PlannerShell.tsx`
- `apps/web/src/features/planner/PromptInput.tsx`
- `apps/web/src/features/planner/ParsedRequestPanel.tsx`
- `apps/web/src/features/planner/PlanCard.tsx`
- `apps/web/src/features/planner/Timeline.tsx`
- `apps/web/src/features/planner/ActionList.tsx`
- `apps/web/src/lib/api-client.ts`
- `apps/web/src/types/planning.ts`

Data:

- `data/mock/activities.json`
- `data/mock/restaurants.json`
- `data/mock/pois.json`
- `data/mock/routes.json`
- `data/mock/execution_status.json`

Docs:

- `docs/api/plans.md`
- `docs/architecture/workflow.md`
- `docs/product/mvp-scope.md`
