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

"""nova instance appliances

Revision ID: 36e79d2f7747
Revises: 28a984ff83e1
Create Date: 2015-11-13 22:14:46.556379

"""

# revision identifiers, used by Alembic.
revision = '36e79d2f7747'
down_revision = '28a984ff83e1'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'a10_appliances_nova',
        sa.Column('id',
                  sa.String(36),
                  sa.ForeignKey('a10_appliances_slb.id'),
                  primary_key=True,
                  nullable=False),
        sa.Column('instance_id', sa.String(36), nullable=False)
    )


def downgrade():
    op.drop_table('a10_appliances_nova')
