import logging
import mosaik_api
import arrow
import sys
from pathlib import Path

import Watershed
import Reservoir
import User
import Hydropower
import Link


PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.append(PROJECT_ROOT)
from coesi.definitions import MODELS_ROOT

import models.energy_networks.grid_model_pandapower as model


logger = logging.getLogger('GRAPS.mosaik')

meta = {
    'type': 'hybrid',
    'models': {
        'WaterReservoir': {
            'public': True,
            'params': [
                'input_data_files',
                'sim_start',
            ],
            'attrs': [],
        },
        'Watershed': {
            'public': False,
            'params': [],
            'attrs': [
                'inflow'
            ],
        },
        'Reservoir': {
            'public': False,
            'params': [],
            'attrs': [
                'storage'
            ],
        },
        'User': {
            'public': False,
            'params': [],
            'attrs': [
                'demand',  # active power [MW]
            ],
        },
        'Link': {
            'public': False,
            'params': [],
            'attrs': [
                'p_from_mw'
            ],
        }
    },
}


class GRAPS(mosaik_api.Simulator):

    def __init__(self):
        self.step_size = None
        self.sim_start = None
        self.delta_of_simulation_start = None
        self.time_step_index = 0
        self._entities = {}
        self._relations = []  # List of pair-wise related entities (IDs)

    def init(self, sid, time_resolution, step_size, sim_meta=None):
        logger.debug("WaterReservoir model will be computed every %d seconds." %
                         (step_size * time_resolution))
        self.step_size = step_size
        return self.meta
    def readReservoirDetails(self):
        with open(MODELS_ROOT + '/graps/input_data_files/reservoir_details.dat', 'r') as file:
            index = 0
            line = file.readline()
            index = index + 1
            while line:
                nameReservoir = file.readline().strip()
                index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                latitude = int(line[0])
                longitude = int(line[1])
                index = index + 1
                line = file.readline()
                line = re.findall(r"(\d*(?:\.\d+)?)", line.strip())
                line = [float(x) for x in line if x != '']
                maxElevation = line[0]
                minElevation = line[1]
                index = index + 1
                line = file.readline()
                line = re.findall(r"(\d*(?:\.\d+)?)", line.strip())
                line = [float(x) for x in line if x != '']
                maxStorage = line[0]
                minStorage = line[1]
                currentStorage = line[2]
                index = index + 1
                line = file.readline()
                line = re.findall(r"(\d*(?:\.\d+)?)", line.strip())
                line = [float(x) for x in line if x != '']
                alpha1 = line[0]
                beta1 = line[1]
                gamma1 = line[2]
                index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                alpha2 = float(line[0] + '.' + line[1])
                beta2 = float(line[2] + '.' + line[3])
                index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                numSpillways = int(line[0])
                numOutlets = int(line[1])
                index = index + 1
                restrictionLevels = file.readline()
                restrictionLevels = re.findall(r"[\w']+", restrictionLevels.strip())
                index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                numChildren = int(line[0])
                numParents = int(line[1])
                for spill in range(numSpillways):
                    line = file.readline()
                    index = index + 1
                for outlet in range(numOutlets):
                    line = file.readline()
                    index = index + 1
                for children in range(numChildren):
                    line = file.readline()
                    index = index + 1
                for parents in range(numParents):
                    line = file.readline()
                    index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                targetStorage = float(line[0])
                targetStorageRealibility = float(line[1])
                index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                support = 0
                evaporationDepth = []
                for i in range(self.timeStepLength):
                    evaporationDepth.append(float(line[support] + '.' + line[support+1]))
                    support = support + 2
                index = index + 1
                targetRestrictionProbability = file.readline().strip()
                index = index + 1
                self.listReservoir.append(Reservoir(nameReservoir, latitude, longitude, minElevation, maxElevation, maxStorage, minStorage, currentStorage, alpha1, beta1, gamma1, alpha2, beta2, numSpillways, numOutlets, restrictionLevels, numChildren, numParents, targetStorage, targetStorageRealibility, evaporationDepth, targetRestrictionProbability))
                line = file.readline()
                index = index + 1
    def create(self, num, modelname, input_data_files, sim_start=None):
        if sim_start != None:
            self.sim_start = arrow.get(sim_start, 'YYYY-MM-DD HH:mm:ss')
        with open(MODELS_ROOT + input_data_files + '/input.dat', 'r') as file:
            input = file.readlines()
        with open(MODELS_ROOT + input_data_files + '/user_details.dat', 'r') as file:
            user_details = file.readlines()
        with open(MODELS_ROOT + input_data_files + '/reservoir_details.dat', 'r') as file:
            reservoir_details = file.readlines()
        with open(MODELS_ROOT + input_data_files + '/decisionvar_details.dat', 'r') as file:
            decisionvar_details = file.readlines()

        children = []
        for eid, attrs in sorted(entities.items()):
            assert eid not in self._entities
            self._entities[eid] = attrs

            # We'll only add relations from line to nodes (and not from
            # nodes to lines) because this is sufficient for mosaik to
            # build the entity graph.
            relations = []
            if attrs['etype'] in ['Trafo', 'Line', 'Load', 'Sgen', 'Storage']:
                relations = attrs['related']

            children.append({
                'eid': eid,
                'type': attrs['etype'],
                'rel': relations,
            })

        grids.append({
            'eid': make_eid(modelname, grid_idx),
            'type': 'Grid',
            'rel': [],
            'children': children,
        })
        return grids

    def setup_done(self):
        #TODO i nomi sono cambiati quindi da ricontrollare
        print('setupDONE rete elettrica')
        # inv_load_id = {v: k for k, v in self.simulator.load_id.items()}
        # inv_gen_id = {v: k for k, v in self.simulator.sgen_id.items()}
        #
        # related_entities = yield self.mosaik.get_related_entities()
        # for edge in related_entities['edges']:
        #     idx = None
        #     name = None
        #     if 'ext_load' in edge[0] or 'ext_load' in edge[1]:
        #         if 'ext_load' in edge[0] and edge[1].split('-')[-1] not in edge[0]:
        #             name = edge[0].split('-')[-2:-1][0] + '-' + edge[0].split('-')[-1:][0]
        #         elif 'ext_load' in edge[1] and edge[0].split('-')[-1] not in edge[1]:
        #             name = edge[1].split('-')[-2:-1][0] + '-' + edge[1].split('-')[-1:][0]
        #         if name:
        #             idx = inv_load_id[name]
        #     elif 'ext_gen' in edge[0] or 'ext_gen' in edge[1]:
        #         if 'ext_gen' in edge[0] and edge[1].split('-')[-1] not in edge[0]:
        #             name = edge[0].split('-')[-2:-1][0] + '-' + edge[0].split('-')[-1:][0]
        #         elif 'ext_gen' in edge[1] and edge[0].split('-')[-1] not in edge[1]:
        #             name = edge[1].split('-')[-2:-1][0] + '-' + edge[1].split('-')[-1:][0]
        #         if name:
        #             idx = inv_gen_id[name]
        #     if idx:
        #         self.simulator.net.sgen.in_service.at[idx] = True

    def step(self, time, inputs, max_advance):
        for eid, attrs in inputs.items():
            idx = self._entities[eid]['idx']
            etype = self._entities[eid]['etype']
            static = self._entities[eid]['static']
            for name, values in attrs.items():
                attrs[name] = sum(float(v) for v in values.values())/1000000

            self.simulator.set_inputs(etype, idx, attrs, static, )

        # TODO: Why is `powerflow_timeseries` not done if there's input?
        if self.mode == 'pf_timeseries' and not bool(inputs):
            self.simulator.powerflow_timeseries(self.time_step_index)
        elif self.mode == 'pf':
            self.simulator.powerflow()

        self._cache = self.simulator.get_cache_entries()

        self.time_step_index += 1

        if self.step_size:
            next_step = time + self.step_size
        else:
            next_step = None
        return next_step

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            for attr in attrs:
                try:
                    val = self._cache[eid][attr]
                except KeyError:
                    val = self._entities[eid]['static'][attr]
                data.setdefault(eid, {})[attr] = val

        return data

def make_eid(name,net_idx):
    return '%s-%s' % (net_idx, name)


if __name__ == "__main__":
    mosaik_api.start_simulation(GRAPS(), 'The GRAPS adapter')