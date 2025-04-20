from alembic import op
import sqlalchemy as sa

revision = 'a16decc90978'
down_revision = '44bac1551c2d'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_column('lesson', 'words_to_learn')
    op.add_column('lesson', sa.Column('words_to_learn', sa.ARRAY(sa.Integer()), nullable=True))

def downgrade() -> None:
    op.drop_column('lesson', 'words_to_learn')
    # Если хочешь восстановить старую ошибочную колонку:
    from sqlalchemy.dialects import postgresql
    op.add_column('lesson', sa.Column('words_to_learn', postgresql.ENUM('A1', 'A2', 'B1', 'B2', 'C1', 'C2', name='languagelevel'), nullable=True))
