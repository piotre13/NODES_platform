"""
Sends mosaik simulation data to ZeroMQ socket.

From mosaik-zmq modified.

"""
import zmq
import mosaik_api
import json
import collections

# meta = {
#     'models': {
#         'Socket': {
#             'public': True,
#             'any_inputs': True,
#             'params': ['host', 'port', 'socket_type'],
#             'attrs': [],
#         },
#     },
# }

META = {
    'type': 'time-based',
    'models': {}
}


class MosaikZMQ(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.sid = None
        self.eid = 'zmq_rcv'
        self.step_size = None
        self.duration = None
        self.db = None
        self.rels = None
        self.series = None
        self.data_buf = {}

        self.data_rcv = {}

        self.port = 5560
        self.host = 'tcp://*:'
        self.socket_type = 'SUB'

    def init(self, sid, step_size, duration, time_resolution=1., sim_meta = None):
        if float(time_resolution) != 1.:
            raise ValueError('ExampleSim only supports time_resolution=1., but'
                             ' %s was set.' % time_resolution)
        self.sid = sid
        self.step_size = step_size
        self.duration = duration

        if self.meta['models'] == {}:
            self.meta['models'] = sim_meta['models']
        return self.meta

    def create(self, num, model, host, port, socket_type, buf_size=1000, dataset_opts=None, start_vrs=None):
        if num != 1 or self.db is not None:
            raise ValueError('Can only create one zeromq socket.')
        if model != 'zmq_rcv':
            raise ValueError('Unknown model: "%s"' % model)

        if not start_vrs:
            raise Exception('It is necessary to provide the starting values of the attributes.')
        if self.meta['models']['zmq_rcv']['attrs'] != list(start_vrs.keys()):
            raise Exception('Declare the attributes in ATTRS and the starting values')

        self.start_vrs = start_vrs

        self.context = zmq.Context()
        self.receiver = self.context.socket(zmq.SUB)
        print("tcp://"+host+":"+str(port))
        self.receiver.connect("tcp://"+host+":"+str(port))
        self.receiver.setsockopt_string(zmq.SUBSCRIBE, '')

        return [{'eid': self.eid, 'type': model, 'rel': []}]

    def step(self, time, max_advance, inputs=None):
        if self.receiver.poll(100, zmq.POLLIN):
            msg = self.receiver.recv_json()
            self.data_rcv = msg
        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr not in self.meta['models']['zmq_rcv']['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)
                try:
                    data[eid][attr] = self.data_rcv[attr]
                except KeyError:
                    data[eid][attr] = self.start_vrs[attr]

        return data



    def finalize(self):
        self.receiver.close()


if __name__ == '__main__':
    desc = __doc__.strip()
    mosaik_api.start_simulation(MosaikZMQ(), desc)
