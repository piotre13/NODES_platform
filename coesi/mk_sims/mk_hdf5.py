"""
Store mosaik simulation data in an HDF5 database.

From Mosaik-components modified. The mosaik HDF5 storage backend was created by Stefan Scherfke. GNU LGPLv2.1
https://gitlab.com/mosaik/mosaik-hdf5

Structure Example
The Relations group contains one dataset for every entity. For each of the
entity's relations, the dataset has one tuple (path_to_relation,
path_to_relatio_series).
The Series group contains (by default) one group for every entity. Each of
these group as one dataset for every attribute.
Static entity data is stored as attributes in the entity groups. Simulation
meta data is stored as attributes of the root group.

/ [meta data]
|
+- Relations
|  |
|  +- Sim-0.Entity-1
|  |
|  +- PyPower-0.1-Node-2
|
+- Series
   |
   +- Sim-0.Entiy-1 [static data]
   |  |
   |  +- val_out
   |
   +- PyPower-0.1-Node-2 [static data]
      |
      +- P
      |
      +- Q


"""
import os
import sys
from pathlib import Path
import shutil
from datetime import date

import json
import re

import h5py
import mosaik_api
import networkx as nx
import numpy as np


PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.insert(0,PROJECT_ROOT)
from coesi.definitions import TEMP_ROOT, OUTPUTS_ROOT
from utils import scn_config_load

__version__ = '0.3'
# meta = {
#     'models': {
#         'Database': {
#             'public': True,
#             'any_inputs': True,
#             'params': ['filename', 'buf_size', 'dataset_opts'],
#             'attrs': [],
#         },
#     },
#     'extra_methods': [
#         'set_meta_data',
#         'set_static_data',
#     ],
# }
META = {
    'type': 'time-based',
    'models': {},
    'extra_methods': [
        'set_meta_data',
        'set_static_data',
    ],
}


