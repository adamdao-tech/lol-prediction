import httpx

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.oddspapi.io"

# LoL esports sportId in OddsPapi v4
LOL_SPORT_ID = 18

# Only fetch major LoL leagues — stays within the 5 tournament ID limit
# LCS=2450, LEC=2452, LCK=2454, LPL (if available), MSI=2527
LOL_MAJOR_TOURNAMENT_IDS = [2450, 2452, 2454, 2527, 2549]

# Market IDs in OddsPapi v4
_MARKET_MONEYLINE = "101"
_OUTCOME_HOME = "101"
_OUTCOME_AWAY = "103"


class OddsPapiClient:
    """
    Async klient pro OddsPapi.io v4.
    Docs: https://api.oddspapi.io
    Auth: apiKey as query parameter on every request
    Flow:
      1. GET /v4/odds-by-tournaments?tournamentIds=2450,2452,2454,2527,2549&apiKey=...
         — get fixtures+odds for major LoL tournaments (max 5 IDs)
      Note: participant names are resolved from fixture data directly (participant1Name/participant2Name)
            or fetched separately if needed.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OddsPapiClient":
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=15.0,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()

    async def get_lol_odds(self) -> list[dict]:
        """
        Fetches H2H (ML) odds for upcoming LoL esports matches from major leagues.

        Returns a list of event dicts compatible with sync_odds.py:
          {
            "id": "<fixtureId>",
            "home": "<team name>",
            "away": "<team name>",
            "date": "<ISO datetime>",
            "status": "pending",
            "bookmakers": {
              "<BookmakerName>": [
                {
                  "name": "ML",
                  "odds": [{"home": <decimal>, "away": <decimal>}],
                }
              ]
            }
          }
        """
        if self._client is None:
            raise RuntimeError("Client not initialized — use async context manager")

        api_key = settings.ODDSPAPI_SECRET_KEY
        tournament_ids_str = ",".join(str(t) for t in LOL_MAJOR_TOURNAMENT_IDS)

        # Fetch fixtures + odds for major LoL tournaments (max 5 IDs per API limit)
        try:
            odds_resp = await self._client.get(
                "/v4/odds-by-tournaments",
                params={
                    "tournamentIds": tournament_ids_str,
                    "bookmaker": "pinnacle",
                    "apiKey": api_key,
                },
            )
            odds_resp.raise_for_status()
            fixtures: list = odds_resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "oddspapi: failed to fetch odds-by-tournaments",
                status_code=exc.response.status_code,
                detail=exc.response.text[:300],
            )
            return []
        except Exception as exc:
            logger.warning("oddspapi: error fetching odds-by-tournaments", error=str(exc))
            return []

        if not fixtures or not isinstance(fixtures, list):
            return []

        result: list[dict] = []
        for fixture in fixtures:
            if not isinstance(fixture, dict):
                continue

            fixture_id = fixture.get("fixtureId")
            start_time = fixture.get("startTime")

            if not fixture_id or not start_time:
                continue

            # Try to get team names directly from fixture (some API versions include them)
            home_name = (
                fixture.get("participant1Name")
                or fixture.get("home")
                or str(fixture.get("participant1Id", ""))
            )
            away_name = (
                fixture.get("participant2Name")
                or fixture.get("away")
                or str(fixture.get("participant2Id", ""))
            )

            # Parse bookmaker odds from v4 structure
            bookmakers_raw = fixture.get("bookmakerOdds") or {}
            if not isinstance(bookmakers_raw, dict):
                continue

            bookmakers_out: dict[str, list[dict]] = {}

            for bk_name, bk_data in bookmakers_raw.items():
                if not isinstance(bk_data, dict):
                    continue
                if not bk_data.get("bookmakerIsActive", True):
                    continue

                markets = bk_data.get("markets") or {}
                if not isinstance(markets, dict):
                    continue

                moneyline = markets.get(_MARKET_MONEYLINE)
                if not moneyline or not isinstance(moneyline, dict):
                    continue

                outcomes = moneyline.get("outcomes") or {}
                if not isinstance(outcomes, dict):
                    continue

                home_outcome = outcomes.get(_OUTCOME_HOME)
                away_outcome = outcomes.get(_OUTCOME_AWAY)

                if not home_outcome or not away_outcome:
                    continue

                try:
                    home_price = float(home_outcome["players"]["0"]["price"])
                    away_price = float(away_outcome["players"]["0"]["price"])
                except (KeyError, TypeError, ValueError):
                    continue

                bookmakers_out[bk_name] = [
                    {
                        "name": "ML",
                        "odds": [{"home": home_price, "away": away_price}],
                    }
                ]

            result.append(
                {
                    "id": fixture_id,
                    "home": home_name,
                    "away": away_name,
                    "date": start_time,
                    "status": "pending",
                    "bookmakers": bookmakers_out,
                }
            )

        return result
