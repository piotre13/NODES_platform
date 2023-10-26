import yaml
import json
import os
from components_templates import comp_temp # todo the template file should be something different than a python file
import io
from copy import deepcopy

class Scenario_Yaml():
    def __init__(self, name):
        self.scenario_name = name
        self.scenario = None
        self.templates = comp_temp
        self.eids=[]
        self.building_eids = []
        self.hvac_eids = []


    def auto_creation(self, sim_dict=False):
        creation_complete = False
        self.scenario = self.templates['basics']
        if sim_dict:
            self.sim_instances(sim_dict)
            self.add_weather(sim_dict)
            self.connect_weather()
            self.auto_connections()
            self.scenario['SCEN_CONFIG']['DAYS']=15
            self.scenario['SCEN_CONFIG']['START_DATE']= '2021-01-01 01:00:00'
            self.scenario['SCEN_CONFIG']['SCENARIO_NAME']= self.scenario_name

        else:
            print('no sim dict') # todo in case no sim dict is prepared should be an iterative flow with input
        print('yo')

        pass
    def sim_instances(self, sim_dict):
        for key in sim_dict['sims'].keys():
            if key == 'FMUs':
                eids = self.Fmu_instances(sim_dict['sims'][key])

            elif key == 'DB':
                eid = self.HDF5_collector(sim_dict['sims'][key])
                pass
            else:
                print('not recognized sim key')

        if sim_dict['autohvac']:
            self.hvac_instances(sim_dict['hvactype'], sim_dict['hvac_attrs'])



    def Fmu_instances(self, fmu_dict):
        #todo capire se posso usare num con diverse fmu senza dover create un simulatore per ogni fmu
        entities_ids = []
        if fmu_dict['auto']:
            i=0
            for fmu in os.listdir(fmu_dict['fmu_dir']):
                if i==300:
                    break
                if fmu.endswith('.fmu'):
                    name = fmu.split('.')[0]
                    inst_name = str('Bui'+ name.split('_')[-1])
                    tmp = self.templates['FMU_inst'][fmu_dict['mk']]
                    tmp['MODELS'][fmu_dict['mod_name']]['ATTRS']= fmu_dict['attrs']
                    tmp['PARAMS']['work_dir'] = fmu_dict['fmu_dir'].split('/')[-1]
                    tmp['MODELS'][fmu_dict['mod_name']]['PARAMS']['fmu_name'] = name
                    tmp['MODELS'][fmu_dict['mod_name']]['PARAMS']['instance_name'] = [inst_name]
                    tmp['MODELS'][fmu_dict['mod_name']]['PARAMS']['num'] = 1
                    tmp['MODELS'][fmu_dict['mod_name']]['PUBLIC'] = True

                sim_name = fmu_dict['mk']+str(i)

                self.scenario['SIM_CONFIG'][sim_name]=deepcopy(tmp)
                eid = sim_name+'.'+list(tmp['MODELS'].keys())[0]+ '_'+inst_name
                self.eids.append(eid)
                self.building_eids.append(eid)
                i+=1

        return entities_ids

    def HDF5_collector(self, db_dict):
        if db_dict:
            self.scenario['SCEN_OUTPUTS'] = self.templates['DB_collector']
            eid = ''
        return eid
    def hvac_instances(self, type, attrs):

        self.scenario['SIM_CONFIG']['heating_system'] = self.templates['heating_sys']['heating_system']
        if type == 'gb' :
            model_name ='hs'
            del self.scenario['SIM_CONFIG']['heating_system']['MODELS']['hp']

        if type == 'hp' :
            model_name ='hp'
            del self.scenario['SIM_CONFIG']['heating_system']['MODELS']['hs']

        self.scenario['SIM_CONFIG']['heating_system']['MODELS'][model_name]['ATTRS'] = attrs
        self.scenario['SIM_CONFIG']['heating_system']['MODELS'][model_name]['PARAMS']['num'] = len(self.building_eids)
        self.scenario['SIM_CONFIG']['heating_system']['MODELS'][model_name]['PARAMS']['leased_area'] = 100 # todo può essere una lista?

        print('yo')

    def auto_connections(self):
        for sim in self.scenario['SIM_CONFIG'].keys():
            if sim.startswith('fmu'):
                self.scenario = self.connect_all2DB(self.scenario, attr_name='TBuilding', sim_name= sim)
                self.scenario = self.connect_all2DB(self.scenario, attr_name='HeatingLoadTarget', sim_name= sim)

            elif sim.startswith('h'):
                self.scenario = self.connect_all2DB(self.scenario, attr_name='fuel', sim_name= sim)
                self.scenario = self.connect_all2DB(self.scenario, attr_name='En_auxel', sim_name= sim)
                self.scenario = self.connect_all2DB(self.scenario, attr_name='Qt', sim_name= sim)

        self.connect_autohvac()
        pass
    def connect_autohvac(self):

        for i in range(len(self.building_eids)):
            j = i  + 1
            self.scenario['CONNECTIONS'][str(j)]={
                'FROM': self.building_eids[i],
                'TO':'heating_system.hs_%s'%i,
                'ATTRS':[['HeatingLoadTarget','Qt']]
            }
        for i in range(len(self.building_eids)):
            j = len(self.scenario['CONNECTIONS'])
            self.scenario['CONNECTIONS'][str(j)] = {
                'FROM': 'heating_system.hs_%s' % i,
                'TO': self.building_eids[i],
                'ATTRS': [['Qt', 'OthEquRadWatt']],
                'PARAMS':{
                    'time_shifted':True,
                    'initial_data':{
                        'Qt': 0.0
                    }
                }
            }


        print('yo')

        pass
    def connect_all2DB(self, yaml_file, attr_name, sim_name=None):
        if sim_name:
            sim = sim_name
            for model in yaml_file['SIM_CONFIG'][sim]['MODELS']:
                num = yaml_file['SIM_CONFIG'][sim]['MODELS'][model]['PARAMS']['num']
                for i in range(num):
                    if 'instance_name' not in yaml_file['SIM_CONFIG'][sim]['MODELS'][model]['PARAMS']:
                        attr = sim + '.' + model + '_' +str(i)+'.' + attr_name

                    elif len(yaml_file['SIM_CONFIG'][sim]['MODELS'][model]['PARAMS']['instance_name']) == 1:
                        inst_names = yaml_file['SIM_CONFIG'][sim]['MODELS'][model]['PARAMS']['instance_name']
                        attr = sim + '.' + model + '_' + inst_names[0] + '.' + attr_name

                    else:
                        inst_names = yaml_file['SIM_CONFIG'][sim]['MODELS'][model]['PARAMS']['instance_name']
                        attr = sim + '.' + model + '_' + inst_names[i] + '_' +str(i)+'.' + attr_name

                    if attr not in yaml_file['SCEN_OUTPUTS']['DB']['attrs']:
                        yaml_file['SCEN_OUTPUTS']['DB']['attrs'].append(attr)
        else:
            for sim in yaml_file['SIM_CONFIG']:
                for model in yaml_file['SIM_CONFIG'][sim]['MODELS']:
                    inst_names = yaml_file['SIM_CONFIG'][sim]['MODELS'][model]['PARAMS']['instance_name']
                    num = yaml_file['SIM_CONFIG'][sim]['MODELS'][model]['PARAMS']['num']
                    for i in range(num):
                        if len(inst_names) == 0:
                            attr = sim + '.' + model + '_' + str(i) + '.' + attr_name

                        elif len(inst_names) == 1:
                            attr = sim + '.' + model + '_' + inst_names[0] + '_' + str(i) + '.' + attr_name

                        else:
                            attr = sim + '.' + model + '_' + inst_names[i] + '_' + str(i) + '.' + attr_name

                        if attr not in yaml_file['SCEN_OUTPUTS']['DB']['attrs']:
                            yaml_file['SCEN_OUTPUTS']['DB']['attrs'].append(attr)

        return yaml_file
    def write_yaml(self):
        path = self.scenario_name+'.yaml'
        with io.open(path, 'w', encoding='utf8') as outfile:
            yaml.dump(self.scenario, outfile, default_flow_style=False, allow_unicode=True)

    def add_weather(self, sim_dict):
        with open('weather_templ.yaml', 'r') as fp:
            tmp = yaml.safe_load(fp)

        key=list(tmp.keys())[0]
        tmp[key]['PARAMS']['datafile'] = sim_dict['sims']['weather']['data_file']
        self.scenario['SIM_CONFIG'][key]= tmp[key]

        print(tmp)
    def connect_weather(self):
        num = len (self.scenario['CONNECTIONS'])
        to = ['heating_system.hs_%i'%i for i in range(len(self.building_eids))]
        attrs = [['DryBulb','Text']]
        self.scenario['CONNECTIONS']['0']={'FROM': 'timeseries.ts_0',
                                                'TO': to,
                                                'ATTRS': attrs}

def timeseries_instances():
    ts_inst = []
    return ts_inst






if __name__ == '__main__':
    sim_dict = {
        "autohvac":True,
        "hvactype":"gb",
        "hvac_attrs":["Qt", "G_gas", "En_auxel", "Text", "fuel"],
        "sims":{
            "FMUs":{"auto":True, # serve per fare un simulatore per ogni fmu
                    "fmu_dir":"/home/pietrorm/Documents/CODE/NODES_platform/models/fmus/frassinetto_casestudy_reduced",
                    "attrs":["PeopleNumber","peopleActivity","LightsWatt","EEquipWatt","InfilAch","OthEquRadWatt","OthEquFCWatt","TBuilding","HeatingLoadTarget"],
                    "mk": "fmu_pyfmi_sim",
                    "mod_name": "rc"},

            "DB": True,
            "weather":{
                "data_file": "/home/pietrorm/Documents/CODE/NODES_platform/data/meteo_file/meteo_bousson.csv"
            }
        }
    }

    scenario = Scenario_Yaml('Frassinetto_test_reduced')
    #scenario.add_weather()
    scenario.auto_creation(sim_dict)
    scenario.write_yaml()