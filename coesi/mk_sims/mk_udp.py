"""
Simulator adn api to send and receive mosaik simulation data to VILLASframework through  UDP.

Research group of Politecnico di Torino Energy Center Lab.

- author: Daniele Salvatore Schiera & Luca Barbierato
- maintainer: Daniele Salvatore Schiera
- email: daniele.schiera@polito.it
- status: Development

"""

import mosaik_api_v3 as mosaik_api

import time, errno
import socket
import sys
import threading
import multiprocessing
import queue

from pathlib import Path
PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.append(PROJECT_ROOT)

from coesi.tests import villas_pb2


# meta = {
#     'models': {
#         'Socket': {
#             'public': True,
#             'params': ['host', 'port'],
#             'attrs': [],
#         },
#     },
# }

META = {
    'type': 'time-based',
    'models': {}
}

BUFFER_SIZE = 1024


class UDP(object):

    def __init__(self, ip, port, msg_rcv):
        self.protocol = 'UDP'
        self.ip = ip
        self.port = port
        self.counter_opal = 0

        self.socket = (self.ip, self.port)
        self.opal = None
        self.q_opal = queue.Queue()
        self.msg_rcv = msg_rcv

        self.vars_values_rcv = {}

        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print('Starting up UDP Server on IP %s Port %s' % self.socket)
        local = ('127.0.0.1', 12004)
        self.server.bind(local)
        self.server.connect(self.socket)

    def start(self):
        self.receiveThread = threading.Thread(target=self.receive_from_opal)
        self.receiveThread.start()
        # super(self.__class__, self).start(ip, port)

    def stop(self):
        #super(self.__class__, self).stop()
        if (hasattr(self, "receiveThread")):
            if self.receiveThread.is_alive():
                try:
                    self.receiveThread._Thread__stop()
                except Exception:
                    print(sys.stderr)
        self.server.close()

    def receive_from_opal(self):

        while self.receiveThread.is_alive():
            data = self.server.recv(BUFFER_SIZE)
            self.msg_rcv.ParseFromString(data)
            for i in range(len(self.msg_rcv.samples[0].values[:])):
                self.vars_values_rcv[i] = self.msg_rcv.samples[0].values[i].f
            #print(self.vars_values_rcv)
            # try:
            #     data = self.server.recv(BUFFER_SIZE)
            #     self.msg_rcv.ParseFromString(data)
            #     for i in range(len(self.msg_rcv.samples[0].values[:])):
            #         self.vars_values_rcv[i]= self.msg_rcv.samples[0].values[i].f
            #     print(self.vars_values_rcv)
            # except Exception:
            #     print('YES')
            #     print(Exception)

class MosaikUDP(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.sid = None
        self.eid = 'udp'

        self.step_size = None

        self.data_rcv = {}

    def init(self, sid, step_size, time_resolution=1., sim_meta = None):
        # if float(time_resolution) != 1.:
        #     raise ValueError('ExampleSim only supports time_resolution=1., but'
        #                      ' %s was set.' % time_resolution)
        self.sid = sid
        self.step_size = step_size

        # Message sender construction
        self.msg_snd = villas_pb2.Message()
        self.sample = self.msg_snd.samples.add()
        self.sample.type = 1

        # Message receiver init
        self.msg_rcv = villas_pb2.Message()

        if self.meta['models'] == {}:
            self.meta['models'] = sim_meta['models']
        return self.meta

    def create(self, num, model, host, port, binding_vrs, start_vrs=None):
        if num != 1:
            raise ValueError('Can only create one udp socket.')
        self.eid = model
        # if model != 'udp':
        #     raise ValueError('Unknown model: "%s"' % model)

        if not binding_vrs:
            raise Exception('It is necessary to provide the binding registry of the exchanged variables by using dict '
                            'binding_vrs param.')
        if not start_vrs:
            raise Exception('It is necessary to provide the starting values of the attributes by using dict start_vrs '
                            'param.')
        if self.meta['models'][model]['attrs'] != list(start_vrs.keys()):
            raise Exception('Declare the attributes in ATTRS and the starting values in the same order.')

        self.start_vrs = start_vrs

        self.vars_rcv = binding_vrs['rcv']
        self.vars_snd = binding_vrs['snd']

        self.udp = UDP(host, port, self.msg_rcv)

        self.udp.start()

        #self.server.receive_from_opal()


        for var, id in self.vars_snd.items():
            self.sample.values.add()
            self.sample.values[id].f = start_vrs[var]
        self.udp.server.send(self.msg_snd.SerializeToString())




        # local = ('130.192.177.102', 12004)
        # remote = (ost, port)
        #
        # print('Start client...')
        # self.receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #
        # self.receiver.bind(local)
        #
        # # Try to connect in case Unix domain socket does not exist yet..
        # connected = False
        # while not connected:
        #     try:
        #         self.receiver.connect(remote)
        #     except socket.error as serr:
        #         if serr.errno not in [errno.ECONNREFUSED, errno.ENOENT]:
        #             raise serr
        #
        #         print('Not connected. Retrying in 1 sec')
        #         time.sleep(1)
        #     else:
        #         connected = True
        #         print('Connected')
        #
        print('Ready.')

        return [{'eid': self.eid, 'type': model, 'rel': []}]

    def step(self, timemk, inputs, max_advance):
        # Set inputs
        for dest_eid, attrs in inputs.items():
            for attr, values in attrs.items():
                new_attr_value = sum(values.values()) # depending on model controlled in villas (grid with battery
                # example)
                self.sample.values[self.vars_snd[attr]].f = new_attr_value

        # TODO implementare il tempo
        self.udp.server.send(self.msg_snd.SerializeToString())
        return timemk + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr not in self.meta['models'][self.eid]['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)
                try:
                    data[eid][attr] = self.udp.vars_values_rcv[self.vars_rcv[attr]]
                except KeyError:
                    data[eid][attr] = self.start_vrs[attr]
        return data



    def finalize(self):
        #self.udp.stop()
        self.udp.server.close()
        # try:
        #     self.udp.stop()
        # except AttributeError:
        #     pass


if __name__ == '__main__':
    desc = __doc__.strip()
    mosaik_api.start_simulation(MosaikUDP(), desc)
