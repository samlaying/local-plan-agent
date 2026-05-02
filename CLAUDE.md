# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LocalPlan Agent is a local activity planning system that generates 4-6 hour executable plans from natural language input. The system uses a custom workflow state machine (designed for future LangGraph migration) and currently operates with mock data.

**Tech Stack**: Next.js + TypeScript frontend, FastAPI + Python backend, PostgreSQL database

**Current Status**: Early development - implementing MVP milestone with mock POI/restaurants and basic workflow.

## Development Commands

### Full Stack Development
```bash
# Start all services (PostgreSQL, API, Web)
docker-compose up

# Start services in detached mode
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f web

# Stop services
docker-compose down
```

### Frontend (Next.js)
```bash
cd apps/web
npm run dev          # Start development server on :3000
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run typecheck    # Run TypeScript type checking
```

### Backend (FastAPI)
```bash
# The API service runs via Docker Compose
# For local development with Python venv:
cd services/api
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ../../
uvicorn services.api.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database
```bash
# PostgreSQL runs on :5432 via Docker Compose
# Migrations run automatically on startup from data/migrations/
# To reset: docker-compose down -v && docker-compose up
```

## Architecture Overview

### Directory Structure
- `apps/web/` - Next.js frontend (App Router)
- `services/api/` - FastAPI HTTP layer (routes, schemas, repositories)
- `services/agent/` - Workflow state machine and agent nodes
- `services/domain/` - Business logic (POI, route, restaurant, itinerary)
- `services/tools/` - External API adapters (mock and real)
- `data/mock/` - JSON fixtures for POIs, restaurants, activities
- `packages/shared-types/` - Cross-stack type definitions
- `docs/` - Product, architecture, and API documentation

### Request Flow
```
Next.js page → apps/web/src/lib/api-client.ts → FastAPI /api/plans/preview
→ Application service → Agent workflow → Domain services → Mock JSON tools
→ PostgreSQL logs and saved plan
```

### Agent Workflow Nodes (Ordered)
The workflow is a custom state machine with explicit node schemas:
1. `intent_parser` - Parse natural language into structured intent
2. `constraint_normalizer` - Normalize constraints
3. `context_resolver` - Resolve user context
4. `candidate_search` - Search POI/restaurants
5. `route_feasibility` - Check route feasibility
6. `ranking` - Rank candidates
7. `itinerary_composer` - Compose plans
8. `validator` - Critique and validate plans
9. `execution_planner` - Generate executable actions

**Key Principle**: Every node accepts typed planning state, returns partial state patch, records tool calls, and avoids direct HTTP/database access unless explicitly owned.

### API Endpoints
- `GET /api/health` - Health check
- `POST /api/plans/preview` - Generate plans from natural language
- `GET /api/plans/{plan_id}` - Retrieve specific plan
- `POST /api/plans/{plan_id}/actions` - Generate executable actions
- `POST /api/actions/{action_id}/execute` - Execute an action

## Key Implementation Patterns

### State Machine Design
- Keep node input/output schemas explicit for LangGraph migration
- Use Pydantic models as single source of truth for types
- Generate or mirror TypeScript types in `packages/shared-types/`
- Workflow execution trace should be logged for debugging

### Domain Services
Business logic lives in `services/domain/`, not in HTTP routes or agent nodes:
- `poi/` - POI search and normalization
- `route/` - Route feasibility estimation
- `restaurant/` - Diet, child-friendly, queue fit analysis
- `itinerary/` - Plan composition and timeline management
- `execution/` - Action plan creation and execution

### Mock vs Real APIs
The system uses mock data during MVP:
- Set `USE_MOCK_POI=true` to use mock POI data
- Set `USE_MOCK_RESTAURANT=true` for mock restaurant details
- Set `USE_MOCK_EXECUTION=true` for mock booking/ticketing
- Real AMap (高德) API integration planned for later

### Scenarios
The system supports predefined user scenarios:
- `family_weight_loss_child5` - Family with weight-loss needs and 5-year-old child
- `friends_4_mixed_gender` - Four-person friends group (2 male, 2 female)

Each scenario has specific participant structures, diet requirements, and activity preferences.

## Data Model

### Core Entities
- `UserIntentSchema` - Parsed user request with constraints and preferences
- `POISchema` - Point of Interest with audience fit, business hours, queue info
- `PlanSchema` - Complete itinerary with steps, POIs, actions, scoring
- `ActionSchema` - Executable actions (navigation, reservation, queue, ticket, etc.)
- `ItineraryStepSchema` - Individual steps in a plan timeline

### Database Schema
- `planning_requests` - User planning requests
- `itinerary_plans` - Generated plans linked to requests
- `execution_actions` - Executable actions linked to plans

## Environment Configuration

Key environment variables (see `.env.example`):
- `APP_ENV` - development/test/production
- `DATABASE_URL` - PostgreSQL connection string
- `AGENT_BACKEND` - `custom_workflow` (current) or `langgraph` (future)
- `USE_MOCK_*` - Toggle mock vs real APIs
- `AMAP_API_KEY` - Real AMap API key (empty for MVP)

## First Milestone Implementation

The MVP implements:
1. Natural language request parsing with scenario detection
2. Mock data-based candidate search and ranking
3. Plan generation with 1 main + 2 alternative plans
4. Restaurant fit explanations (child-friendly, diet-friendly)
5. Execution action list generation
6. Real map navigation link as first real execution capability
7. PostgreSQL persistence for requests, plans, and actions

## Common Tasks

### Adding a New Workflow Node
1. Create node file in `services/agent/nodes/`
2. Define input/output schemas using Pydantic
3. Return partial state patch, not full state
4. Record tool calls for traceability
5. Add to workflow execution order in `services/agent/workflow/`

### Adding New Mock Data
1. Update relevant JSON in `data/mock/`
2. Update `MockPOIRepository` to include new data
3. Ensure POIs have required fields: `audience_fit`, `business_hours`, `queue`, `suitable_scenarios`

### Frontend Type Sync
1. Backend: Use Pydantic schemas in `services/api/app/schemas/`
2. Frontend: Mirror types in `apps/web/src/types/` or `packages/shared-types/`
3. Keep TypeScript types in sync with Pydantic models

### Running Tests
Currently no test suite exists. When adding tests:
- Backend: Use pytest in `services/api/`
- Frontend: Use Jest/React Testing Library in `apps/web/`
- Test workflow nodes independently before integration
