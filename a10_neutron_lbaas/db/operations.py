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
#    under the License.from neutron.db import model_base

from sqlalchemy import or_
from sqlalchemy.orm import with_polymorphic

import models


class Operations(object):

    def __init__(self, openstack_context):
        self.session = openstack_context.session

    def summon_appliance_configured(self, device_key):
        # print 'summon_appliance_configured({0})'.format(repr(device_key))
        return models.summon(self.session,
                             models.A10ApplianceConfigured,
                             device_key=device_key)

    def get_slb_v1(self, vip_id):
        # print 'get_slb_v1({0})'.format(repr(vip_id))
        return self.session.query(models.A10SLBV1).\
            filter_by(vip_id=vip_id).first()

    def delete_slb_v1(self, vip_id):
        query = self.session.query(models.A10SLBV1).filter_by(vip_id=vip_id)
        models.delete_all(self.session, query)

    def get_slb_v2(self, loadbalancer_id):
        # print 'get_slb_v2({0})'.format(repr(loadbalancer_id))
        return self.session.query(models.A10SLBV2).\
            filter_by(lbaas_loadbalancer_id=loadbalancer_id).first()

    def delete_slb_v2(self, loadbalancer_id):
        query = self.session.query(models.A10SLBV2).\
            filter_by(lbaas_loadbalancer_id=loadbalancer_id)
        models.delete_all(self.session, query)

    def get_tenant_appliance(self, tenant_id):
        return self.session.query(models.A10TenantAppliance).\
            filter_by(tenant_id=tenant_id).first()

    def get_shared_appliances(self, tenant_id):
        """Get appliances that are shared with (available for the tenant to use)"""

        any_appliance = with_polymorphic(models.A10ApplianceSLB,
                                         [models.A10ApplianceConfigured, models.A10ApplianceDB])
        not_null_ = lambda x: x != None  # noqa
        return list(self.session.query(any_appliance).filter(
            or_(
                not_null_(any_appliance.A10ApplianceConfigured.id),
                not_null_(any_appliance.A10ApplianceDB.id),
                any_appliance.A10ApplianceDB.tenant_id == tenant_id
            )))

    def add(self, obj):
        # print 'add({0})'.format(repr(obj))
        return self.session.add(obj)
