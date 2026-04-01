"""add lol_esports_game_id to games

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("games", sa.Column("lol_esports_game_id", sa.String(100), nullable=True))
    op.create_index("ix_games_lol_esports_game_id", "games", ["lol_esports_game_id"])


def downgrade() -> None:
    op.drop_index("ix_games_lol_esports_game_id", table_name="games")
    op.drop_column("games", "lol_esports_game_id")
