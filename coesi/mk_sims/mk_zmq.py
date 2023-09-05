"""
Sends mosaik simulation data to ZeroMQ socket.

From mosaik-zmq modified.

"""
import zmq
import mosaik_api


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
        self.eid = 'zmq'
        self.step_size = None
        self.duration = None
        self.db = None
        self.rels = None
        self.series = None
        self.data_buf = {}

        self.port = 5558
        self.host = 'tcp://*:'
        self.socket_type = 'PUB'

    def init(self, sid, step_size, duration, time_resolution=1., sim_meta = None):
        # if float(time_resolution) != 1.:
        #     raise ValueError('ExampleSim only supports time_resolution=1., but'
        #                      ' %s was set.' % time_resolution)
        self.sid = sid
        self.step_size = step_size
        self.duration = duration

        if self.meta['models'] == {}:
            self.meta['models'] = sim_meta['models']
        return self.meta

    def create(self, num, model, host, port, socket_type, buf_size=1000, dataset_opts=None):
        if num != 1 or self.db is not None:
            raise ValueError('Can only create one zeromq socket.')
        if model != 'zmq':
            raise ValueError('Unknown model: "%s"' % model)

        self.context = zmq.Context()
        if socket_type == 'PUSH':
            self.sender = self.context.socket(zmq.PUSH)
        elif socket_type == 'PUB':
            self.sender = self.context.socket(zmq.PUB)
        else:
            raise ValueError('Unknown socket type. Allowed are PUSH and PUB')
        self.sender.bind(host + str(port))
        return [{'eid': self.eid, 'type': model, 'rel': []}]

    def step(self, time, inputs, max_advance):
        assert len(inputs) == 1
        inputs = list(inputs.values())[0]
        data = (time,inputs)
        self.sender.send_json(data)
        return time + self.step_size

    def get_data(self, outputs):
        raise RuntimeError('mosaik_zmq does not provide any outputs.')

    def finalize(self):
        self.sender.close()


#  message structure from simulation
#         [29700,
#         {'power_dc':
#               {'pv-0.PV_0': 365.2684652613373},
#         'ghi':
#               {'pv-0.PV_0': 72.5001,
#               'csv_meteo-0.meteo_0': 72.5001},
#          T_ext': {'pv-0.PV_0': -1.84,
#                   'csv_meteo-0.meteo_0': -1.84}
#         }
#         ]

if __name__ == '__main__':
    desc = __doc__.strip()
    mosaik_api.start_simulation(MosaikZMQ(), desc)
