"""chat_tz_offset

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chats",
        sa.Column("tz_offset_minutes", sa.Integer(), nullable=False, server_default="180"),
    )


def downgrade() -> None:
    op.drop_column("chats", "tz_offset_minutes")
