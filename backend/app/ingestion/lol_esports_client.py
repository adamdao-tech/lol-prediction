from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from app.utils.logging import get_logger

logger = get_logger(__name__)

LOL_ESPORTS_API_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
LOL_ESPORTS_BASE = "https://esports-api.lolesports.com/persisted/gw"
LIVESTATS_BASE = "https://feed.lolesports.com/livestats/v1"


class LiveDataNotAvailable(Exception):
    """Raised when the LoL Esports livestats API returns no usable data (404/400)."""
    pass


class LoLEsportsClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "LoLEsportsClient":
        self._client = httpx.AsyncClient(
            headers={"x-api-key": LOL_ESPORTS_API_KEY},
            timeout=15.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _starting_time(self) -> str:
        dt = datetime.now(timezone.utc) - timedelta(seconds=30)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    async def get_live_window(self, game_id: str) -> dict:
        assert self._client is not None, "Client not initialised — use async with"
        url = f"{LIVESTATS_BASE}/window/{game_id}"
        params = {"startingTime": self._starting_time()}
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LiveDataNotAvailable(
                f"No live data for game_id={game_id} (HTTP {exc.response.status_code})"
            ) from exc
        return response.json()

    async def get_live_details(self, game_id: str) -> dict:
        assert self._client is not None, "Client not initialised — use async with"
        url = f"{LIVESTATS_BASE}/details/{game_id}"
        params = {"startingTime": self._starting_time()}
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LiveDataNotAvailable(
                f"No live details for game_id={game_id} (HTTP {exc.response.status_code})"
            ) from exc
        return response.json()

    async def get_schedule(self, league_id: str | None = None) -> dict:
        assert self._client is not None, "Client not initialised — use async with"
        url = f"{LOL_ESPORTS_BASE}/getSchedule"
        params: dict[str, str] = {"hl": "en-US"}
        if league_id is not None:
            params["leagueId"] = league_id
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_event_details(self, event_id: str) -> dict:
        assert self._client is not None, "Client not initialised — use async with"
        url = f"{LOL_ESPORTS_BASE}/getEventDetails"
        params = {"hl": "en-US", "id": event_id}
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()
