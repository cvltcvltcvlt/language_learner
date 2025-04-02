"""empty message

Revision ID: 3a98bf639142
Revises: 4acf53bd1ba9
Create Date: 2025-04-02 23:49:42.008265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a98bf639142'
down_revision: Union[str, None] = '4acf53bd1ba9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('words',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('word', sa.String(), nullable=True),
    sa.Column('translation', sa.String(), nullable=True),
    sa.Column('language_level', sa.Enum('A1', 'A2', 'B1', 'B2', 'C1', 'C2', name='languagelevel'), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_words_id'), 'words', ['id'], unique=False)
    op.create_index(op.f('ix_words_word'), 'words', ['word'], unique=False)
    op.drop_index('ix_word_id', table_name='word')
    op.drop_index('ix_word_word', table_name='word')
    op.drop_table('word')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('word',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('word', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('translation', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('pronunciation', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('example_sentence', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('language', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='word_pkey')
    )
    op.create_index('ix_word_word', 'word', ['word'], unique=True)
    op.create_index('ix_word_id', 'word', ['id'], unique=False)
    op.drop_index(op.f('ix_words_word'), table_name='words')
    op.drop_index(op.f('ix_words_id'), table_name='words')
    op.drop_table('words')
    # ### end Alembic commands ###
