import h5py
import pandas as pd
from datetime import datetime, timedelta

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
        self.dfs = {}
        for entity in entities:
            print(entity)
            sim_data = self.series[entity]
            keys = list(sim_data.keys())
            for k in keys:
                build_name = entity.split('.')[-1]
                col_names =['id','date','value']
                start_time = datetime(2021,1,1,0,0,0)
                time_delta = timedelta (minutes=10) # todo generalize this can be storing at begining the sim config data


                if k not in self.dfs.keys():
                    self.dfs[k]=pd.DataFrame(columns=col_names)
                    curr_time = start_time
                    rows=[]
                    for val in sim_data[k][1440:]:
                        row = [build_name,curr_time,val]
                        rows.append(row)
                        #self.dfs[k].loc[len(self.dfs[k])] = row
                        curr_time+=time_delta
                    self.dfs[k]=pd.concat([self.dfs[k], pd.DataFrame(rows, columns=col_names)])
                else:
                    curr_time=start_time
                    rows=[]
                    for val in sim_data[k][1440:]:
                        row = [build_name,curr_time,val]
                        rows.append(row)
                        curr_time+=time_delta
                    self.dfs[k] = pd.concat([self.dfs[k], pd.DataFrame(rows, columns=col_names)])

        print('yo')
    def save_dfs(self):
        for key,df in self.dfs.items():
            path = '_dfs/'+self.file_path.split('/')[-1].split('.')[0]+'_'+key+'.csv'
            df.to_csv(path)





if __name__ == '__main__':
    file_path = "/home/pietrorm/Documents/CODE/NODES_platform/Outputs/20231119_Frassinetto_test_med.hdf5"
    analiser = Analyser(file_path)
    entities = analiser.get_group_keys()
    df = analiser.get_df_from_entities(entities)
    analiser.save_dfs()
