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

from twisted.internet import defer
from twisted.python import log
from twisted.internet import threads

from buildbot.util import service


def deferToThread(f):
    '''
    Run a synchronous method that potentially can take lot of time into a deferred thread, so this
    will not block the main reactor. Use it when you want to issue network request with a non
    twisted library.
    '''
    def decorated(*args, **kwargs):
        return threads.deferToThread(f, *args, **kwargs)
    return decorated


class MetricsService(service.ReconfigurableServiceMixin, service.AsyncMultiService):

    def __init__(self, master):
        service.AsyncMultiService.__init__(self)
        self.setName('metricsService')
        log.msg("Creating MetricsService")
        self.master = master
        self.registeredDbServices = []

    def reconfigServiceWithBuildbotConfig(self, new_config):
        log.msg("Reconfiguring MetricsService with config: {!r}".format(new_config))

        for svc in new_config.metricsServices:
            if not isinstance(svc, DBServiceBase):
                raise TypeError("Invalid type of metrics storage service {!r}. "
                                "Should be of type DBServiceBase, "
                                "is: {}".format(type(DBServiceBase)))
            self.registeredDbServices.append(svc)

        return svc.ReconfigurableServiceMixin.reconfigServiceWithBuildbotConfig(self,
                                                                                new_config)

    @defer.inlineCallbacks
    def postMetricsValue(self, name, value, context):
        '''
        name: name of the metrics that has been created by the step
        value: value of this metrics
        context: dictionary with contextual information (TBD), such as:
           - step name
           - build name
           - builder id
           - ...
        '''
        # post to each of the storage services
        # import ipdb;ipdb.set_trace()
        for registerService in self.registeredDbServices:
            yield registerService.postMetricsValue(name, value, context)


class DBServiceBase(object):

    """
    Base class for sub service responsible for passing on metrics data to a Metrics Storage
    """

    # Note: both following code are equivalent
    # @defer.inlineCallbacks
    # def postMetricsValue(self, name, value, context):
    #     defer.returnValue(None)
    def postMetricsValue(self, name, value, context):
        return defer.succeed(None)


class FakeDBService(DBServiceBase):

    """
    Fake Storage service used in unit tests
    """

    def __init__(self):
        self.stored_data = []

    @defer.inlineCallbacks
    def postMetricsValue(self, name, value, context):
        self.stored_data.append((name, value, context))
        defer.returnValue(None)


class InfluxDBService(DBServiceBase):

    """
    Delegates data to InfluxDB
    """

    def __init__(self, url, port, user, password, db, metrics):
        self.url = url
        self.port = port
        self.user = user
        self.password = password
        self.db = db

        self.metrics = metrics
        self.inited = False

        try:
            from influxdb import InfluxDBClient
            self.client = InfluxDBClient(self.url, self.port, self.user,
                                         self.password, self.db)
            self.inited = True
        except:
            pass

    # This decorator is more easy to use than
    # res = yield threads.deferToThread(syncMethodToMakeAsync, arg1, arg2, ....)
    # Simply yield this call directly and it will be run into a deferred tutu
    @deferToThread
    def postMetricsValue(self, name, value, context):
        if not self.inited:
            return
        log.msg("Sending data to InfluxDB")
        log.msg("name: {!r}".format(name))
        log.msg("value: {!r}".format(value))
        log.msg("context: {!r}".format(context))

        buildername = self.context["builder_name"]
        data = {}
        data['name'] = buildername + '-' + name
        data['fields'] = {
            "name": name,
            "value": value
        }
        data['tags'] = {
            "buildername": buildername,
        }
        points = [data]
        self.client.write_points(points)
