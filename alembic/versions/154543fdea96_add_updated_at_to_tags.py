"""add updated_at to tags

Revision ID: 154543fdea96
Revises: 366a812a472c
Create Date: 2025-07-09 22:26:45.463891

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import DateTime

# revision identifiers, used by Alembic.
revision: str = '154543fdea96'
down_revision: Union[str, None] = '366a812a472c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add updated_at as nullable=True (backfill safety)
    op.add_column('tags', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # Step 2: Backfill updated_at = created_at
    op.execute("UPDATE tags SET updated_at = created_at")

    # Step 3: Alter updated_at to nullable=False
    op.alter_column('tags', 'updated_at', nullable=False)

    # Step 4: Drop server_default from created_at (matches model's use of ORM-level default)
    op.alter_column('tags', 'created_at',
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=None
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Step 1: Restore server default to created_at (optional, if needed)
    op.alter_column('tags', 'created_at',
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=sa.text('now()')
    )

    # Step 2: Drop updated_at column
    op.drop_column('tags', 'updated_at')