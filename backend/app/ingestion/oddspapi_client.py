import httpx

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://v5.oddspapi.io"

# LoL esports sport_id in OddsPapi
LOL_SPORT_ID = 18


class OddsPapiClient:
    """
    Async klient pro OddsPapi.io.
    Docs: https://oddspapi.io/en/docs
    Auth: apiKey header
    Flow:
      1. GET /en/events?sport_id=18  — get upcoming LoL events
      2. GET /en/odds?event_id={id}  — get bookmaker odds for each event
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OddsPapiClient":
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"apiKey": settings.ODDSPAPI_SECRET_KEY},
            timeout=15.0,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()

    async def get_lol_odds(self) -> list[dict]:
        """
        Fetches H2H (ML) odds for upcoming LoL esports matches.

        Returns a list of event dicts with the following structure:
          {
            "id": <int>,
            "home": "<team name>",
            "away": "<team name>",
            "date": "<ISO datetime>",
            "status": "<pending|live|finished>",
            "bookmakers": {
              "<BookmakerName>": [
                {
                  "name": "ML",
                  "odds": [{"home": "<decimal>", "away": "<decimal>"}],
                }
              ]
            }
          }
        """
        if self._client is None:
            raise RuntimeError("Client not initialized — use async context manager")

        # Step 1: get upcoming LoL events
        try:
            resp = await self._client.get(
                "/en/events",
                params={"sport_id": LOL_SPORT_ID, "status": "pending"},
            )
            resp.raise_for_status()
            events: list[dict] = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "oddspapi: failed to fetch events",
                status_code=exc.response.status_code,
                detail=exc.response.text[:200],
            )
            return []
        except Exception as exc:
            logger.warning("oddspapi: error fetching events", error=str(exc))
            return []

        if not events:
            return []

        # Step 2: enrich each event with bookmaker odds
        result: list[dict] = []
        for event in events:
            event_id = event.get("id")
            if not event_id:
                continue
            try:
                odds_resp = await self._client.get(
                    "/en/odds", params={"event_id": event_id}
                )
                odds_resp.raise_for_status()
                bookmakers = odds_resp.json()
                result.append({**event, "bookmakers": bookmakers})
            except httpx.HTTPStatusError as exc:
                logger.debug(
                    "oddspapi: failed to fetch odds for event",
                    event_id=event_id,
                    status_code=exc.response.status_code,
                )
                # Include event without odds so we still log coverage
                result.append(event)
            except Exception as exc:
                logger.debug(
                    "oddspapi: error fetching odds for event",
                    event_id=event_id,
                    error=str(exc),
                )
                result.append(event)

        return result
