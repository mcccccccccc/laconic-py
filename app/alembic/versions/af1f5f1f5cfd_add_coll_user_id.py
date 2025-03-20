"""add coll user_id

Revision ID: af1f5f1f5cfd
Revises: 
Create Date: 2025-03-19 19:20:26.729909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, String, UUID, ForeignKey


# revision identifiers, used by Alembic.
revision: str = 'af1f5f1f5cfd'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("short_links", Column("user_id", UUID, ForeignKey("user.id")))
    pass


def downgrade() -> None:
    pass
