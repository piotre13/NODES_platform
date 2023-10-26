import h5py
import pandas as pd


class Analyser():
    def __init__(self, file_path):
        self.hdf5 = h5py.File(file_path)
        self.file_path =file_path
        self.keys=list(self.hdf5.keys())
        self.series = self.hdf5[self.keys[1]]
        self.relations = self.hdf5[self.keys[0]]
        self.sim_config = self.hdf5[self.keys[2]]
        print(self.hdf5)

    def get_group_keys(self, group = 'series'):
        if group == 'series':
            return list(self.series.keys())
        if group == 'relations':
            return list(self.relations.keys())
        if group == 'sims':
            return list(self.sim_config.keys())
    def get_df_from_entities(self,entities):
        self.df = pd.DataFrame()
        for entity in entities
        sim_data =self.series[entities[0]]
        keys = list(sim_data.keys())
        series = sim_data[keys[0]]
        val = series[0]
        print(series)
        pass





if __name__ == '__main__':
    file_path = "/home/pietrorm/Documents/CODE/NODES_platform/Outputs/20231026_Frassinetto_test_reduced.hdf5"
    analiser = Analyser(file_path)
    entities = analiser.get_group_keys()
    df = analiser.get_df_from_entities(entities)
