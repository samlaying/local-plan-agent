"""PostgreSQL-backed repository for user_profiles."""
from __future__ import annotations

import json

from app.db import get_connection
from app.schemas.planning import UserProfileSchema


class UserProfileRepository:
    """Async repository for the user_profiles table.

    Uses a single connection per operation (no shared pool at this stage).
    All methods open and close a connection internally.
    """

    async def get(self, session_id: str) -> UserProfileSchema | None:
        """Return the profile for the given session_id, or None if not found."""
        async with await get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT session_id, preference_weights, selected_poi_ids, created_at, updated_at"
                    " FROM user_profiles WHERE session_id = %s",
                    (session_id,),
                )
                row = await cur.fetchone()
        if row is None:
            return None
        return UserProfileSchema(
            session_id=row["session_id"],
            preference_weights=row["preference_weights"] or {},
            selected_poi_ids=row["selected_poi_ids"] or [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def upsert(self, profile: UserProfileSchema) -> None:
        """Insert or update a user profile (ON CONFLICT DO UPDATE)."""
        async with await get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO user_profiles (session_id, preference_weights, selected_poi_ids)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE SET
                        preference_weights = EXCLUDED.preference_weights,
                        selected_poi_ids = EXCLUDED.selected_poi_ids,
                        updated_at = now()
                    """,
                    (
                        profile.session_id,
                        json.dumps(profile.preference_weights),
                        json.dumps(profile.selected_poi_ids),
                    ),
                )
            await conn.commit()

    async def update_weights(self, session_id: str, weight_delta: dict[str, float]) -> None:
        """Merge weight_delta into the existing preference_weights.

        Rules:
        - New tags are added directly.
        - Existing tags are averaged: new = (old + delta) / 2.
        - All values are clamped to [0.0, 1.0].

        If the profile does not exist yet it is created from the delta alone.
        """
        profile = await self.get(session_id)
        if profile is None:
            profile = UserProfileSchema(session_id=session_id)

        current = dict(profile.preference_weights)
        for tag, delta in weight_delta.items():
            if tag in current:
                merged = (current[tag] + delta) / 2
            else:
                merged = delta
            current[tag] = min(1.0, max(0.0, merged))

        await self.upsert(profile.model_copy(update={"preference_weights": current}))
