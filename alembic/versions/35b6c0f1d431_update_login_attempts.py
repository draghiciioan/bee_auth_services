"""make user_id nullable and add email_attempted

Revision ID: 35b6c0f1d431
Revises: 1c572a13dc24
Create Date: 2025-07-21 18:38:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '35b6c0f1d431'
down_revision: Union[str, Sequence[str], None] = '1c572a13dc24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply schema changes."""
    op.add_column('login_attempts', sa.Column('email_attempted', sa.String(length=255), nullable=False))
    op.alter_column('login_attempts', 'user_id', nullable=True)


def downgrade() -> None:
    """Revert schema changes."""
    op.alter_column('login_attempts', 'user_id', nullable=False)
    op.drop_column('login_attempts', 'email_attempted')
