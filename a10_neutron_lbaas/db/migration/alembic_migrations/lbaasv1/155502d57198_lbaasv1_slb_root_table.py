# Copyright 2015,  A10 Networks
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""lbaasv1 slb root table

Revision ID: 155502d57198
Revises: 2e7daa753e19
Create Date: 2016-03-16 19:30:07.069851

"""

# revision identifiers, used by Alembic.
revision = '155502d57198'
down_revision = '2e7daa753e19'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'a10_slb_root_v1',
        sa.Column('id',
                  sa.String(36),
                  primary_key=True,
                  nullable=False),
        sa.Column('a10_appliance_id',
                  sa.String(36),
                  sa.ForeignKey('a10_appliances_slb.id'),
                  nullable=False),
        sa.Column('pool_id',
                  sa.String(36),
                  sa.ForeignKey('pools.id'),
                  unique=True,
                  nullable=False)
    )


def downgrade():
    op.drop_table('a10_slb_root_v1')
