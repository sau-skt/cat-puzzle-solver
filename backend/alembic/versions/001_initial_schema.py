"""Initial schema for users, sessions, and puzzles.

Revision ID: 001_initial
Revises:
Create Date: 2026-11-08
"""

from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_token_hash", sa.String(length=64), nullable=True),
        sa.Column("verification_expires", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("remember_me", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("request_ip", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)

    op.create_table(
        "puzzles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("original_image_path", sa.String(length=500), nullable=False),
        sa.Column("normalized_image_path", sa.String(length=500), nullable=True),
        sa.Column("rows", sa.Integer(), nullable=True),
        sa.Column("cols", sa.Integer(), nullable=True),
        sa.Column("rules_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detection_confidence", sa.Float(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("detection_notes", sa.Text(), nullable=True),
        sa.Column("solver_status", sa.String(length=32), nullable=True),
        sa.Column("solution_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("solutions_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("processing_time_ms", sa.Float(), nullable=True),
        sa.Column("solver_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_puzzles_user_id", "puzzles", ["user_id"])
    op.create_index("ix_puzzles_status", "puzzles", ["status"])

    op.create_table(
        "puzzle_cells",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("puzzle_id", sa.String(length=36), sa.ForeignKey("puzzles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row", sa.Integer(), nullable=False),
        sa.Column("col", sa.Integer(), nullable=False),
        sa.Column("color_id", sa.Integer(), nullable=True),
        sa.Column("color_label", sa.String(length=32), nullable=True),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_cat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bbox_x", sa.Integer(), nullable=True),
        sa.Column("bbox_y", sa.Integer(), nullable=True),
        sa.Column("bbox_w", sa.Integer(), nullable=True),
        sa.Column("bbox_h", sa.Integer(), nullable=True),
        sa.UniqueConstraint("puzzle_id", "row", "col", name="uq_puzzle_cell_position"),
    )
    op.create_index("ix_puzzle_cells_puzzle_id", "puzzle_cells", ["puzzle_id"])

    op.create_table(
        "puzzle_solutions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("puzzle_id", sa.String(length=36), sa.ForeignKey("puzzles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("solution_index", sa.Integer(), nullable=False),
        sa.Column("execution_time_ms", sa.Float(), nullable=False),
        sa.Column("validation_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("validation_errors", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("puzzle_id", "solution_index", name="uq_puzzle_solution_index"),
    )
    op.create_index("ix_puzzle_solutions_puzzle_id", "puzzle_solutions", ["puzzle_id"])

    op.create_table(
        "solution_positions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("solution_id", sa.String(length=36), sa.ForeignKey("puzzle_solutions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cat_index", sa.Integer(), nullable=False),
        sa.Column("row", sa.Integer(), nullable=False),
        sa.Column("col", sa.Integer(), nullable=False),
        sa.Column("color_id", sa.Integer(), nullable=True),
        sa.Column("color_label", sa.String(length=32), nullable=True),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.UniqueConstraint("solution_id", "cat_index", name="uq_solution_cat_index"),
    )
    op.create_index("ix_solution_positions_solution_id", "solution_positions", ["solution_id"])


def downgrade() -> None:
    op.drop_table("solution_positions")
    op.drop_table("puzzle_solutions")
    op.drop_table("puzzle_cells")
    op.drop_table("puzzles")
    op.drop_table("password_reset_tokens")
    op.drop_table("user_sessions")
    op.drop_table("users")
