"""Add updated_at column and backfill from upload_time

Revision ID: 366a812a472c
Revises: f9b95301b762
Create Date: 2025-07-08 16:10:40.263283

This migration adds a new `updated_at` column to the `documents` table. It is a non-nullable
timestamp used for tracking the last modification time of a document record. Upon creation,
it is backfilled with the value of `upload_time` to maintain consistency for existing records.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '366a812a472c'
down_revision: Union[str, None] = 'f9b95301b762'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('documents', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # Backfill updated_at from upload_time
    op.execute("UPDATE documents SET updated_at = upload_time")

    # Now mark the column as non-nullable
    op.alter_column('documents', 'updated_at', nullable=False)

    op.alter_column(
        'documents',
        'upload_time',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text('now()')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'documents',
        'upload_time',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()')
    )
    op.drop_column('documents', 'updated_at')