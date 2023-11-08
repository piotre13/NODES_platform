""""
timeseries data used as simulator
with pandas and interpolation


CSV input format

DateTime column in format 'YYYY-MM-DD HH:mm:ss'
DateTime | attr1 | attr2 | ... |

will be converted in types:
datetime64 | float | float
"""

import os
import sys
from pathlib import Path

import mosaik_api_v3 as mosaik_api
import pandas as pd
import numpy as np


PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.append(PROJECT_ROOT)
from coesi.definitions import MODELS_ROOT


META = {
    'type': 'time-based',
    'models': {},
}

DATE_FORMAT = 'YYYY-MM-DD HH:mm:ss'


class TimeSeriesSim(mosaik_api.Simulator):

    def __init__(self):
        super().__init__(META)
        self.start_date = None
        self.stop_date = None
        self.df = None
        self.stepsize = None
        self.modelname = 'ts'
        self.attrs = None
        self.eids = []
        self.cache = None
        self.timesteps = None

    def init(self, sid, datafile, start_date, stop_date=None, stepsize=None, time_resolution=1., sim_meta=None,
             conv_dict=None):
        if float(time_resolution) != 1.:
            raise ValueError('ExampleSim only supports time_resolution=1., but'
                             ' %s was set.' % time_resolution)
        # load datafile
        self.df = pd.read_csv(os.path.join(MODELS_ROOT, datafile))

        # Set timestamp and DatetimeIndex
        assert 'DateTime' in self.df.columns
        self.df.DateTime = pd.to_datetime(self.df.DateTime)
        assert self.df.select_dtypes(include=[np.datetime64]).columns.to_list() == ['DateTime']
        self.df.set_index(pd.DatetimeIndex(self.df.DateTime), inplace=True)

        self.df.drop(columns='DateTime', inplace=True)

        # make conversion
        # conv_dict = {'column_name':'a.b'} where ax + b are the coefficiets to converte the measure
        if conv_dict:
            for attr, conv in conv_dict.items():
                a, b = [eval(x) for x in conv.split(':')]
                self.df[attr] = self.df[attr] * a + b
        # Collect all columns as attrs
        self.attrs = self.df.columns.to_list

        # Get attribute names and strip optional comments or retrieve from sim_meta yaml
        if self.meta['models'] == {} and sim_meta != None:
            self.meta['models'] = sim_meta['models']

        else:
            self.meta['models'][self.modelname] = {
                'public': True,
                'params': [],
                'attrs': self.attrs,
            }

        # Set start date and stop date
        if start_date != None:
            self.start_date = pd.to_datetime(start_date)
        else:
            self.start_date = self.df.index[0]
        if stop_date != None:
            self.stop_date = pd.to_datetime(stop_date)
        else:
            self.stop_date = self.df.index[-1]
        try:
            self.df.loc[self.start_date]
            self.df.loc[self.stop_date]
            self.df = self.df.loc[self.start_date:self.stop_date]
        except KeyError:
            raise KeyError(f'{self.start_date} is not present in timeseries.')

        # set stepsize
        stepsize_from_df = int((self.df.index[1] - self.df.index[0]).total_seconds())
        if stepsize != None:
            self.stepsize = stepsize
            if self.stepsize != stepsize_from_df:
                # Resampling wrt stepsize
                print("Resampling of the timeseries..")
                self.df = self.df.resample(pd.Timedelta(seconds=self.stepsize)).interpolate('akima')
                print("done.")
        else:
            self.stepsize = stepsize_from_df



        self.df_dict = self.df.to_dict('records')
        self.timesteps = 0
        #print(self.df.head())
        return self.meta

    def create(self, num, model):
        # if model != self.modelname:
        #     raise ValueError('Invalid model "%s" % model')

        start_idx = len(self.eids)
        entities = []
        for i in range(num):
            eid = '%s_%s' % (model, i + start_idx)
            entities.append({
                'eid': eid,
                'type': model,
                'rel': [],
            })
            self.eids.append(eid)
        return entities

    def step(self, time, max_advance, inputs=None):
        expected_date = self.start_date + pd.Timedelta(seconds=time)
        self.timesteps = int(time / self.stepsize)
        # Chacke date
        date = self.df.iloc[self.timesteps].name
        if date != expected_date:
            raise IndexError(f'Wrong date "{date}", expected "{expected_date}"')

        # Put data into the cache for get_data() calls
        self.cache = self.df_dict[self.timesteps]

        return time + int(self.stepsize)

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            if eid not in self.eids:
                raise ValueError('Unknown entity ID "%s"' % eid)

            data[eid] = {}
            for attr in attrs:
                data[eid][attr] = self.cache[attr]

        return data


def main():
    return mosaik_api.start_simulation(TimeSeriesSim())
