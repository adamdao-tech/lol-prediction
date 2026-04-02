import httpx

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.oddspapi.io"

# LoL esports sportId in OddsPapi v4
LOL_SPORT_ID = 18

# Only fetch major LoL leagues — stays within the 5 tournament ID limit
# LCS=2450, LEC=2452, LCK=2454, MSI=2527, Worlds=2549
LOL_MAJOR_TOURNAMENT_IDS = [2450, 2452, 2454, 2527, 2549]


class OddsPapiClient:
    """
    Async klient pro OddsPapi.io v4.
    Auth: apiKey as query parameter on every request.
    Flow:
      1. GET /v4/participants?sportId=18 — build id->name mapping
         Response format: {"240608": "kt Rolster", "240616": "T1", ...}
      2. GET /v4/odds-by-tournaments?tournamentIds=... — get fixtures+odds (max 5 IDs)
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

    async def _fetch_participant_names(self, api_key: str) -> dict[int, str]:
        """Fetch participantId -> name mapping for LoL.
        API returns a flat dict: {"<str_id>": "<team_name>", ...}
        """
        assert self._client is not None
        try:
            resp = await self._client.get(
                "/v4/participants",
                params={"sportId": LOL_SPORT_ID, "apiKey": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

            names: dict[int, str] = {}

            if isinstance(data, dict):
                # Flat format: {"240608": "kt Rolster", "240616": "T1", ...}
                for str_id, name in data.items():
                    if isinstance(name, str) and name:
                        try:
                            names[int(str_id)] = name
                        except (ValueError, TypeError):
                            pass
            elif isinstance(data, list):
                # Fallback: list of dicts format
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    pid = item.get("participantId") or item.get("id")
                    pname = (
                        item.get("participantName")
                        or item.get("name")
                        or item.get("teamName")
                        or ""
                    )
                    if isinstance(pid, int) and pname:
                        names[pid] = pname

            logger.info("oddspapi: fetched participant names", count=len(names))
            return names
        except Exception as exc:
            logger.warning("oddspapi: failed to fetch participants", error=str(exc))
            return {}

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
                {"name": "ML", "odds": [{"home": <decimal>, "away": <decimal>}]}  
              ]
            }
          }
        """
        if self._client is None:
            raise RuntimeError("Client not initialized - use async context manager")

        api_key = settings.ODDSPAPI_SECRET_KEY
        tournament_ids_str = ",".join(str(t) for t in LOL_MAJOR_TOURNAMENT_IDS)

        # Step 1: fetch participant id->name mapping (best-effort)
        participant_names = await self._fetch_participant_names(api_key)

        # Step 2: fetch fixtures + odds
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

            p1_id = fixture.get("participant1Id")
            p2_id = fixture.get("participant2Id")

            # Resolve names: fixture field > participants lookup > raw ID string
            home_name = (
                fixture.get("participant1Name")
                or (participant_names.get(p1_id) if isinstance(p1_id, int) else None)
                or str(p1_id or "")
            )
            away_name = (
                fixture.get("participant2Name")
                or (participant_names.get(p2_id) if isinstance(p2_id, int) else None)
                or str(p2_id or "")
            )

            # Parse bookmaker odds - scan all markets, find moneyline by bookmakerOutcomeId "home"/"away"
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

                home_price: float | None = None
                away_price: float | None = None

                for market_data in markets.values():
                    if not isinstance(market_data, dict):
                        continue
                    outcomes = market_data.get("outcomes") or {}
                    if not isinstance(outcomes, dict):
                        continue

                    for outcome_data in outcomes.values():
                        if not isinstance(outcome_data, dict):
                            continue
                        players = outcome_data.get("players") or {}
                        player = players.get("0") if isinstance(players, dict) else None
                        if not isinstance(player, dict):
                            continue
                        outcome_side = player.get("bookmakerOutcomeId", "")
                        price = player.get("price")
                        if price is None:
                            continue
                        try:
                            price_f = float(price)
                        except (ValueError, TypeError):
                            continue
                        if outcome_side == "home":
                            home_price = price_f
                        elif outcome_side == "away":
                            away_price = price_f

                    if home_price is not None and away_price is not None:
                        break

                if home_price is not None and away_price is not None:
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