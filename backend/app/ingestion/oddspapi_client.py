import httpx

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.oddspapi.io"

# LoL esports sportId in OddsPapi v4
LOL_SPORT_ID = 18

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
      1. GET /v4/tournaments?sportId=18&apiKey=...  — get all LoL tournament IDs
      2. GET /v4/participants?sportId=18&apiKey=...  — build participantId→name mapping
      3. GET /v4/odds-by-tournaments?tournamentIds=...&apiKey=...  — get fixtures+odds
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
        Fetches H2H (ML) odds for upcoming LoL esports matches.

        Returns a list of event dicts with the following structure:
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

        # Step 1: get all LoL tournaments to obtain tournament IDs
        try:
            resp = await self._client.get(
                "/v4/tournaments",
                params={"sportId": LOL_SPORT_ID, "apiKey": api_key},
            )
            resp.raise_for_status()
            tournaments: list[dict] = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "oddspapi: failed to fetch tournaments",
                status_code=exc.response.status_code,
                detail=exc.response.text[:200],
            )
            return []
        except Exception as exc:
            logger.warning("oddspapi: error fetching tournaments", error=str(exc))
            return []

        if not tournaments:
            logger.info("oddspapi: no LoL tournaments found")
            return []

        tournament_ids = [
            str(t["tournamentId"])
            for t in tournaments
            if isinstance(t.get("tournamentId"), int)
        ]
        if not tournament_ids:
            return []

        # Step 2: fetch participant id→name mapping
        participant_names: dict[int, str] = {}
        try:
            parts_resp = await self._client.get(
                "/v4/participants",
                params={"sportId": LOL_SPORT_ID, "apiKey": api_key},
            )
            parts_resp.raise_for_status()
            participants: list[dict] = parts_resp.json()
            for p in participants:
                pid = p.get("participantId")
                pname = p.get("participantName") or p.get("name", "")
                if isinstance(pid, int) and pname:
                    participant_names[pid] = pname
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "oddspapi: failed to fetch participants",
                status_code=exc.response.status_code,
                detail=exc.response.text[:200],
            )
            # Continue without names — IDs will be used as fallback
        except Exception as exc:
            logger.warning("oddspapi: error fetching participants", error=str(exc))

        # Step 3: get fixtures+odds for all tournaments
        try:
            odds_resp = await self._client.get(
                "/v4/odds-by-tournaments",
                params={
                    "tournamentIds": ",".join(tournament_ids),
                    "bookmaker": "pinnacle",
                    "apiKey": api_key,
                },
            )
            odds_resp.raise_for_status()
            fixtures: list[dict] = odds_resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "oddspapi: failed to fetch odds-by-tournaments",
                status_code=exc.response.status_code,
                detail=exc.response.text[:200],
            )
            return []
        except Exception as exc:
            logger.warning("oddspapi: error fetching odds-by-tournaments", error=str(exc))
            return []

        if not fixtures:
            return []

        result: list[dict] = []
        for fixture in fixtures:
            fixture_id = fixture.get("fixtureId")
            p1_id = fixture.get("participant1Id")
            p2_id = fixture.get("participant2Id")
            start_time = fixture.get("startTime")

            if not fixture_id or not start_time:
                continue

            home_name = participant_names.get(p1_id, str(p1_id)) if p1_id is not None else ""
            away_name = participant_names.get(p2_id, str(p2_id)) if p2_id is not None else ""

            # Parse bookmaker odds from v4 structure
            bookmakers_raw: dict = fixture.get("bookmakerOdds") or {}
            bookmakers_out: dict[str, list[dict]] = {}

            for bk_name, bk_data in bookmakers_raw.items():
                if not isinstance(bk_data, dict):
                    continue
                if not bk_data.get("bookmakerIsActive", True):
                    continue

                markets: dict = bk_data.get("markets") or {}
                moneyline = markets.get(_MARKET_MONEYLINE)
                if not moneyline:
                    continue

                outcomes: dict = moneyline.get("outcomes") or {}
                home_outcome = outcomes.get(_OUTCOME_HOME)
                away_outcome = outcomes.get(_OUTCOME_AWAY)

                if not home_outcome or not away_outcome:
                    continue

                try:
                    home_price = float(
                        home_outcome["players"]["0"]["price"]
                    )
                    away_price = float(
                        away_outcome["players"]["0"]["price"]
                    )
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
