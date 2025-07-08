"""Switch tag_status_updated_at to use Python-level default instead of server-side default

Revision ID: f9b95301b762
Revises: 9e1e24c0242f
Create Date: 2025-07-08 15:53:24.216151

This migration does not introduce any schema changes at the database level.
It reflects a shift in the SQLAlchemy model where the `tag_status_updated_at` column
was changed to use a Python-level default (`default=func.now()`) instead of a
PostgreSQL server-side default (`server_default=func.now()`).

This change ensures that the timestamp is always set at the application level
rather than relying on implicit behavior from the database.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9b95301b762'
down_revision: Union[str, None] = '9e1e24c0242f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No schema changes needed for this upgrade."""
    pass


def downgrade() -> None:
    """No schema changes needed for this downgrade."""
    pass