"""calculator removed: service_type/area_m2/price_min/price_max become nullable

Revision ID: a1f3c9d27b44
Revises: cbc68d66be23
Create Date: 2026-08-16 14:00:00.000000

Владелец убрал калькулятор стоимости с сайта — клиент больше никогда не
передаёт service_type/area_m2/price_min/price_max при создании заявки
(см. DECISIONS.md). Существующие заявки, созданные до этой миграции,
сохраняют свои значения как есть.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1f3c9d27b44'
down_revision: Union[str, None] = 'cbc68d66be23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('leads') as batch_op:
        batch_op.alter_column(
            'service_type',
            existing_type=sa.Enum('maintenance', 'general', 'post_renovation', 'post_move',
                                   name='servicetype', native_enum=False, length=20),
            nullable=True,
        )
        batch_op.alter_column('area_m2', existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column('price_min', existing_type=sa.Numeric(precision=10, scale=2), nullable=True)
        batch_op.alter_column('price_max', existing_type=sa.Numeric(precision=10, scale=2), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('leads') as batch_op:
        batch_op.alter_column(
            'service_type',
            existing_type=sa.Enum('maintenance', 'general', 'post_renovation', 'post_move',
                                   name='servicetype', native_enum=False, length=20),
            nullable=False,
        )
        batch_op.alter_column('area_m2', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('price_min', existing_type=sa.Numeric(precision=10, scale=2), nullable=False)
        batch_op.alter_column('price_max', existing_type=sa.Numeric(precision=10, scale=2), nullable=False)
