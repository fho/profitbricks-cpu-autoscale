#!/usr/bin/env python

# Example script for CPU autoscaling of ProfitBricks Servers

# On the servers runs a inetd service that publishes the Load Average values as
# "Load: 0.01 0.03 0.02" line.
# This script gets the load average value from TCP service periodically,
# calculcates the CPU utilization and if the CPU utilization is bigger than a
# threshold a CPU is hot plugged into the server via the ProfitBricks API.

import logging
import datetime
import socket
import re
import sys
import time

sys.path.append("/home/fholler/git/ProfitBricks-CLI-API/src")
from pb.api import API

# List of servers that are autoscaled, as (host,port) tuples
# The port specifies port of the Load Avg. TCP service
SERVERS = [("127.0.0.1", 777), ("127.0.0.2", 777)]

# ProfitBricks User Account data
PB_USER = "email-addr"
PB_PASSWD = "my-very-secret-password"

# Maximum amount of cores that are plugged into a VM
MAX_CORES = 3

# If CPU utilization of a server is bigger than this threshhold a core is added
# to the VM.
CPU_UTILIZATION_THRESHOLD = 100

logger = logging.getLogger()
api = API(PB_USER, PB_PASSWD)


class ServerIdNotFoundError(Exception):
    pass


class Server(object):
    def _get_ressource_ids(self):
        # TODO: make this operation less expensive (caching?)
        logger.debug("Retrieving Server id for Host: %s" % (self.hostname))
        for dc in api.getAllDataCenters():
            dcid = dc["dataCenterId"]
            dc = api.getDataCenter(dcid)
            if "servers" not in dc:
                continue
            for server in dc["servers"]:
                if "nics" not in server:
                    continue
                for nic in server["nics"]:
                    if "ips" not in nic:
                        continue
                    for ip in nic["ips"]:
                        if ip == self.ip:
                            logger.debug("%s has Server ID: %s" %
                                         (self.hostname, server["serverId"]))
                            return (dc["dataCenterId"], server["serverId"])

        logger.warning("Server ID not found for host %s (%s) (IP correct?)."
                       (self.hostname, self.ip))
        return None

    def __init__(self, hostname, port):
        self.ip = socket.gethostbyname(hostname)
        self.hostname = hostname
        self.port = port
        self._cores = None
        self.load = ()
        self.last_update = None
        self.api = API(PB_USER, PB_PASSWD)
        res_ids = self._get_ressource_ids()
        if not res_ids:
            raise ServerIdNotFoundError()
        (self.datacenter_id, self.server_id) = res_ids

    def add_core(self):
        if self.cores >= MAX_CORES:
            logger.warning("Server already has %s cores, no cores added" %
                           self.cores)
            return
        cores = self.cores + 1
        res = api.updateServer({"srvid": self.server_id,
                                "cores": cores})
        logger.info("Adding core to server %s" % self.hostname)

        ts_hotplug = datetime.datetime.now()
        self._wait_for_dc_state("AVAILABLE")
        hotplug_duration = ((datetime.datetime.now() -
                            ts_hotplug).total_seconds())
        logger.info("+ Core Added (Total Cores: %s) to %s, Hotplugging CPU"
                    " took: %s seconds" %
                    (cores, self.hostname, hotplug_duration))

    def _update_metrics(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.hostname, self.port))

        receive = True
        buf = ""
        while receive:
            tmp = sock.recv(1024)
            if tmp:
                buf += tmp
            else:
                receive = False
        sock.close()

        m = re.search("Load: ([\d.]+)", buf)
        if m:
            self.load = float(m.groups()[0])
        else:
            logger.warning("Load value not found in %s:%s socket response" %
                           (self.hostname, self.port))
            self.load = None

        self.last_update = datetime.datetime.now()

    @property
    def load_avg(self):
        self._update_metrics()
        return self.load

    @property
    def core_utilization(self):
        return self.load_avg / self.cores * 100

    def _wait_for_dc_state(self, state):
        dc_state = "UNKNOWN"
        while dc_state != state:
            dc_state = api.getDataCenterState(self.datacenter_id)
            if dc_state != state:
                logger.info("Datacenter is in provisioning state %s, waiting"
                            " till it reaches state" " %s..." %
                            (dc_state, state))
                time.sleep(1)

    @property
    def cores(self):
        # wait till datacenter is in state AVAILABLE, if it is in INPROCESS and
        # we request the number of current CPus we can get an old number and
        # hotplug a new cpu again and again until we have an expensive VM with
        # the max. number of possible VMs :)
        self._wait_for_dc_state("AVAILABLE")
        server = api.getServer(self.server_id)
        self._cores = int(server["cores"])
        return self._cores


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    servers = []
    for host in SERVERS:
        try:
            s = Server(host[0], host[1])
        except ServerIdNotFoundError:
            logger.warning("Ignoring server: %s" % s.hostname)
            continue
        servers.append(s)

    while True:
        for s in servers:
            logger.info("Server %s (%s)\n\tCores: %s/%s\n\tLoad Avg.: %s\n"
                        "\tCore Utilization: %s%%" %
                        (s.hostname, s.ip, s.cores, MAX_CORES, s.load_avg,
                         s.core_utilization))
            if s.core_utilization > CPU_UTILIZATION_THRESHOLD:
                s.add_core()
            logger.info("Server %s (%s)\n\tCores: %s/%s\n\tLoad Avg.: %s\n"
                        "\tCore Utilization: %s%%" %
                        (s.hostname, s.ip, s.cores, MAX_CORES, s.load_avg,
                         s.core_utilization))
            logger.info("---------------")
            time.sleep(5)
