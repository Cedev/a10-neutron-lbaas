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

import acos_client

from a10_neutron_lbaas import a10_exceptions as ex
from a10_neutron_lbaas.db import models
from a10_neutron_lbaas.vthunder import instance_manager


class BasePlumbingHooks(object):

    def __init__(self, driver, **kwargs):
        self.driver = driver
        self.client_wrapper_class = None

    # While you can override select_device in hooks to get custom selection
    # behavior, it is much easier to use the 'device_scheduling_filters'
    # mechanism, as documented in the config file.

    def select_device(self, tenant_id):
        # Not a terribly useful scheduler
        raise ex.NotImplemented()

    # Network plumbing hooks from here on out

    def partition_create(self, client, context, partition_name):
        client.system.partition.create(partition_name)

    def partition_delete(self, client, context, partition_name):
        client.system.partition.delete(partition_name)

    def after_member_create(self, client, context, member):
        pass

    def after_member_update(self, client, context, member):
        pass

    def after_member_delete(self, client, context, member):
        pass

    def after_vip_create(self, client, context, vip):
        pass

    def after_vip_update(self, client, context, vip):
        pass

    def after_vip_delete(self, client, context, vip):
        pass


# The default set of plumbing hooks/scheduler, meant for hardware or manual orchestration

class PlumbingHooks(BasePlumbingHooks):

    def __init__(self, driver, devices=None, get_devices_func=None, **kwargs):
        super(PlumbingHooks, self).__init__(
            driver, devices=devices, get_devices_func=get_devices_func, **kwargs)
        if devices is not None:
            self.devices = devices
        elif get_devices_func is not None:
            self.devices = get_devices_func()
        else:
            self.devices = None
        self.appliance_hash = None

    def _late_init(self):
        if self.devices is None:
            self.devices = self.driver.config.get_devices()
        if self.appliance_hash is None:
            self.appliance_hash = acos_client.Hash(self.devices.keys())

    def _select_device_hash(self, tenant_id):
        self._late_init()

        # Must return device dict from config.py
        s = self.appliance_hash.get_server(tenant_id)
        return self.devices[s]

    def _select_device_db(self, tenant_id, db_session=None):
        self._late_init()

        # See if we have a saved tenant
        a10 = models.A10TenantBinding.find_by_tenant_id(tenant_id, db_session=db_session)
        if a10 is not None:
            if a10.device_name in self.devices:
                return self.devices[a10.device_name]
            else:
                raise ex.DeviceConfigMissing(
                    'A10 device %s mapped to tenant %s is not present in config; '
                    'add it back to config or migrate loadbalancers' %
                    (a10.device_name, tenant_id))

        # Nope, so we hash and save
        d = self._select_device_hash(tenant_id)
        models.A10TenantBinding.create_and_save(
            tenant_id=tenant_id, device_name=d['name'],
            db_session=db_session)

        return d

    def select_device(self, tenant_id):
        if self.driver.config.get('use_database'):
            return self._select_device_db(tenant_id)
        else:
            return self._select_device_hash(tenant_id)


# This next set of plumbing hooks needs to be used when the vthunder
# scheduler is active.

class VThunderPlumbingHooks(PlumbingHooks):

    def select_device_with_lbaas_obj(self, tenant_id, a10_context, lbaas_obj,
                                     db_session=None):
        if not self.driver.config.get('use_database'):
            raise ex.RequiresDatabase('vThunder orchestration requires use_database=True')

        # If we already have a vThunder, use it.

        if hasattr(lbaas_obj, 'root_loadbalancer'):
            # lbaas v2
            root_id = lbaas_obj.root_loadbalancer.id
            slb = models.A10SLB.find_by_loadbalancer_id(root_id, db_session=db_session)
            if slb is not None:
                d = self.driver.config.get(slb.device_name, db_session=db_session)
                if d is None:
                    raise ex.InstanceMissing(
                        'A10 instance mapped to loadbalancer_id %s is not present in db; '
                        'add it back to config or migrate loadbalancers' % root_id)
                return d
        else:
            # lbaas v1 -- one vthunder per tenant
            root_id = None
            tb = models.A10TenantBinding.find_by_tenant_id(tenant_id, db_session=db_session)
            if tb is not None:
                d = self.driver.config.get(tb.device_name, db_session=db_session)
                if d is None:
                    raise ex.InstanceMissing(
                        'A10 instance mapped to tenant %s is not present in db; '
                        'add it back to config or migrate loadbalancers' % tenant_id)
                return d

        # No? Then we need to create one.

        cfg = self.driver.config
        vth = cfg.get_vthunder_config()
        imgr = instance_manager.InstanceManager(
            ks_version=cfg.get('keystone_version'),
            auth_url=cfg.get('keystone_auth_url'),
            vthunder_tenant_name=vth['vthunder_tenant_name'],
            user=vth['vthunder_tenant_username'],
            password=vth['vthunder_tenant_password'],
            tenant_id=tenant_id,
            vthunder_config=vth)
        device_config = imgr.create_default_instance()

        models.A10Instance.create_and_save(
            device_config,
            db_session=db_session)

        if root_id is not None:
            models.A10SLB.create_and_save(
                device_name=device_config['name'],
                loadbalancer_id=root_id,
                db_session=db_session)
        else:
            models.A10TenantBinding.create_and_save(
                tenant_id=tenant_id,
                device_name=device_config['name'],
                db_session=db_session)

        return device_config

    def after_vip_create(self, client, context, vip):
        instance = self.device_cfg
        if 'nova_instance_id' not in instance:
            raise ex.InternalError('Attempting virtual plumbing on non-virtual device')

        if hasattr(vip, 'ip_address'):
            vip_ip_address = vip.ip_address
        else:
            vip_ip_address = vip['ip_address']

        cfg = self.driver.config
        vth = cfg.get_vthunder_config()
        imgr = instance_manager.InstanceManager(
            ks_version=cfg.get('keystone_version'),
            auth_url=cfg.get('keystone_auth_url'),
            vthunder_tenant_name=vth['vthunder_tenant_name'],
            user=vth['vthunder_tenant_username'],
            password=vth['vthunder_tenant_password'],
            tenant_id=context['tenant_id'],
            vthunder_config=vth)

        return imgr.plumb_instance_subnet(
            instance['nova_instance_id'],
            instance['vip_subnet_id'],
            vip_ip_address,
            wrong_ips=[instance['host']])
