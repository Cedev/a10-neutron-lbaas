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

import mock
import os

import oslo_config
import oslo_config.fixture
import test_base

import a10_neutron_lbaas
import a10_neutron_lbaas.db.migration.cli as cli
import sqlalchemy
import sys

import a10_neutron_lbaas.db.models as models
import neutron.db.models_v2 as neutron_models
import neutron.db.servicetype_db as servicetype_db
import neutron_lbaas.db.loadbalancer.loadbalancer_db as lbaasv1_models
import neutron_lbaas.db.loadbalancer.models as lbaasv2_models


class ARGV(object):

    def __init__(self, *argv):
        self.argv = argv

    def __enter__(self):
        self.original_argv = sys.argv
        sys.argv = self.argv
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sys.argv = self.original_argv


class TestCLI(test_base.UnitTestBase):

    def setUp(self):
        super(TestCLI, self).setUp()
        self.patch_create_engine = mock.patch.object(sqlalchemy,
                                                     'create_engine',
                                                     return_value=self.connection)
        self.patch_create_engine.__enter__()

    def tearDown(self):
        self.patch_create_engine.__exit__()
        super(TestCLI, self).tearDown()

    def run_cli(self, *argv, **kw):
        drivers = kw.get('drivers', mock.MagicMock())
        with oslo_config.fixture.Config(oslo_config.cfg.CONF):
            with ARGV(os.path.abspath(cli.__file__), *argv):
                return cli.run(drivers)

    def test_install(self):
        status = self.run_cli('install')

        self.assertEqual('UPGRADED', status['core'].status)
        self.assertEqual('UPGRADED', status['lbaasv1'].status)
        self.assertEqual('UPGRADED', status['lbaasv2'].status)

    def test_install_lbaasv1(self):
        drivers = {'LOADBALANCER': mock.MagicMock()}
        status = self.run_cli('install', drivers=drivers)

        self.assertEqual('UPGRADED', status['core'].status)
        self.assertEqual('UPGRADED', status['lbaasv1'].status)
        self.assertEqual('ERROR', status['lbaasv2'].status)

    def test_install_lbaasv2(self):
        drivers = {'LOADBALANCERV2': mock.MagicMock()}
        status = self.run_cli('install', drivers=drivers)

        self.assertEqual('UPGRADED', status['core'].status)
        self.assertEqual('ERROR', status['lbaasv1'].status)
        self.assertEqual('UPGRADED', status['lbaasv2'].status)

    def test_upgrade_heads_downgrade_base(self):
        self.run_cli('upgrade', 'heads')
        self.run_cli('downgrade', 'base')

    def test_install_downgrade_base(self):
        self.run_cli('install')
        self.run_cli('downgrade', 'base')

    def test_migration_populate_lbaasv1(self):
        device_key = 'fake-device-key'
        provider = 'fake-provider'
        tenant_id = 'fake-tenant'
        status = 'FAKE'

        session = self.Session()
        network = models.default(neutron_models.Network)
        session.add(network)
        subnet = models.default(
            neutron_models.Subnet,
            network_id=network.id,
            ip_version=4,
            cidr='10.0.0.0/8')
        session.add(subnet)
        pool = models.default(
            lbaasv1_models.Pool,
            tenant_id=tenant_id,
            admin_state_up=False,
            status=status,
            subnet_id=subnet.id,
            protocol="TCP",
            lb_method="ROUND_ROBIN")
        vip = models.default(
            lbaasv1_models.Vip,
            tenant_id=tenant_id,
            admin_state_up=False,
            status=status,
            pool_id=pool.id,
            pool=[pool],
            protocol=pool.protocol,
            protocol_port=80)
        vip_id = vip.id
        session.add(vip)
        pra = models.default(
            servicetype_db.ProviderResourceAssociation,
            provider_name=provider,
            resource_id=vip.id)
        session.add(pra)
        session.commit()

        mock_config = mock.MagicMock(
            name='mock_config',
            devices={device_key: {'key': device_key}})
        mock_hooks = mock.MagicMock(
            name='mock_hooks',
            select_device=lambda x: mock_config.devices[device_key])
        mock_a10 = mock.MagicMock(
            name='mock_a10',
            spec=a10_neutron_lbaas.A10OpenstackLBV1,
            config=mock_config,
            hooks=mock_hooks)
        mock_driver = mock.MagicMock(
            name='mock_driver',
            a10=mock_a10)
        drivers = {'LOADBALANCER': ({provider: mock_driver}, provider)}
        status = self.run_cli('install', drivers=drivers)

        self.assertEqual('UPGRADED', status['core'].status)
        self.assertEqual('UPGRADED', status['lbaasv1'].status)

        session = self.Session()
        slb = session.query(models.A10SLBV1).first()

        self.assertEqual(vip_id, slb.vip_id)

    def test_migration_populate_lbaasv2(self):
        device_key = 'fake-device-key'
        provider = 'fake-provider'
        tenant_id = 'fake-tenant'
        status = 'FAKE'

        session = self.Session()
        network = models.default(neutron_models.Network)
        session.add(network)
        subnet = models.default(
            neutron_models.Subnet,
            network_id=network.id,
            ip_version=4,
            cidr='10.0.0.0/8')
        session.add(subnet)
        lb = models.default(
            lbaasv2_models.LoadBalancer,
            tenant_id=tenant_id,
            admin_state_up=False,
            provisioning_status=status,
            operating_status=status,
            vip_subnet_id=subnet.id)
        lb_id = lb.id
        session.add(lb)
        pra = models.default(
            servicetype_db.ProviderResourceAssociation,
            provider_name=provider,
            resource_id=lb.id)
        session.add(pra)
        session.commit()

        mock_config = mock.MagicMock(
            name='mock_config',
            devices={device_key: {'key': device_key}})
        mock_hooks = mock.MagicMock(
            name='mock_hooks',
            select_device=lambda x: mock_config.devices[device_key])
        mock_a10 = mock.MagicMock(
            name='mock_a10',
            spec=a10_neutron_lbaas.A10OpenstackLBV2,
            config=mock_config,
            hooks=mock_hooks)
        mock_driver = mock.MagicMock(
            name='mock_driver',
            a10=mock_a10)
        drivers = {'LOADBALANCERV2': ({provider: mock_driver}, provider)}
        status = self.run_cli('install', drivers=drivers)

        self.assertEqual('UPGRADED', status['core'].status)
        self.assertEqual('UPGRADED', status['lbaasv2'].status)

        session = self.Session()
        slb = session.query(models.A10SLBV2).first()

        self.assertEqual(lb_id, slb.lbaas_loadbalancer_id)