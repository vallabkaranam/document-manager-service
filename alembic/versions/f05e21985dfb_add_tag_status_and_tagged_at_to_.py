"""Add tag_status and tagged_at to documents

Revision ID: f05e21985dfb
Revises: 3a93748c3306
Create Date: 2025-07-08 14:43:14.559512
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f05e21985dfb'
down_revision: Union[str, None] = '3a93748c3306'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Explicitly create enum before using it
    tag_status_enum = sa.Enum('pending', 'processing', 'completed', 'failed', name='tagstatusenum')
    tag_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('documents', sa.Column(
        'tag_status',
        tag_status_enum,
        nullable=False,
        server_default='completed'  # Safe for existing rows
    ))
    op.add_column('documents', sa.Column(
        'tagged_at',
        sa.DateTime(timezone=True),
        nullable=True
    ))

    # Backfill tagged_at for existing completed rows
    op.execute("UPDATE documents SET tagged_at = now() WHERE tag_status = 'completed'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'tagged_at')
    op.drop_column('documents', 'tag_status')

    # Drop the enum type after dropping columns that depend on it
    sa.Enum(name='tagstatusenum').drop(op.get_bind(), checkfirst=True)