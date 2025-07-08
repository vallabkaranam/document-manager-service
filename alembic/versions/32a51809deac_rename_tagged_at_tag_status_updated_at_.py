"""Rename tagged_at → tag_status_updated_at and add 'skipped' to tag status enum

Revision ID: 32a51809deac
Revises: f05e21985dfb
Create Date: 2025-07-08 15:24:32.708529
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '32a51809deac'
down_revision: Union[str, None] = 'f05e21985dfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_enum = sa.Enum('pending', 'processing', 'completed', 'failed', name='tagstatusenum')
new_enum = sa.Enum('pending', 'processing', 'completed', 'failed', 'skipped', name='tagstatusenum')


def upgrade() -> None:
    # Add new value to existing ENUM type in Postgres
    op.execute("ALTER TYPE tagstatusenum ADD VALUE IF NOT EXISTS 'skipped'")

    # Rename column
    op.add_column('documents', sa.Column('tag_status_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_column('documents', 'tagged_at')


def downgrade() -> None:
    # Rename column back
    op.add_column('documents', sa.Column('tagged_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_column('documents', 'tag_status_updated_at')

    # Optional: You cannot easily remove a value from Postgres enums, so note this:
    # You may choose to leave the 'skipped' value in place.