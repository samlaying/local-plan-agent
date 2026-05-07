from __future__ import annotations

import logging

from agent.nodes.base import BaseNode
from agent.state.types import PlanningState, TraceEvent
from app.repositories.user_profile_repository import UserProfileRepository
from app.schemas.planning import UserProfileSchema

logger = logging.getLogger(__name__)

_TAG_INCREMENT = 0.1


class FeedbackNode(BaseNode):
    """Records user selection and updates preference weights after plan confirmation.

    This node is fire-and-forget: the orchestrator calls it via
    ``asyncio.create_task()`` and does not await the result.

    Errors are caught and logged as warnings only — the node never
    propagates exceptions into the main workflow.
    """

    def __init__(self, repository: UserProfileRepository) -> None:
        self._repo = repository

    async def run(self, state: PlanningState) -> PlanningState:
        state.trace.append(
            TraceEvent(agent="feedback_node", status="running", message="记录用户选择中...")
        )

        try:
            if state.confirmed_plan is None:
                logger.warning("FeedbackNode: confirmed_plan is None, skipping feedback.")
                state.trace.append(
                    TraceEvent(
                        agent="feedback_node",
                        status="done",
                        message="跳过：无 confirmed_plan",
                    )
                )
                return state

            plan = state.confirmed_plan
            session_id = state.session_id

            poi_ids = [poi.id for poi in plan.pois]

            weight_delta: dict[str, float] = {}
            for poi in plan.pois:
                for tag in poi.tags:
                    weight_delta[tag] = round(weight_delta.get(tag, 0.0) + _TAG_INCREMENT, 4)

            self._repo.update_weights(session_id, weight_delta)

            # upsert merges selected_poi_ids (deduplicates) without touching weights,
            # since update_weights already handled the weight increment above.
            self._repo.upsert(
                UserProfileSchema(
                    session_id=session_id,
                    selected_poi_ids=poi_ids,
                )
            )

            state.trace.append(
                TraceEvent(
                    agent="feedback_node",
                    status="done",
                    message=f"偏好记录完成：{len(poi_ids)} 个 POI，{len(weight_delta)} 个 tag 权重更新",
                )
            )
            logger.debug(
                "FeedbackNode done: session=%s poi_ids=%s weight_delta=%s",
                session_id,
                poi_ids,
                weight_delta,
            )

        except Exception:
            logger.warning("FeedbackNode: error updating user profile, suppressing.", exc_info=True)

        return state
