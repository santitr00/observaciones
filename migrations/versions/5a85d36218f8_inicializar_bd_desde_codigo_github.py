"""inicializar_bd_desde_codigo_github

Revision ID: 5a85d36218f8
Revises: 
Create Date: 2025-05-18 19:49:03.107449

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a85d36218f8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dni', sa.String(length=20), nullable=False),
    sa.Column('nombre_completo', sa.String(length=128), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('password_hash', sa.String(length=256), nullable=True),
    sa.Column('barrio', sa.String(length=100), nullable=False),
    sa.Column('zona', sa.String(length=100), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dni', 'barrio', name='uq_dni_barrio')
    )
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_barrio'), ['barrio'], unique=False)
        batch_op.create_index(batch_op.f('ix_user_dni'), ['dni'], unique=False)
        batch_op.create_index(batch_op.f('ix_user_email'), ['email'], unique=True)

    op.create_table('observation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('classification', sa.String(length=100), nullable=False),
    sa.Column('body', sa.String(length=500), nullable=False),
    sa.Column('observation_date', sa.Date(), nullable=False),
    sa.Column('observation_time', sa.Time(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('barrio', sa.String(length=100), nullable=False),
    sa.Column('zona', sa.String(length=100), nullable=False),
    sa.Column('filename', sa.String(length=200), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('observation', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_observation_barrio'), ['barrio'], unique=False)
        batch_op.create_index(batch_op.f('ix_observation_observation_date'), ['observation_date'], unique=False)
        batch_op.create_index(batch_op.f('ix_observation_timestamp'), ['timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_observation_zona'), ['zona'], unique=False)

    op.create_table('user_puesto_assignment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('barrio', sa.String(length=100), nullable=False),
    sa.Column('puesto', sa.String(length=100), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'barrio', 'puesto', name='uq_user_barrio_puesto')
    )
    with op.batch_alter_table('user_puesto_assignment', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_puesto_assignment_barrio'), ['barrio'], unique=False)
        batch_op.create_index(batch_op.f('ix_user_puesto_assignment_puesto'), ['puesto'], unique=False)
        batch_op.create_index(batch_op.f('ix_user_puesto_assignment_user_id'), ['user_id'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_puesto_assignment', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_puesto_assignment_user_id'))
        batch_op.drop_index(batch_op.f('ix_user_puesto_assignment_puesto'))
        batch_op.drop_index(batch_op.f('ix_user_puesto_assignment_barrio'))

    op.drop_table('user_puesto_assignment')
    with op.batch_alter_table('observation', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_observation_zona'))
        batch_op.drop_index(batch_op.f('ix_observation_timestamp'))
        batch_op.drop_index(batch_op.f('ix_observation_observation_date'))
        batch_op.drop_index(batch_op.f('ix_observation_barrio'))

    op.drop_table('observation')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_email'))
        batch_op.drop_index(batch_op.f('ix_user_dni'))
        batch_op.drop_index(batch_op.f('ix_user_barrio'))

    op.drop_table('user')
    # ### end Alembic commands ###
