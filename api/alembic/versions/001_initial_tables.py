"""initial tables

Revision ID: 001
Revises:
Create Date: 2025-11-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create patients table
    op.create_table(
        'patients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patients_id'), 'patients', ['id'], unique=False)

    # Create prescribers table
    op.create_table(
        'prescribers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('npi', sa.String(length=10), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('clinic_name', sa.String(length=255), nullable=True),
        sa.Column('clinic_address', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prescribers_id'), 'prescribers', ['id'], unique=False)
    op.create_index(op.f('ix_prescribers_npi'), 'prescribers', ['npi'], unique=True)

    # Create devices table
    op.create_table(
        'devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('authorization_required', sa.Boolean(), nullable=True),
        sa.Column('cost_per_unit', sa.Integer(), nullable=True),
        sa.Column('device_type', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_devices_id'), 'devices', ['id'], unique=False)
    op.create_index(op.f('ix_devices_sku'), 'devices', ['sku'], unique=True)

    # Create orders table with foreign keys (many-to-one relationships)
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_name', sa.String(length=255), nullable=True),
        sa.Column('order_cost_raw', sa.Integer(), nullable=True),
        sa.Column('order_cost_to_insurer', sa.Integer(), nullable=True),
        sa.Column('item_quantity', sa.Integer(), nullable=True),
        sa.Column('reason_prescribed', sa.Text(), nullable=True),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('prescriber_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['prescriber_id'], ['prescribers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=False)

    # Create order_devices association table
    op.create_table(
        'order_devices',
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('order_id', 'device_id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('order_devices')
    op.drop_index(op.f('ix_orders_id'), table_name='orders')
    op.drop_table('orders')
    op.drop_index(op.f('ix_devices_sku'), table_name='devices')
    op.drop_index(op.f('ix_devices_id'), table_name='devices')
    op.drop_table('devices')
    op.drop_index(op.f('ix_prescribers_npi'), table_name='prescribers')
    op.drop_index(op.f('ix_prescribers_id'), table_name='prescribers')
    op.drop_table('prescribers')
    op.drop_index(op.f('ix_patients_id'), table_name='patients')
    op.drop_table('patients')
