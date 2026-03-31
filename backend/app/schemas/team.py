from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pandascore_id: str
    name: str
    slug: str | None = None
    acronym: str | None = None
    image_url: str | None = None
    region: str | None = None


class TeamDetail(TeamOut):
    created_at: datetime
    updated_at: datetime
