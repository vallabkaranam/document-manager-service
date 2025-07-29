from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'dc8e889f1401'
down_revision: Union[str, None] = '9afa5b7807cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define enum values
embedding_status_enum = sa.Enum(
    'pending', 'processing', 'completed', 'failed', 'skipped',
    name='embeddingstatusenum'
)


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum type in DB
    embedding_status_enum.create(op.get_bind(), checkfirst=True)

    # Add new columns
    op.add_column('documents', sa.Column(
        'embedding_status', embedding_status_enum, nullable=False, server_default='pending'
    ))
    op.add_column('documents', sa.Column(
        'embedding_status_updated_at', sa.DateTime(timezone=True),
        nullable=False, server_default=sa.func.now()
    ))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns
    op.drop_column('documents', 'embedding_status_updated_at')
    op.drop_column('documents', 'embedding_status')

    # Drop enum type from DB
    embedding_status_enum.drop(op.get_bind(), checkfirst=True)