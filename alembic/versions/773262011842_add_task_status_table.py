"""add_task_status_table

Revision ID: 773262011842
Revises: 4262ff5f798e
Create Date: 2025-12-31 00:02:01.372098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '773262011842'
down_revision: Union[str, None] = '4262ff5f798e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create TaskState enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE taskstate AS ENUM ('pending', 'started', 'success', 'failure', 'retry');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create task_status table without triggering automatic enum creation
    op.create_table(
        'task_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('state', postgresql.ENUM('pending', 'started', 'success', 'failure', 'retry', name='taskstate', create_type=False), nullable=False, server_default='pending'),
        sa.Column('result', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_status_created_at'), 'task_status', ['created_at'], unique=False)
    op.create_index(op.f('ix_task_status_task_id'), 'task_status', ['task_id'], unique=True)
    op.create_index(op.f('ix_task_status_user_id'), 'task_status', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_task_status_user_id'), table_name='task_status')
    op.drop_index(op.f('ix_task_status_task_id'), table_name='task_status')
    op.drop_index(op.f('ix_task_status_created_at'), table_name='task_status')
    op.drop_table('task_status')
    
    # Drop TaskState enum
    op.execute("DROP TYPE IF EXISTS taskstate")
