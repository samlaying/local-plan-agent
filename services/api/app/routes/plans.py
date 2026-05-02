from fastapi import APIRouter

router = APIRouter(prefix="/api/plans", tags=["plans"])

# First-stage endpoints:
# POST /api/plans/preview
# GET /api/plans/{plan_id}
# POST /api/plans/{plan_id}/actions
