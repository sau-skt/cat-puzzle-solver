"""Store a phone number with its country calling code.

Revision ID: 002_user_phone
Revises: 001_initial
Create Date: 2026-11-08
"""

from alembic import op
import sqlalchemy as sa

revision = "002_user_phone"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("country_iso", sa.String(length=2), nullable=True))
    op.add_column("users", sa.Column("dial_code", sa.String(length=8), nullable=True))
    op.add_column("users", sa.Column("phone_number", sa.String(length=15), nullable=True))
    op.add_column("users", sa.Column("phone_e164", sa.String(length=16), nullable=True))
    op.create_index("ix_users_phone_e164", "users", ["phone_e164"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_phone_e164", table_name="users")
    op.drop_column("users", "phone_e164")
    op.drop_column("users", "phone_number")
    op.drop_column("users", "dial_code")
    op.drop_column("users", "country_iso")
