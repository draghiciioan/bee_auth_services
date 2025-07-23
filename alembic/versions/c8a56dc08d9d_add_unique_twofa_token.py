"""add unique constraint to twofa token

Revision ID: c8a56dc08d9d
Revises: 35b6c0f1d431
Create Date: 2025-07-22 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8a56dc08d9d"
down_revision: Union[str, Sequence[str], None] = "35b6c0f1d431"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint to twofa_tokens.token."""
    op.create_unique_constraint("uq_twofa_tokens_token", "twofa_tokens", ["token"])


def downgrade() -> None:
    """Remove unique constraint from twofa_tokens.token."""
    op.drop_constraint("uq_twofa_tokens_token", "twofa_tokens", type_="unique")
