import json
from pathlib import Path

from app.core.config import settings
from app.schemas import POISchema


class MockPOIRepository:
    """Loads first-stage POI data from local JSON files."""

    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = self._resolve_data_dir(data_dir or settings.mock_data_dir)

    def list_activities(self) -> list[POISchema]:
        return self._load_pois("activities.json")

    def list_restaurants(self) -> list[POISchema]:
        return self._load_pois("restaurants.json")

    def list_all(self) -> list[POISchema]:
        return [*self.list_activities(), *self.list_restaurants()]

    def _load_pois(self, filename: str) -> list[POISchema]:
        path = self.data_dir / filename
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return [POISchema.model_validate(item) for item in payload]

    @staticmethod
    def _resolve_data_dir(data_dir: str) -> Path:
        path = Path(data_dir)
        if path.is_absolute():
            return path

        project_root = Path(__file__).resolve().parents[4]
        return project_root / path
