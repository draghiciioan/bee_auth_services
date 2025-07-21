"""create auth tables

Revision ID: 1c572a13dc24
Revises:
Create Date: 2025-07-21 15:45:34.722766
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from models.user import UserRole


# revision identifiers, used by Alembic.
revision: str = '1c572a13dc24'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    role_enum = postgresql.ENUM(*[r.value for r in UserRole], name="userrole")
    role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "email",
            sa.String(),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String()),
        sa.Column("phone_number", sa.String()),
        sa.Column(
            "role",
            role_enum,
            nullable=False,
            server_default=UserRole.CLIENT.value,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_social",
            sa.Boolean(),
            server_default=sa.text("false"),
        ),
        sa.Column("provider", sa.String()),
        sa.Column("social_id", sa.String()),
        sa.Column("avatar_url", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "login_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(), nullable=False),
        sa.Column("user_agent", sa.String()),
        sa.Column(
            "success",
            sa.Boolean(),
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_login_attempts_user_id_created_at",
        "login_attempts",
        ["user_id", "created_at"],
    )

    op.create_table(
        "email_verification",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "token",
            sa.String(),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_email_verification_user_id",
        "email_verification",
        ["user_id"],
    )

    op.create_table(
        "twofa_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "token",
            sa.String(),
            nullable=False,
            index=True,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "is_used",
            sa.Boolean(),
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_twofa_tokens_user_id",
        "twofa_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_twofa_tokens_token",
        "twofa_tokens",
        ["token"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_twofa_tokens_token", table_name="twofa_tokens")
    op.drop_index("ix_twofa_tokens_user_id", table_name="twofa_tokens")
    op.drop_table("twofa_tokens")

    op.drop_index(
        "ix_email_verification_user_id",
        table_name="email_verification",
    )
    op.drop_table("email_verification")

    op.drop_index(
        "ix_login_attempts_user_id_created_at",
        table_name="login_attempts",
    )
    op.drop_table("login_attempts")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
