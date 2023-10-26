"""
Heating System simulator for Mosaik.

Research group of Politecnico di Torino Energy Center Lab.

- author: Daniele Salvatore Schiera
- copyright: Copyright 2020. Energy Center Lab - Politecnico di Torino"
- credits: Daniele Salvatore Schiera
- maintainer: Daniele Salvatore Schiera
- email: daniele.schiera@polito.it
- status: Development
"""

import sys
from pathlib import Path

import mosaik_api

PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.insert(0, PROJECT_ROOT)
from models.heating_system.heating_system_sim import Heating_system

# META = {
#     'models': {
#         'NAMEMODEL': {
#             'public': True,
#             'params': [],
#             'attrs': [],
#         },
#     },
# }

META = {
    'type': 'time-based',
    'models': {}
}


class Heating_System(mosaik_api.Simulator):

    def __init__(self):
        super().__init__(META)
        # self.eid_prefix = 'hs_'
        self.entities = {}  # Maps EIDs to model indices in self.simulator

    def init(self, sid, time_resolution=1., eid_prefix=None, step_size=None, stop_time=None, sim_meta=None):
        if float(time_resolution) != 1.:
            raise ValueError('ExampleSim only supports time_resolution=1., but'
                             ' %s was set.' % time_resolution)
        if eid_prefix is not None:
            self.eid_prefix = eid_prefix
        self.step_size = step_size
        self.stop_time = stop_time

        if self.meta['models'] == {}:
            self.meta['models'] = sim_meta['models']
        return self.meta

    #todo should add instance name for the specific boiler??
    def create(self, num, model, leased_area=100, EPC_rating='B', type='hp', storage=False, sizing=True,
               Text_mean_season=0, V_tank=100,
               **kwargs):
        next_eid = len(self.entities)
        entities = []

        for i in range(next_eid, next_eid + num):
            eid = '%s_%d' % (model, i)
            model_instance = Heating_system(leased_area, EPC_rating, step_size=self.step_size, type=type, storage=storage, sizing=sizing,
                                            Text_mean_season=Text_mean_season, V_tank=V_tank,
                                            **kwargs)

            self.entities[eid] = model_instance
            entities.append({'eid': eid, 'type': model})

        return entities

    def step(self, time, inputs, max_advance):
        self.time = time

        # Text and Qt from House
        # Perform simulation steps
        for eid, model_instance in self.entities.items():
            if eid in inputs:
                attrs = inputs[eid]
                for attr, values in attrs.items():
                    if attr == 'Qt': # W
                        Qt = sum(values.values())
                    elif attr == 'Text':
                        Text = list(values.values())[0]

            model_instance.step(Text, Qt)

        return time + self.step_size  # Step size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            model = self.entities[eid]
            data['time'] = self.time
            model_type = eid.split('_')[0]
            data[eid] = {}
            for attr in attrs:
                if attr not in self.meta['models'][model_type]['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)

                # Get model.val or model.delta:
                data[eid][attr] = getattr(model, attr)
        return data


if __name__ == '__main__':
    mosaik_api.start_simulation(Heating_System())
