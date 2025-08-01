"""Add Photo model for multiple images

Revision ID: 0ac113b6a272
Revises: 67dbd0e48445
Create Date: 2025-07-27 19:40:58.694102
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0ac113b6a272'
down_revision = '67dbd0e48445'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'photo' not in inspector.get_table_names():
        op.create_table(
            'photo',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('filename', sa.String(length=255), nullable=False),
            sa.Column('room_id', sa.Integer(), sa.ForeignKey('property.id', name='fk_photo_property'), nullable=False)
        )
    else:
        print("📸 Table 'photo' already exists. Skipping creation.")


def downgrade():
    op.drop_table('photo')