class MosaikHdf5(mosaik_api.Simulator):

    def __init__(self):
        super().__init__(META)
        self.eid = 'db'

        # Set in init()
        self.sid = None
        self.step_size = None
        self.duration = None
        self.ds_size = None
        self.series_path = None  # regex object for the series path
        self.series_path_repl = None  # replacement string for series path

        # Set in create()
        self.db = None
        self.rels = None
        self.series = None
        self.buf_size = None
        self.dataset_opts = {}

        # Used in step()
        self.eid_path = {}  # Stores the series path for an entity
        self.data_buf = {}

    def init(self, sid, step_size, duration, time_resolution=1., series_path=(None, None), sim_meta=None):
        # if float(time_resolution) != 1.:
        #     raise ValueError('ExampleSim only supports time_resolution=1., but'
        #                      ' %s was set.' % time_resolution)
        self.sid = sid
        self.step_size = step_size
        self.duration = duration
        self.ds_size = self.duration // self.step_size
        if series_path[0] is not None:
            self.series_path = re.compile(series_path[0])
            self.series_path_repl = series_path[1]

        if self.meta['models'] == {}:  # Todo: definire meglio per hdf5 come fornire il meta. meglio
            # automaticoo
            self.meta['models'] = sim_meta['models']

        return self.meta

    def create(self, num, model, filename, buf_size=1000, dataset_opts=None, scn_config_file=None):
        # TODO scn_config_file al momento non utilizzato perche si prende da temp folder
        if num != 1 or self.db is not None:
            raise ValueError('Can only create one database.')
        if model != 'db':
            raise ValueError('Unknown model: "%s"' % model)

        self.buf_size = buf_size
        if dataset_opts:
            self.dataset_opts.update(dataset_opts)

        today = date.today().strftime("%Y%m%d")
        self.filename = f'{today}_{filename}.hdf5'


        if os.path.isfile(os.path.join(OUTPUTS_ROOT,self.filename)):
            expand = 1
            while True:
                expand += 1
                new_file_name = self.filename.split(".hdf5")[0] + "_"+str(expand) + ".hdf5"
                if os.path.isfile(os.path.join(OUTPUTS_ROOT,new_file_name)):
                    continue
                else:
                    self.filename = new_file_name
                    break

        self.db = h5py.File(os.path.join(TEMP_ROOT,self.filename), 'w')
        self.rels = self.db.create_group('Relations')
        self.series = self.db.create_group('Series')

        self.dscn = self.db.create_dataset('Sim_set',shape=(100,))
        scn = scn_config_load("temp_scn.yaml", TEMP_ROOT) # TODO scenario preso dal temp, non affidabile al 100 e
        # generalizzabile
        self.dscn.attrs['Scenario'] = json.dumps(scn)

        return [{'eid': self.eid, 'type': model, 'rel': []}]

    def setup_done(self):
        yield from self._store_relations()

    def step(self, time, inputs, max_advance):
        assert len(inputs) == 1
        inputs = inputs[self.eid]

        # Store series
        g_series = self.series
        buf_size = self.buf_size
        eid_path = self.eid_path
        buf = self.data_buf
        abs_idx = time // self.step_size
        rel_idx = abs_idx % buf_size

        for attr, data in inputs.items():
            for src_id, value in data.items():
                if time == 0:
                    self._create_dataset(src_id, attr, float,
                                         self.ds_size, buf, buf_size)

                path = eid_path[src_id]
                key = '%s/%s' % (path, attr)

                # Buffer data to improve performance
                buf[key][rel_idx] = value

        # Save step size time todo: e anche il time date conoscendo lo start date?
        if time == 0:
            self._create_dataset('time', 't', type(float(time)),
                                 self.ds_size, buf, buf_size)
        path = eid_path['time']
        key = '%s/%s' % (path, 't')
        # Buffer data to improve performance
        buf[key][rel_idx] = float(time)



        buf_len = rel_idx + 1
        last_step = bool(time + self.step_size >= self.duration)
        if buf_len == buf_size or last_step:
            # Write and clear buffer
            start = abs_idx - rel_idx
            end = start + buf_len
            for key, val in buf.items():
                g_series[key][start:end] = buf[key][:buf_len]

        return time + self.step_size

    def finalize(self):
        self.db.close()
        Path(OUTPUTS_ROOT).mkdir(parents=True, exist_ok=True)
        shutil.move(os.path.join(TEMP_ROOT,self.filename),os.path.join(OUTPUTS_ROOT,self.filename))
        print(f'Simulation data saved in Outputs folder as {self.filename}')


    def set_meta_data(self, data):
        self._save_attrs(self.db, data)

    def set_static_data(self, data):
        for eid, attrs in data.items():
            g = self._get_group(eid)
            self._save_attrs(g, attrs)

    def _store_relations(self):
        """Query relations graph and store it in the database."""
        db_full_id = '%s.%s' % (self.sid, self.eid)
        data = yield self.mosaik.get_related_entities()
        nxg = nx.Graph()
        nxg.add_nodes_from(data['nodes'].items())
        nxg.add_edges_from(data['edges'])

        s_name = self.series.name
        r_name = self.rels.name
        for node, neighbors in sorted(nxg.adj.items()):
            if node == db_full_id:
                continue
            rels = sorted(n for n in neighbors if n != db_full_id)
            rels = np.array([
                (
                    ('%s/%s' % (r_name, n)).encode(),
                    ('%s/%s' % (s_name, self._get_entity_path(n))).encode(),
                ) for n in rels
            ], dtype=(bytes, bytes))
            self.rels.create_dataset(node, data=rels, **self.dataset_opts)

    def _create_dataset(self, src_id, attr, dtype, ds_size, buf, buf_size):
        """Create a dataset for the attribute *attr* of entity *src_id*.

        The dataset will use the type *dtype* and will have the size *ds_size*.

        Also initialize the buffer *buf* with size *buf_size*.

        """
        g = self._get_group(src_id)
        ds = g.create_dataset(attr, (ds_size,), dtype=np.dtype(dtype),
                              **self.dataset_opts)
        buf[ds.name] = np.empty(buf_size, dtype=dtype)

    def _get_group(self, eid):
        """Get or create group for entity *eid*."""
        try:
            path = self.eid_path[eid]
            g = self.series[path]
        except KeyError:
            path = self._get_entity_path(eid)
            g = self.series.create_group(path)
            self.eid_path[eid] = g.name

        return g

    def _get_entity_path(self, eid):
        if self.series_path is not None:
            path = self.series_path.sub(self.series_path_repl, eid)
        else:
            path = eid
        return path

    def _save_attrs(self, g, attrs):
        for k, v in attrs.items():
            print(type(v))
            # type(v) is in (int, float, str, list, dict, bool, type(None))
            if type(v) in (list, dict, tuple):
                g.attrs[k] = json.dumps(v).encode()
            else:
                g.attrs[k] = v


if __name__ == '__main__':
    desc = __doc__.strip()
    mosaik_api.start_simulation(MosaikHdf5(), desc)
