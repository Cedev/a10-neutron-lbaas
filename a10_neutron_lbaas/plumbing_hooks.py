# Copyright 2014, A10 Networks
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

# Plumbing hooks is the primary way to override the scheduling and plumbing
# used within this driver. Please refer to plumbing/*, as this is the old
# location of this module.

# Backwards-compat locations

from a10_neutron_lbaas.plumbing.simple import PlumbingHooks  # flake8: noqa
from a10_neutron_lbaas.plumbing.vthunder_user_tenant import VThunderPerTenantPlumbingHooks \
    as VThunderPlumbingHooks  # flake8: noqa
