"""
Agent Scheduler simulator for Mosaik.

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

import mosaik_api_v3 as mosaik_api
import pandas as pd
import numpy as np


PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.insert(0, PROJECT_ROOT)

# META = {
#     'models': {
#         'PVsimulator': {
#             'public': True,
#             'params': ['P_system', 'slope', 'aspect', 'latitude', 'longitude', 'elevation',
#                        'Tc_noct', 'T_ex_noct', 'a_p', 'ta', 'P_mpdule',
#                        'G_noct', 'G_stc', 'Area', 'Tc_stc', 'start_date'],
#             'attrs': ['power_dc', 'ghi', 'T_ext'],
#         },
#     },
# }

META = {
    'type': 'time-based',
    'models': {}
}


class AgentScheduler(mosaik_api.Simulator):

    def __init__(self):
        super().__init__(META)
        self.agents = {}

    def init(self, sid,  time_resolution=1., start_date=None, days=None, sim_meta=None):
        # if float(time_resolution) != 1.:
        #     raise ValueError('ExampleSim only supports time_resolution=1., but'
        #                      ' %s was set.' % time_resolution)
        self.start_date = pd.to_datetime(start_date)  # TODO: la start_date è importante per iniziare nel momento
        # giusto, non viene utilizzata ma si suppone si inizi sempre alle 00:00:00 di un giorno x
        self.time_resolution = time_resolution
        self.step_size = None
        self.times = []
        if days:
            self.days = int(np.ceil(days + 1)) #days+1  # to guaranteee the sim until the end
        else:
            self.days = 2

        if self.meta['models'] == {}:
            self.meta['models'] = sim_meta['models']
        return self.meta

    def create(self, num, model, schedule, type_schedule='day', unit_schedule='hour'):
        if num != 1:
            raise ValueError('Can only create one entity per each model agent.')  # TODO: per adesso un agente
            # gestisce un parametro solo ma posso creare più modelli
        next_eid = len(self.agents)
        entities = []
        # Schedule structure:
        # list of string in order of time ['', '..'] starting from start_date (at 00:00:00) for unit schedule and it
        # repeat as
        # type_schedule. Example for daily/hour:var ['0:16','6:20','22:16']
        sch = {}
        day_in_seconds = 1 * 24 * 60 * 60
        counter = 0
        for day in range(self.days):
            for tr_val in schedule:
                tr, val = list(map(float, tr_val.split(':')))

                sch[pd.to_timedelta(tr, unit=unit_schedule).total_seconds() + counter * day_in_seconds] = val
                self.times.append(pd.to_timedelta(tr, unit=unit_schedule).total_seconds() + counter *
                                  day_in_seconds)
            counter += 1

        for i in range(next_eid, next_eid + num):
            eid = '%s_%d' % (model, i)
            parameter = self.meta['models'][model]['attrs'][0]  # TODO: for the moment one parameter per each model

            self.agents[eid] = {parameter: sch}
            entities.append({'eid': eid, 'type': model})

        return entities

    def step(self, time, max_advance, inputs=None):
        self.cache = {}
        time_new = self.times[self.times.index(int(time*self.time_resolution)) + 1]
        self.step_size = time_new - int(time*self.time_resolution)
        for agent, param_sch in self.agents.items():
            par_time_value = {}
            self.cache[agent] = {}
            for param in param_sch.keys():
                self.cache[agent][param] = param_sch[param][int(time*self.time_resolution)]
        return time + int(self.step_size/self.time_resolution)

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            model_type = eid.split('_')[0]
            data[eid] = {}
            for attr in attrs:
                if attr not in self.meta['models'][model_type]['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)

                # Get model.val or model.delta:
                data[eid][attr] = self.cache[eid][attr]

        return data


if __name__ == '__main__':
    mosaik_api.start_simulation(AgentScheduler())
