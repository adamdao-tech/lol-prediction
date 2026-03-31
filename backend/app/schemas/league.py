from datetime import datetime
from pydantic import BaseModel, ConfigDict


class LeagueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pandascore_id: str
    name: str
    slug: str | None = None
    image_url: str | None = None
    region: str | None = None
    created_at: datetime
    updated_at: datetime
