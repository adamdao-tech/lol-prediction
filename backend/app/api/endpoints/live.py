from fastapi import APIRouter, HTTPException

from app.ingestion.lol_esports_client import LoLEsportsClient
from app.prediction.live_engine import compute_live_win_prob
from app.schemas.live import LivePredictionOut, LiveSignals, LiveWindowOut

router = APIRouter()

_MAX_PROB_HISTORY = 20


@router.get("/{game_id}", response_model=LiveWindowOut)
async def get_live_prediction(game_id: str):
    client = LoLEsportsClient()
    async with client:
        window_data = await client.get_live_window(game_id)

    frames = window_data.get("frames", [])
    if not frames:
        raise HTTPException(status_code=404, detail="No live data available for this game_id")

    game_state = window_data.get("gameMetadata", {}).get("gameState", "unknown")
    game_metadata = window_data.get("gameMetadata", {})

    # Build prob_history from all frames (max last N), enriching each with gameMetadata
    prob_history: list[float] = []
    for frame in frames[-_MAX_PROB_HISTORY:]:
        enriched = {**frame, "gameMetadata": game_metadata}
        frame_pred = compute_live_win_prob(enriched)
        prob_history.append(frame_pred["win_prob_blue"])

    latest_frame = frames[-1]
    enriched_latest = {**latest_frame, "gameMetadata": game_metadata}
    prediction_data = compute_live_win_prob(enriched_latest)
    signals = LiveSignals(**prediction_data["signals"])

    prediction = LivePredictionOut(
        game_id=game_id,
        win_prob_blue=prediction_data["win_prob_blue"],
        win_prob_red=prediction_data["win_prob_red"],
        signals=signals,
        blue_dragons=prediction_data["blue_dragons"],
        red_dragons=prediction_data["red_dragons"],
        blue_total_kills=prediction_data["blue_total_kills"],
        red_total_kills=prediction_data["red_total_kills"],
        blue_total_gold=prediction_data["blue_total_gold"],
        red_total_gold=prediction_data["red_total_gold"],
        game_state=game_state,
        frame_timestamp=latest_frame.get("rfc460Timestamp"),
        game_timer_seconds=prediction_data["game_timer_seconds"],
        game_timer=prediction_data["game_timer"],
        blue_towers=prediction_data["blue_towers"],
        red_towers=prediction_data["red_towers"],
        blue_barons=prediction_data["blue_barons"],
        red_barons=prediction_data["red_barons"],
    )

    blue_participants = latest_frame.get("blueTeam", {}).get("participants", [])
    red_participants = latest_frame.get("redTeam", {}).get("participants", [])

    return LiveWindowOut(
        game_id=game_id,
        prediction=prediction,
        raw_participants_blue=blue_participants,
        raw_participants_red=red_participants,
        game_state=game_state,
        prob_history=prob_history,
    )
