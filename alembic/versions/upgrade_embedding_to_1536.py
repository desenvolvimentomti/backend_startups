"""Upgrade embedding vector to 1536 dimensions for OpenAI

Revision ID: upgrade_embedding_1536
Revises: 2c27dfefd871
Create Date: 2025-01-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'upgrade_embedding_1536'
down_revision: Union[str, Sequence[str], None] = '2c27dfefd871'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade embedding_vector from 1024 to 1536 dimensions."""
    # Drop the old column with 1024 dimensions
    op.drop_column('startups', 'embedding_vector')

    # Add new column with 1536 dimensions
    op.add_column('startups', sa.Column('embedding_vector', Vector(1536), nullable=True))


def downgrade() -> None:
    """Downgrade embedding_vector from 1536 to 1024 dimensions."""
    # Drop the 1536 dimension column
    op.drop_column('startups', 'embedding_vector')

    # Recreate with 1024 dimensions
    op.add_column('startups', sa.Column('embedding_vector', Vector(1024), nullable=True))
