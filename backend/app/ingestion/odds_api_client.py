import httpx

from app.config import settings

BASE_URL = "https://api.the-odds-api.com/v4"


class OddsApiClient:
    """
    Async klient pro The Odds API.
    Docs: https://the-odds-api.com/lol-api/
    Endpoint: GET /v4/sports/esports_lol/odds
    Params: apiKey, regions=eu, markets=h2h, oddsFormat=decimal
    """

    async def __aenter__(self) -> "OddsApiClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def get_lol_odds(self) -> list[dict]:
        """
        Fetches H2H odds for LoL esports matches.
        Returns list of events with bookmaker H2H odds.
        """
        params = {
            "apiKey": settings.THE_ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/sports/esports_lol/odds", params=params)
            resp.raise_for_status()
            return resp.json()
