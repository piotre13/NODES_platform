"""
A simple data collector that prints all data when the simulation finishes or still running.
From Mosaik-components modified

"""
import collections
import json
from pathlib import Path

import mosaik_api


META = {
    'type': 'time-based',
    'models': {
        'Monitor': {
            'public': True,
            'any_inputs': True,
            'params': [],
            'attrs': [],
        },
    },
}


class Collector(mosaik_api.Simulator):

    def __init__(self):
        super().__init__(META)
        self.eid = None
        self.data = collections.defaultdict(lambda:
                                            collections.defaultdict(list))
        self.data_exp = collections.defaultdict(lambda:
                                                collections.defaultdict(dict))
        # Set in init()
        self.step_size = None
        self.output_name = None
        self.print_data = False
        self.sim_meta = None

        self.time_coll = []

    def init(self, sid, step_size, time_resolution=1., output_name="data_output", print_data=False, sim_meta = None):
        if float(time_resolution) != 1.:
            raise ValueError('ExampleSim only supports time_resolution=1., but'
                             ' %s was set.' % time_resolution)
        self.step_size = step_size
        self.output_name = output_name
        self.print_data = print_data

        if self.meta['models'] == {}: # Todo: definire meglio per il collettore come fornire il meta. meglio automatico
            self.meta['models'] = sim_meta['models']
        return self.meta

    def create(self, num, model):
        if num > 1 or self.eid is not None:
            raise RuntimeError('Can only create one instance of Monitor.')

        self.eid = 'Monitor'

        return [{'eid': self.eid, 'type': model}]

    def step(self, time, inputs, max_advance):
        self.time_coll.append(time)
        data = inputs[self.eid]
        for attr, values in data.items():
            for src, value in values.items():
                self.data[src][attr].append(value)
                self.data_exp[time][f'{src}:{attr}'] = value

        return time + self.step_size

    def finalize(self):
        if self.print_data:
            data = {}
            print('Collected data:')
            for sim, sim_data in sorted(self.data.items()):
                print('- %s:' % sim)
                data[sim] = {}
                for attr, values in sorted(sim_data.items()):
                    print('  - %s: %s' % (attr, values))
                    data[sim][attr] = values
            print(f'- Time: {self.time_coll}')

        Path("../Outputs").mkdir(parents=True, exist_ok=True)
        with open(f'../Outputs/output_sim_{self.output_name}.json', 'w') as outfile:
            json.dump(self.data_exp, outfile)


if __name__ == '__main__':
    mosaik_api.start_simulation(Collector())
