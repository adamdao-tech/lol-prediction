"""initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leagues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pandascore_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=True),
        sa.Column("image_url", sa.String(1024), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pandascore_id"),
    )
    op.create_index("ix_leagues_pandascore_id", "leagues", ["pandascore_id"])

    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pandascore_id", sa.String(100), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=True),
        sa.Column("tier", sa.String(50), nullable=True),
        sa.Column("begin_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("patch_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pandascore_id"),
    )
    op.create_index("ix_tournaments_pandascore_id", "tournaments", ["pandascore_id"])
    op.create_index("ix_tournaments_league_id", "tournaments", ["league_id"])

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pandascore_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=True),
        sa.Column("acronym", sa.String(50), nullable=True),
        sa.Column("image_url", sa.String(1024), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pandascore_id"),
    )
    op.create_index("ix_teams_pandascore_id", "teams", ["pandascore_id"])

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pandascore_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("image_url", sa.String(1024), nullable=True),
        sa.Column("nationality", sa.String(100), nullable=True),
        sa.Column("current_team_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["current_team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pandascore_id"),
    )
    op.create_index("ix_players_pandascore_id", "players", ["pandascore_id"])
    op.create_index("ix_players_current_team_id", "players", ["current_team_id"])

    op.create_table(
        "rosters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rosters_team_id", "rosters", ["team_id"])
    op.create_index("ix_rosters_player_id", "rosters", ["player_id"])

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pandascore_id", sa.String(100), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=True),
        sa.Column("team1_id", sa.Integer(), nullable=True),
        sa.Column("team2_id", sa.Integer(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("scheduled", "running", "finished", "cancelled", name="matchstatus"),
            nullable=False,
        ),
        sa.Column("number_of_games", sa.Integer(), nullable=True),
        sa.Column("winner_id", sa.Integer(), nullable=True),
        sa.Column("patch_version", sa.String(50), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.ForeignKeyConstraint(["team1_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["team2_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["winner_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pandascore_id"),
    )
    op.create_index("ix_matches_pandascore_id", "matches", ["pandascore_id"])
    op.create_index("ix_matches_tournament_id", "matches", ["tournament_id"])
    op.create_index("ix_matches_team1_id", "matches", ["team1_id"])
    op.create_index("ix_matches_team2_id", "matches", ["team2_id"])
    op.create_index("ix_matches_scheduled_at", "matches", ["scheduled_at"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column(
            "model_type",
            sa.Enum("winner", "kills", "duration", "combined", name="modeltype"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pandascore_id", sa.String(100), nullable=True),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("game_number", sa.Integer(), nullable=False),
        sa.Column("team1_id", sa.Integer(), nullable=True),
        sa.Column("team2_id", sa.Integer(), nullable=True),
        sa.Column("winner_id", sa.Integer(), nullable=True),
        sa.Column("blue_side_team_id", sa.Integer(), nullable=True),
        sa.Column("red_side_team_id", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("total_kills", sa.Integer(), nullable=True),
        sa.Column("team1_kills", sa.Integer(), nullable=True),
        sa.Column("team2_kills", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("not_started", "running", "finished", name="gamestatus"),
            nullable=False,
        ),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["team1_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["team2_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["winner_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["blue_side_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["red_side_team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pandascore_id"),
    )
    op.create_index("ix_games_match_id", "games", ["match_id"])
    op.create_index("ix_games_pandascore_id", "games", ["pandascore_id"])

    op.create_table(
        "drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("blue_bans", sa.JSON(), nullable=True),
        sa.Column("red_bans", sa.JSON(), nullable=True),
        sa.Column("blue_picks", sa.JSON(), nullable=True),
        sa.Column("red_picks", sa.JSON(), nullable=True),
        sa.Column(
            "source",
            sa.Enum("api", "manual", "ocr", name="draftsource"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drafts_game_id", "drafts", ["game_id"])

    op.create_table(
        "odds_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("bookmaker", sa.String(100), nullable=False),
        sa.Column("team1_odds", sa.Numeric(8, 4), nullable=False),
        sa.Column("team2_odds", sa.Numeric(8, 4), nullable=False),
        sa.Column("implied_prob_team1", sa.Numeric(8, 6), nullable=False),
        sa.Column("implied_prob_team2", sa.Numeric(8, 6), nullable=False),
        sa.Column("vig", sa.Numeric(8, 6), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source",
            sa.Enum("manual_csv", "api", name="oddssource"),
            nullable=False,
        ),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_odds_snapshots_match_id", "odds_snapshots", ["match_id"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("model_version_id", sa.Integer(), nullable=False),
        sa.Column("predicted_winner_id", sa.Integer(), nullable=True),
        sa.Column("win_prob_team1", sa.Numeric(8, 6), nullable=False),
        sa.Column("win_prob_team2", sa.Numeric(8, 6), nullable=False),
        sa.Column("predicted_total_kills", sa.Numeric(8, 2), nullable=True),
        sa.Column("predicted_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(8, 6), nullable=True),
        sa.Column("draft_adjusted", sa.Boolean(), nullable=False),
        sa.Column("features_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"]),
        sa.ForeignKeyConstraint(["predicted_winner_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_match_id", "predictions", ["match_id"])
    op.create_index("ix_predictions_model_version_id", "predictions", ["model_version_id"])

    op.create_table(
        "ingestion_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column(
            "status",
            sa.Enum("success", "partial", "failed", name="ingestionstatus"),
            nullable=False,
        ),
        sa.Column("records_fetched", sa.Integer(), nullable=False),
        sa.Column("records_inserted", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(2048), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_logs")
    op.drop_table("predictions")
    op.drop_table("odds_snapshots")
    op.drop_table("drafts")
    op.drop_table("games")
    op.drop_table("model_versions")
    op.drop_table("matches")
    op.drop_table("rosters")
    op.drop_table("players")
    op.drop_table("teams")
    op.drop_table("tournaments")
    op.drop_table("leagues")
    op.execute("DROP TYPE IF EXISTS matchstatus")
    op.execute("DROP TYPE IF EXISTS gamestatus")
    op.execute("DROP TYPE IF EXISTS draftsource")
    op.execute("DROP TYPE IF EXISTS oddssource")
    op.execute("DROP TYPE IF EXISTS modeltype")
    op.execute("DROP TYPE IF EXISTS ingestionstatus")
