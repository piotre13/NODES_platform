import sys
from pathlib import Path

import mosaik_api_v3 as mosaik_api



PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.insert(0,PROJECT_ROOT)

from models.graps.WaterReservoir import WaterReservoir

__version__ = '0.1'

META = {
    'type': 'time-based',
    'models': {}
}

class WaterReservoirSim(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.eid_prefix = ''
        self.entities = {}
        self.sid = None

    def init(self, sid, stepsize=None, time_resolution=1., sim_meta=None, eid_prefix=None):
        if eid_prefix is not None:
            self.eid_prefix = eid_prefix

        if stepsize is not None:
            self.step_size = stepsize
        else:
            self.step_size = 86400

        self.time_resolution = time_resolution

        if self.meta['models'] == {} and sim_meta != None:
            self.meta['models'] = sim_meta['models']

        return self.meta

    def create(self, num, model, input_names=None):
        next_eid = len(self.entities)
        entities = []

        for i in range(next_eid, next_eid + num):
            eid = '%s_%d' % (model, i)
            self.entities[eid] = WaterReservoir(eid, input_names)
            entities.append({'eid': eid, 'type': model})

        return entities

    def step(self, time, inputs, max_advance):
        self.time = time
        print(time)
        # Check for new delta and do step for each model instance:
        for eid, model_instance in self.entities.items():
            if eid in inputs:
                attrs = inputs[eid]
                for attr, values in attrs.items():
                    for key, value in values.items():
                        print(value)
                        model_instance.listWatershed[attr].step(value)
        model_instance.step()
        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            model = self.entities[eid]
            model_type = eid.split('_')[0]
            data['time'] = self.time
            data[eid] = {}
            for attr in attrs:
                if attr not in self.meta['models'][model_type]['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)

                # Get model.val or model.delta:
                data[eid][attr] = model.listStorage[attr]

        return data

def main():
    return mosaik_api.start_simulation(WaterReservoirSim())