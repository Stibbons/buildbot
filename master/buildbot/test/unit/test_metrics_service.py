# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

import mock

from twisted.internet import defer
from twisted.trial import unittest

from buildbot import config
from buildbot.metrics.metrics_service import MetricsService
from buildbot.metrics.metrics_service import FakeDBService
from buildbot.metrics.metrics_service import InfluxDBService
from buildbot.steps import master
from buildbot.test.util import steps


class TestMetricsServicesBase(unittest.TestCase):

    def setUp(self):
        self.master = mock.Mock(name='master')
        self.config = config.MasterConfig()

        self.metrics_service = MetricsService(self.master)
        self.metrics_service.startService()

    def tearDown(self):
        self.metrics_service.stopService()


class TestMetricsServicesConfiguration(TestMetricsServicesBase):

    @defer.inlineCallbacks
    def test_reconfigure_without_conf(self):
        yield self.metrics_service.reconfigServiceWithBuildbotConfig(self.config)

    @defer.inlineCallbacks
    def test_reconfigure_with_fake_service(self):
        # First, configure with an empty service
        yield self.metrics_service.reconfigServiceWithBuildbotConfig(self.config)

        # Now, reconfigure with a FakeDBService.
        self.config.metricsServices[FakeDBService()]
        yield self.metrics_service.reconfigServiceWithBuildbotConfig(self.config)

        # unset it, see it stop
        self.config.metricsServices = []
        yield self.metrics_service.reconfigServiceWithBuildbotConfig(self.config)

    # Smooth test of influx db service. We don't want to force people to install influxdb, so we
    # just disable this unit test if the influxdb module is not installed, using SkipTest
    @defer.inlineCallbacks
    def test_reconfigure_with_influx_service(self):
        try:
            # Try to import
            import influxdb
            # consume it somehow to please pylint
            [influxdb]
        except:
            raise unittest.SkipTest("Skipping unit test of InfluxDBService because "
                                    "you don't have the influxdb module in your system")

        self.config.metricsServices[InfluxDBService(
            "fake_url", "fake_port", "fake_user", "fake_password", "fake_db", "fake_metrics",
        )]
        yield self.metrics_service.reconfigServiceWithBuildbotConfig(self.config)


class TestMetricsServicesYieldValue(TestMetricsServicesBase):

    @defer.inlineCallbacks
    def test_reconfigure_without_conf(self):
        fake_db_service = FakeDBService()
        self.config.metricsServices[fake_db_service]
        yield self.metrics_service.reconfigServiceWithBuildbotConfig(self.config)
        name = "metrics name"
        value = "value"
        context = {"builder_name": "name of the builder"}
        yield self.master.metricsServices.postMetricsValue(name, value, context)

        self.assertEqual([{
            name: "metrics name",
            value: "value",
            context: {"builder_name": "name of the builder"},
        }], fake_db_service.stored_data)


class TestMetricsServicesCallFromAStep(steps.BuildStepMixin, TestMetricsServicesBase):

    '''
    test the metrics service from a fake step
    '''

    def setUp(self):
        TestMetricsServicesBase.setUp(self)
        return self.setUpBuildStep()

    def tearDown(self):
        TestMetricsServicesBase.tearDown(self)
        return self.tearDownBuildStep()

    def createFakeBuildStep(self):
        def
        self.setupStep(self.createDynamicRun(None))
