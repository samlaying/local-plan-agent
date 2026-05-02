from fastapi import APIRouter

from app.services.activity_workflow import (
    PlanPreviewRequest,
    WorkflowResult,
    run_activity_workflow,
)

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.post("/preview", response_model=WorkflowResult)
def preview_plans(request: PlanPreviewRequest) -> WorkflowResult:
    return run_activity_workflow(raw_text=request.query, location=request.location)
