from fastapi import APIRouter, HTTPException

from app.ingestion.lol_esports_client import LoLEsportsClient
from app.prediction.live_engine import compute_live_win_prob
from app.schemas.live import LivePredictionOut, LiveSignals, LiveWindowOut

router = APIRouter()


@router.get("/{game_id}", response_model=LiveWindowOut)
async def get_live_prediction(game_id: str):
    client = LoLEsportsClient()
    async with client:
        window_data = await client.get_live_window(game_id)

    frames = window_data.get("frames", [])
    if not frames:
        raise HTTPException(status_code=404, detail="No live data available for this game_id")

    latest_frame = frames[-1]
    game_state = window_data.get("gameMetadata", {}).get("gameState", "unknown")

    prediction_data = compute_live_win_prob(latest_frame)
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
    )

    blue_participants = latest_frame.get("blueTeam", {}).get("participants", [])
    red_participants = latest_frame.get("redTeam", {}).get("participants", [])

    return LiveWindowOut(
        game_id=game_id,
        prediction=prediction,
        raw_participants_blue=blue_participants,
        raw_participants_red=red_participants,
        game_state=game_state,
    )
