"""update db

Revision ID: 4680975c9767
Revises: e4955192f245
Create Date: 2024-08-12 22:04:02.934073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4680975c9767'
down_revision: Union[str, None] = 'e4955192f245'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a temporary table with the new structure
    op.create_table(
        'temp_RatingUsers',
        sa.Column('user_id', sa.BIGINT(), nullable=False),
        sa.Column('chat_id', sa.BIGINT(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('user_id', 'chat_id')
    )

def downgrade() -> None:
   # Create a temporary table with the old structure    
   op.drop_table('temp_RatingUsers')