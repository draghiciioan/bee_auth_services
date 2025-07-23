"""add login attempts email index

Revision ID: 5ba4be585eee
Revises: c8a56dc08d9d
Create Date: 2025-07-23 16:12:54.072739

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5ba4be585eee"
down_revision: Union[str, Sequence[str], None] = "c8a56dc08d9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_login_attempts_email_created_at",
        "login_attempts",
        ["email_attempted", "created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_login_attempts_email_created_at",
        table_name="login_attempts",
    )
