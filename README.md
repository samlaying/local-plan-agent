# LocalPlan Agent

本地短时活动规划与执行 Agent。用户输入一句自然语言，系统生成 4-6 小时可执行方案，并在确认后生成导航、预约、取号、购票、消息、日历等动作。

## Tech Stack

- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI + Python
- Agent orchestration: custom Workflow state machine, replaceable by LangGraph later
- Database: PostgreSQL
- Initial data: Mock JSON for POI, restaurants, activities and execution state

## Structure

```text
apps/web                  Next.js frontend
services/api              FastAPI HTTP API
services/agent            Workflow state machine and agent nodes
services/domain           Domain services for POI, route, restaurant, itinerary, execution
services/tools            External API adapters and mock tools
data/mock                 Mock POI, restaurant, activity and queue data
data/migrations           PostgreSQL migrations
packages/shared-types     Cross-stack schemas and generated types
packages/scoring          Shared scoring rules
docs                      Product, architecture and API docs
infra/docker              Dockerfiles and runtime infra files
```

## First Milestone

The first milestone should implement:

1. `POST /api/plans/preview`: parse request and return 1 main plan + 2 alternatives from Mock JSON.
2. `POST /api/plans/{plan_id}/actions`: generate executable action list.
3. Frontend planner page: input, parsed constraints, plan cards and action list.
4. Workflow nodes: intent parsing, mock candidate search, scoring, itinerary composition, validation, execution planning.
