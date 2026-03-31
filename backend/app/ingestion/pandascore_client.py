import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.pandascore.co"
REQUEST_INTERVAL = 0.5  # seconds between requests


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))


class PandaScoreClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._last_request_at: float = 0.0

    async def __aenter__(self) -> "PandaScoreClient":
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {settings.PANDASCORE_API_KEY}"},
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def _rate_limit(self) -> None:
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_at
        if elapsed < REQUEST_INTERVAL:
            await asyncio.sleep(REQUEST_INTERVAL - elapsed)
        self._last_request_at = asyncio.get_event_loop().time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if self._client is None:
            raise RuntimeError("Client not initialized — use async context manager")
        await self._rate_limit()
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_lol_leagues(self) -> list[dict]:
        return await self._get("/lol/leagues", params={"per_page": 100})

    async def get_lol_upcoming_matches(self, days_ahead: int = 7) -> list[dict]:
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days_ahead)
        range_value = f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')},{future.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        return await self._get(
            "/lol/matches/upcoming",
            params={"per_page": 100, "range[scheduled_at]": range_value},
        )

    async def get_lol_past_matches(self, page: int = 1, per_page: int = 100) -> list[dict]:
        return await self._get("/lol/matches/past", params={"per_page": per_page, "page": page})

    async def get_lol_match(self, match_id: str | int) -> dict:
        return await self._get(f"/lol/matches/{match_id}")

    async def get_lol_teams(self, page: int = 1, per_page: int = 100) -> list[dict]:
        return await self._get("/lol/teams", params={"per_page": per_page, "page": page})

    async def ping(self) -> bool:
        try:
            await self._get("/lol/leagues", params={"per_page": 1})
            return True
        except Exception as exc:
            logger.warning("PandaScore ping failed", error=str(exc))
            return False


pandascore_client = PandaScoreClient()
