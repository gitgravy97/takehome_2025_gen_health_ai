"""add medical_record_number to patients

Revision ID: 0bcee806b271
Revises: 001
Create Date: 2025-11-23 12:32:15.892630

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bcee806b271'
down_revision: Union[str, Sequence[str], None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add medical_record_number column to patients table."""
    # Add the medical_record_number column (nullable initially to handle existing data)
    op.add_column('patients', sa.Column('medical_record_number', sa.String(length=50), nullable=True))

    # Create unique index on medical_record_number
    op.create_index(op.f('ix_patients_medical_record_number'), 'patients', ['medical_record_number'], unique=True)

    # Note: In production, you would need to populate medical_record_number for existing rows
    # before making it non-nullable. Since we have no data, we can skip that step.
    # If you had data, you would:
    # 1. Add column as nullable
    # 2. Run data migration to populate medical_record_number
    # 3. Make column non-nullable with: op.alter_column('patients', 'medical_record_number', nullable=False)


def downgrade() -> None:
    """Remove medical_record_number column from patients table."""
    # Drop the index first
    op.drop_index(op.f('ix_patients_medical_record_number'), table_name='patients')

    # Drop the column
    op.drop_column('patients', 'medical_record_number')
